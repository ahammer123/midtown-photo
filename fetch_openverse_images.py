#!/usr/bin/env python3
"""
Download one preview image per equipment row from Openverse (legal CC catalog).
Favors CC0/PDM, then CC BY. Not every result is a white seamless product shot—
queries include 'white background' / 'isolated' to bias toward clean looks.
"""
from __future__ import annotations

import json
import re
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from build_from_pdf import ROOT, apply_bh_urls_to_payload, image_stem

UA = "PhotoKitEquipmentList/1.0 (local; Openverse API)"
IMAGES_DIR = ROOT / "images"
CREDITS_PATH = ROOT / "image_credits.json"
DATA_PATH = ROOT / "data.json"
API = "https://api.openverse.engineering/v1/images/"


def search_openverse(query: str, license_param: str | None) -> list[dict]:
    qd: dict[str, str | int] = {"q": query, "page_size": 8}
    if license_param:
        qd["license"] = license_param
    params = urllib.parse.urlencode(qd)
    url = f"{API}?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = json.loads(resp.read().decode())
    return data.get("results") or []


def alpha_tokens(item: str) -> list[str]:
    """Words from the item (before parentheses), dropping tokens that contain digits."""
    base = item.split("(")[0]
    base = base.replace('"', "").replace("'", "")
    parts = re.split(r"[^\w]+", base)
    return [p for p in parts if len(p) > 1 and not any(c.isdigit() for c in p)]


def build_queries(item: str) -> list[str]:
    # Openverse returns 0 hits for long, highly specific strings; prefer short tails + generics.
    toks = alpha_tokens(item)
    blob = " ".join(toks).lower()
    out: list[str] = []

    def add(q: str) -> None:
        q = re.sub(r"\s+", " ", q).strip()
        if q and q not in out:
            out.append(q)

    for n in (5, 4, 3):
        if len(toks) >= n:
            add(" ".join(toks[-n:]) + " photography")

    # Category fallbacks (broad but usually return hits)
    if "softbox" in blob or "octabank" in blob or "rotalux" in blob:
        add("photography softbox studio")
    if "umbrella" in blob:
        add("photography umbrella lighting")
    if "snoot" in blob or "spot" in blob:
        add("studio lighting snoot")
    if "reflector" in blob or "beauty dish" in blob:
        add("photography reflector dish")
    if "fresnel" in blob or "tungsten" in blob or "arri" in blob:
        add("tungsten fresnel studio light")
    if "monolight" in blob or "strobe" in blob or "elinchrom" in blob or "godox" in blob:
        add("studio strobe monolight")
    if "speedlight" in blob or "speed ring" in blob or ("pocket" in blob and "flash" in blob):
        add("camera flash speedlight")
    if "sync" in blob or "stinger" in blob or "extension cord" in blob:
        add("heavy duty extension cord")
    if "clamp" in blob or "mafer" in blob or "super clamp" in blob:
        add("grip super clamp studio")
    il = item.lower()
    if "c-stand" in il or "c-stands" in il:
        add("c stand grip photography")
    if "stand" in blob and "light" in blob:
        add("studio light stand photography")
    if "stand" in blob:
        add("light stand studio")
    if "tripod" in blob or "monopod" in blob:
        add("camera tripod monopod")
    if "ball head" in blob:
        add("tripod ball head")
    if "lens" in blob or "mm" in item or "nikkor" in blob or "canon ef" in blob or "fujinon" in blob or "zeiss" in blob or "distagon" in blob:
        add("camera lens product photography")
    if "body" in blob or "camera" in blob and "lens" not in blob:
        add("camera body photography")
    if "meter" in blob or "sekonic" in blob:
        add("light meter photography")
    if "polaroid" in blob or "hasselblad" in blob or "fujifilm" in blob:
        add("vintage camera photography")
    if "gobo" in blob or "scrim" in blob or "flag" in blob:
        add("photography scrim flag lighting")
    if "sandbag" in blob or "weight" in blob:
        add("studio sandbag weight bag")
    if "apple box" in blob:
        add("film production apple boxes")
    if "adapter" in blob and "mount" in blob:
        add("camera lens mount adapter")
    if "spigot" in blob or "stud" in blob or "receiver" in blob or "pin adapter" in blob:
        add("lighting grip stud adapter")
    if "j-hook" in blob.replace(" ", "") or "j hook" in blob:
        add("studio cable hook")
    if "boom" in blob:
        add("studio boom arm light")
    if "pocketwizard" in blob or "wireless" in blob and "trigger" in blob:
        add("radio flash trigger photography")
    if "munki" in blob or "spyder" in blob or "calibration" in blob:
        add("monitor calibration tool")
    if "white balance" in blob:
        add("white balance card photography")
    if "pole" in blob:
        add("photography backdrop pole")
        add("studio lighting pole")

    add("photography equipment studio")
    return out


def pick_result(results: list[dict]) -> dict | None:
    if not results:
        return None
    # Prefer larger images for clearer hover preview
    def score(r: dict) -> tuple[int, int]:
        w = r.get("width") or 0
        h = r.get("height") or 0
        return (min(w, h), w * h)

    return sorted(results, key=score, reverse=True)[0]


def download_file(url: str, dest: Path) -> None:
    dest.parent.mkdir(parents=True, exist_ok=True)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=60) as resp:
        dest.write_bytes(resp.read())


def main() -> None:
    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    apply_bh_urls_to_payload(payload)
    credits: list[dict] = []
    if CREDITS_PATH.exists():
        try:
            credits = json.loads(CREDITS_PATH.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, OSError):
            credits = []
    credited_items = {c.get("item") for c in credits if c.get("item")}
    license_tiers: list[str | None] = ["cc0,pdm", "by,by-sa", None]

    total = sum(
        len(sub["items"]) for g in payload["groups"] for sub in g["subsections"]
    )
    done = 0

    for g in payload["groups"]:
        for sub in g["subsections"]:
            for it in sub["items"]:
                item = it["item"]
                stem = image_stem(item)
                dest = IMAGES_DIR / f"{stem}.jpg"
                done += 1

                if dest.exists() and dest.stat().st_size > 500:
                    if item not in credited_items:
                        credits.append(
                            {
                                "item": item,
                                "note": "Image from an earlier fetch; Openverse attribution was not checkpointed—replace or re-fetch for full license metadata.",
                            }
                        )
                        credited_items.add(item)
                    print(f"[{done}/{total}] skip (exists): {item[:50]}…", flush=True)
                    continue

                chosen = None
                for lic in license_tiers:
                    for q in build_queries(item):
                        try:
                            results = search_openverse(q, lic)
                        except urllib.error.HTTPError as e:
                            print("HTTPError", e.code, q[:60], flush=True)
                            time.sleep(1.0)
                            continue
                        except Exception as e:
                            print("Error", e, q[:60], flush=True)
                            time.sleep(1.0)
                            continue
                        chosen = pick_result(results)
                        if chosen:
                            break
                        time.sleep(0.25)
                    if chosen:
                        break

                if not chosen:
                    print(f"[{done}/{total}] NO IMAGE: {item}", flush=True)
                    it["image"] = ""
                    time.sleep(0.3)
                    continue

                img_url = chosen.get("url") or chosen.get("thumbnail")
                if not img_url:
                    it["image"] = ""
                    continue
                try:
                    download_file(img_url, dest)
                except Exception as e:
                    print(f"Download failed {item}: {e}", flush=True)
                    it["image"] = ""
                    time.sleep(0.5)
                    continue

                it["image"] = f"images/{stem}.jpg"
                if item not in credited_items:
                    credits.append(
                        {
                            "item": item,
                            "openverse_id": chosen.get("id"),
                            "title": chosen.get("title"),
                            "creator": chosen.get("creator"),
                            "license": chosen.get("license"),
                            "license_url": chosen.get("license_url"),
                            "source_url": chosen.get("foreign_landing_url"),
                            "file_url": img_url,
                            "attribution": chosen.get("attribution"),
                        }
                    )
                    credited_items.add(item)
                print(f"[{done}/{total}] ok: {item[:55]}…", flush=True)
                time.sleep(0.35)
                # Checkpoint so an interrupted run keeps credits + strips image_stem.
                CREDITS_PATH.write_text(
                    json.dumps(credits, indent=2) + "\n", encoding="utf-8"
                )
                DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")

    CREDITS_PATH.write_text(json.dumps(credits, indent=2) + "\n", encoding="utf-8")
    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {CREDITS_PATH} ({len(credits)} entries)", flush=True)


if __name__ == "__main__":
    main()
