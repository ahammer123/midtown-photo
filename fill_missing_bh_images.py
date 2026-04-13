#!/usr/bin/env python3
"""
For equipment rows that have NO matching file in the EQ list photos album, fetch the
first B&H search-result thumbnail (via r.jina.ai reader), download it to images/eq-*.jpg,
and point data.json at the local file so hover previews are not dead hotlinks.

Run ``python3 sync_eq_photos.py`` first when your shots live in ``~/Downloads/EQ list photos``;
that copies your photos into ``images/`` for every filename that fuzzy-matches a PDF line.
This script only fills rows that still have no album match after that.

This is the same discovery source as resolve_bh_previews.py, but persists bytes locally.

  python3 fill_missing_bh_images.py
  python3 fill_missing_bh_images.py --album "/path/to/EQ list photos"
  python3 fill_missing_bh_images.py --force   # redo download for all unmatched rows
"""
from __future__ import annotations

import argparse
import io
import json
import random
import re
import sys
import time
from pathlib import Path

from build_from_pdf import ROOT, apply_bh_urls_to_payload, image_stem

from resolve_bh_previews import (
    UA,
    bh_search_reader_url,
    fetch_url,
    parse_first_listing,
    search_query_for_item,
)

from sync_eq_photos import DEFAULT_SRC, album_matched_items, collect_items

DATA_PATH = ROOT / "data.json"
IMAGES = ROOT / "images"


_STATIC_BH_RE = re.compile(
    r"(https?://static\.bhphoto\.com/[^\s\")\]]+)", re.IGNORECASE
)


def bh_image_fetch_url(url: str) -> str:
    """B&H wraps thumbs in cdn-cgi URLs that return 403 to scripts; static host is open."""
    if "static.bhphoto.com" in url.lower():
        m = _STATIC_BH_RE.search(url)
        if m:
            return m.group(1).rstrip(").,]")
    return url


def download_thumbnail(url: str, dst: Path) -> bool:
    import urllib.request

    fetch_url = bh_image_fetch_url(url)
    req = urllib.request.Request(
        fetch_url,
        headers={
            "User-Agent": UA,
            "Referer": "https://www.bhphotovideo.com/",
            "Accept": "image/avif,image/webp,image/apng,image/*,*/*;q=0.8",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as resp:
            data = resp.read()
    except Exception as e:
        print(f"  download error: {e}", flush=True)
        return False
    if len(data) < 300:
        print("  download too small", flush=True)
        return False

    dst.parent.mkdir(parents=True, exist_ok=True)
    if data[:2] == b"\xff\xd8":
        dst.write_bytes(data)
        return True
    try:
        from PIL import Image  # type: ignore

        im = Image.open(io.BytesIO(data))
        im.convert("RGB").save(dst, "JPEG", quality=90)
        return True
    except Exception as e:
        print(f"  JPEG convert error: {e}", flush=True)
        return False


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--album",
        type=Path,
        default=DEFAULT_SRC,
        help="Album folder used to decide which rows are 'missing' (default: ~/Downloads/EQ list photos)",
    )
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-fetch every row not covered by the album (even if local image already exists).",
    )
    args = ap.parse_args()

    if not DATA_PATH.exists():
        print("Missing data.json", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    apply_bh_urls_to_payload(payload)

    covered = album_matched_items(args.album)
    items_order = collect_items()
    missing_set = {it for it in items_order if it not in covered}

    ok = fail = skip = 0
    for g in payload.get("groups", []):
        for sub in g.get("subsections", []):
            for it in sub.get("items", []):
                item = it.get("item") or ""
                if item not in missing_set:
                    continue

                stem = image_stem(item)
                dst = IMAGES / f"{stem}.jpg"
                if dst.exists() and dst.stat().st_size > 500 and not args.force:
                    skip += 1
                    continue

                q = search_query_for_item(item)
                print(f"{item[:60]}…", flush=True)
                md = fetch_url(bh_search_reader_url(q))
                img_url, product_url = (None, None)
                if md:
                    img_url, product_url = parse_first_listing(md)

                if not img_url:
                    legacy = (it.get("bh_preview_url") or "").strip()
                    if legacy and "static.bhphoto.com" in legacy.lower():
                        img_url = legacy
                        print("  using stored B&H thumbnail URL", flush=True)

                if not img_url:
                    print("  (no B&H listing thumbnail)", flush=True)
                    fail += 1
                    time.sleep(1.2 + random.uniform(0, 0.5))
                    continue

                if download_thumbnail(img_url, dst):
                    it["image"] = f"images/{stem}.jpg"
                    it["bh_preview_url"] = ""
                    if product_url and not (it.get("bh_page_url") or "").strip():
                        it["bh_page_url"] = product_url
                    ok += 1
                    print(f"  saved {dst.name}", flush=True)
                else:
                    it["bh_preview_url"] = img_url
                    fail += 1
                    print("  kept remote bh_preview_url only", flush=True)

                DATA_PATH.write_text(
                    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
                )
                time.sleep(1.85 + random.uniform(0, 0.55))

    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Done. Downloaded {ok}, failed {fail}, skipped (existing file) {skip}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
