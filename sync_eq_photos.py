#!/usr/bin/env python3
"""
Copy photos from the EQ list album into images/eq-*.jpg (hashed names from data.json).

Default album: ~/Downloads/EQ list photos (override with env PHOTO_KIT_EQ_ALBUM or CLI args).

  python3 sync_eq_photos.py
  python3 sync_eq_photos.py "/path/to/EQ list photos"
  python3 sync_eq_photos.py --fresh "/path/to/EQ list photos"   # delete images/* first, then sync

After copying, removes any file in images/ that is not listed in data.json (old Openverse/B&H junk).

Optional: eq_photo_overrides.json next to this script maps { "filename.jpg": "Exact PDF item line" }.
"""
from __future__ import annotations

import json
import os
import re
import shutil
import sys
from difflib import SequenceMatcher
from pathlib import Path

from build_from_pdf import image_stem

ROOT = Path(__file__).resolve().parent
DATA = ROOT / "data.json"
IMAGES = ROOT / "images"
OVERRIDES_PATH = ROOT / "eq_photo_overrides.json"
DEFAULT_SRC = Path(
    os.environ.get(
        "PHOTO_KIT_EQ_ALBUM",
        str(Path.home() / "Downloads" / "EQ list photos"),
    )
)

SYNC_IMAGE_ATTRIBUTION = (
    "Hover images are your photos from ~/Downloads/EQ list photos (run sync_eq_photos.py)."
)

# Filename (exact) -> exact data.json item string (when fuzzy match is wrong)
MANUAL: dict[str, str] = {
    "Avenger_D600CB_D600CB_Mini_Boom_331474.jpg": "Avenger D520LB mini boom with clamp",
    "Manfrotto_Ground_Stand.jpg": "Floor / backlight stands",
    "Elinchrom 6000N Ws bi-tube head": "Elinchrom 6000 Ws bi-tube head",
    "Elinchrom A3000N Ws head.jpg": "Elinchrom 3000 Ws head",
    "Elinchrom 3x3 large softbox _ bank.jpg": "Elinchrom Rotalux / standard 3 x 3' softbox",
    "Elinchrom 6' x 6' large softbox _ bank.jpg": "Elinchrom 6' x 6' large softbox / bank",
    "himera soft banks - 1 x 1x4', 2 x 2x4' strip _ frame kits.jpg": (
        "Chimera soft banks - 1 x 1x4', 2 x 2x4' strip / frame kits"
    ),
    "Canon EOS (EF_EF-S) to Fujifilm X adapter.jpg": "Canon EOS (EF/EF-S) to Fujifilm X adapter",
    "Hasselblad 500C_M medium-format film body.jpg": "Hasselblad 500C/M medium-format film body",
}


def load_user_overrides() -> dict[str, str]:
    if not OVERRIDES_PATH.exists():
        return {}
    try:
        raw = json.loads(OVERRIDES_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {str(k): str(v) for k, v in raw.items() if not str(k).startswith("_")}


def norm(s: str) -> str:
    s = s.lower().strip()
    s = re.sub(r"^\d+\s+", "", s)
    s = s.replace("_", " ")
    s = re.sub(r"[^a-z0-9\s]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def collect_items() -> list[str]:
    data = json.loads(DATA.read_text(encoding="utf-8"))
    out: list[str] = []
    for g in data["groups"]:
        for sub in g["subsections"]:
            for it in sub["items"]:
                out.append(it["item"])
    return out


def best_item_fuzzy(filename: str, items: list[str]) -> tuple[str, float]:
    stem = Path(filename).name
    key = norm(stem)
    best, score = items[0], 0.0
    for it in items:
        r = SequenceMatcher(None, key, norm(it)).ratio()
        if r > score:
            best, score = it, r
    return best, score


def match_file_to_item(filename: str, items: list[str]) -> tuple[str, float]:
    """Prefer exact match of normalized filename stem to a PDF line; else fuzzy."""
    stem_key = norm(Path(filename).stem)
    for it in items:
        if norm(it) == stem_key:
            return it, 1.0
    return best_item_fuzzy(filename, items)


def save_as_jpg(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    suf = src.suffix.lower()
    if suf in (".jpg", ".jpeg"):
        shutil.copy2(src, dst)
        return
    try:
        from PIL import Image  # type: ignore

        im = Image.open(src)
        if im.mode in ("RGBA", "P"):
            im = im.convert("RGBA")
            bg = Image.new("RGB", im.size, (255, 255, 255))
            bg.paste(im, mask=im.split()[-1] if im.mode == "RGBA" else None)
            im = bg
        else:
            im = im.convert("RGB")
        im.save(dst, "JPEG", quality=90)
    except ImportError:
        import subprocess

        tmp = dst.with_suffix(".tmp.jpg")
        r = subprocess.run(
            ["sips", "-s", "format", "jpeg", str(src), "--out", str(tmp)],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0 or not tmp.exists():
            print(f"PIL missing and sips failed for {src.name}: {r.stderr}", file=sys.stderr)
            sys.exit(1)
        shutil.move(tmp, dst)


def collect_files_from_dirs(dirs: list[Path]) -> list[Path]:
    exts = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
    out: list[Path] = []
    for d in dirs:
        for p in d.iterdir():
            if not p.is_file() or p.name.startswith("."):
                continue
            suf = p.suffix.lower()
            if suf and suf not in exts:
                continue
            out.append(p)
    out.sort(key=lambda p: (p.name.lower(), str(p.resolve())))
    return out


def album_matched_items(album: Path) -> set[str]:
    """Item strings from data.json that have at least one matching file in ``album``."""
    manual = {**MANUAL, **load_user_overrides()}
    items = collect_items()
    item_set = set(items)
    matched: set[str] = set()
    if not album.is_dir():
        return matched
    for path in collect_files_from_dirs([album.resolve()]):
        name = path.name
        if name in manual:
            if manual[name] in item_set:
                matched.add(manual[name])
        else:
            item, score = match_file_to_item(name, items)
            if score >= 0.5:
                matched.add(item)
    return matched


def required_image_basenames() -> set[str]:
    """Filenames under images/ that data.json references (one per equipment line)."""
    return {f"{image_stem(it)}.jpg" for it in collect_items()}


def prune_orphan_images() -> int:
    """Delete anything in images/ not referenced by data.json (stale downloads)."""
    required = required_image_basenames()
    if not IMAGES.is_dir():
        return 0
    removed = 0
    for p in IMAGES.iterdir():
        if not p.is_file() or p.name.startswith("."):
            continue
        if p.name not in required:
            p.unlink()
            print(f"Removed orphan: {p.name}", flush=True)
            removed += 1
    return removed


def wipe_images_dir() -> None:
    """Remove every file in images/ (fresh sync from album only)."""
    IMAGES.mkdir(parents=True, exist_ok=True)
    for p in IMAGES.iterdir():
        if p.is_file() and not p.name.startswith("."):
            p.unlink()


def apply_sync_site_metadata() -> None:
    """Refresh footer attribution after syncing photos (does not remove bh_preview_url fallback)."""
    if not DATA.exists():
        return
    payload = json.loads(DATA.read_text(encoding="utf-8"))
    payload.setdefault("meta", {})["image_attribution"] = SYNC_IMAGE_ATTRIBUTION
    DATA.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    import argparse

    ap = argparse.ArgumentParser(description="Copy EQ album photos into images/eq-*.jpg")
    ap.add_argument(
        "--fresh",
        action="store_true",
        help="Delete everything in images/ before syncing (start from album only).",
    )
    ap.add_argument(
        "dirs",
        nargs="*",
        type=Path,
        help=f"Album folder (default: {DEFAULT_SRC})",
    )
    args = ap.parse_args()

    dirs = [p.resolve() for p in args.dirs if p.is_dir()]
    if not dirs:
        dirs = [DEFAULT_SRC.resolve()]
    for d in dirs:
        if not d.is_dir():
            print(f"Not a directory: {d}", file=sys.stderr)
            sys.exit(1)

    if args.fresh:
        wipe_images_dir()
        print("Cleared images/ (--fresh).", flush=True)

    manual = {**MANUAL, **load_user_overrides()}
    items = collect_items()
    item_set = set(items)
    files = collect_files_from_dirs(dirs)
    matched_items: set[str] = set()
    used_items: set[str] = set()
    applied = 0

    for path in files:
        name = path.name
        if name in manual:
            item = manual[name]
            if item not in item_set:
                print(f"OVERRIDE/MANUAL key not in data.json: {name!r} -> {item!r}", file=sys.stderr)
                continue
        else:
            item, score = match_file_to_item(name, items)
            if score < 0.5:
                print(f"SKIP (low score {score:.2f}): {name}", file=sys.stderr)
                continue
            if score < 0.72:
                print(f"WARN ({score:.2f}): {name!r} -> {item!r}", file=sys.stderr)

        stem = image_stem(item)
        dst = IMAGES / f"{stem}.jpg"

        save_as_jpg(path, dst)
        print(f"{name} -> {stem}.jpg ({item[:48]}…)")
        applied += 1
        matched_items.add(item)
        if item in used_items:
            print(f"  NOTE: duplicate item {item!r} (later file wins)", file=sys.stderr)
        used_items.add(item)

    print(f"Done. Wrote {applied} image(s) from {len(dirs)} folder(s) into {IMAGES}.")

    not_in_album = [it for it in items if it not in matched_items]
    if not_in_album:
        print(
            f"\n--- {len(not_in_album)} line(s) had no file in the album (left unchanged) ---",
            flush=True,
        )
        print(
            "Existing images/eq-*.jpg for those rows are unchanged until you add matching files.",
            flush=True,
        )
        print("Only add more files if you want to replace those too.\n", flush=True)
        for it in not_in_album:
            print(f"  • {it}", flush=True)

    n_pruned = prune_orphan_images()
    if n_pruned:
        print(f"Pruned {n_pruned} orphan file(s) from images/.", flush=True)

    apply_sync_site_metadata()
    print("Updated data.json: image_attribution refreshed.", flush=True)


if __name__ == "__main__":
    main()
