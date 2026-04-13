#!/usr/bin/env python3
"""
Rebuild data.json from PHOTO_KIT_EQ_LIST.pdf copy only (no other sources).
Hover photos: run sync_eq_photos.py against ~/Downloads/EQ list photos (see PHOTO_KIT_EQ_ALBUM).
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PDF_NOTICE = (
    "Insurance certificate and ID may be required. "
    "Replacement value charged for loss or damage."
)
# Page-2 extract truncates the same line; PDF source of truth is the complete notice above.

# (subsection_title or None to omit heading, list of (qty, item, price))
# Item and price strings match the PDF text extraction exactly.
GROUPS: list[tuple[str, list[tuple[str | None, list[tuple[int, str, str]]]]]] = [
    (
        "I. GRIP & SUPPORT",
        [
            (
                "Stands & specialized support",
                [
                    (1, "Tre-D Delta 4 heavy-duty professional light stand (Mod. 7731)", "$10"),
                    (10, "Manfrotto Auto Poles (painted studio poles)", "$15"),
                    (9, "Matthews C-Stands (standard turtle base)", "$10"),
                    (1, 'Matthews 20" baby C-Stand', "$9"),
                    (1, "Avenger D520LB mini boom with clamp", "$13"),
                    (8, "Aluminum kit light stands (Manfrotto, Avenger, Impact, assorted)", "$8"),
                    (6, "Floor / backlight stands", "$5"),
                    (4, "Matthews apple boxes (full)", "$5"),
                    (6, "Sandbags (25 lb)", "$5"),
                    (1, "Pumpkin weight (studio shot bag)", "$5"),
                ],
            ),
            (
                "Mounting & hardware",
                [
                    (7, "Matthews Super Clamps", "$4"),
                    (1, 'Matthews Magic Finger with 5/8" stud adapter', "$8"),
                    (1, 'Matthews 3" baby plate', "$8"),
                    (1, 'Matthews mounting plate with 5/8" receiver', "$8"),
                    (2, '6" Matthews grip head pins with collar', "$6"),
                    (
                        2,
                        "Avenger snap-in 5/8\" aluminum spigots (Super Clamp accessory)",
                        "$5",
                    ),
                    (1, "Right-angle snap-in pin (Mafer-style clamp accessory)", "$6"),
                    (1, "Junior-to-baby pin adapter", "$6"),
                    (6, "J-hooks (assorted)", "$5"),
                    (1, "A-clamps (assorted small & medium), set", "$4"),
                ],
            ),
            (
                "Light control (flags, scrims & gobos)",
                [
                    (
                        1,
                        'Impact PortaFrame scrim kit (18 x 24") with fingers & dots',
                        "$25",
                    ),
                    (1, "2 x 3' flag kit (assorted frames & fabrics)", "$18"),
                    (2, "Gobos (additional, assorted patterns)", "$8"),
                ],
            ),
        ],
    ),
    (
        "II. ELECTRIC & POWER",
        [
            (
                None,
                [
                    (12, "AC stingers (extension cords)", "$5"),
                    (1, "PC sync cable set", "$5"),
                ],
            ),
        ],
    ),
    (
        "III. LIGHTING SYSTEMS",
        [
            (
                "Elinchrom AC strobe - power packs",
                [
                    (1, "Elinchrom 6000 Ws Digital RX power pack", "$125"),
                    (4, "Elinchrom 2400 Ws Digital RX power pack", "$95"),
                    (2, "Elinchrom 1200 Ws Digital RX power pack", "$75"),
                ],
            ),
            (
                "Elinchrom AC strobe - heads",
                [
                    (2, "Elinchrom 6000 Ws bi-tube head", "$40"),
                    (4, "Elinchrom 3000 Ws head", "$30"),
                    (6, "Elinchrom 2000 Ws head", "$25"),
                    (2, "Elinchrom 1000 Ws head", "$17"),
                ],
            ),
            (
                "Battery-powered & portable flash",
                [
                    (1, "Godox AD600 Pro TTL monolight", "$50"),
                    (1, "Godox AD400 Pro TTL monolight", "$40"),
                    (1, "Godox AD200 Pro TTL pocket flash", "$25"),
                    (1, "Godox V350-F TTL speedlight (Fujifilm)", "$14"),
                    (1, "LightPix Labs FlashQ M20 compact flash", "$14"),
                ],
            ),
            (
                "Continuous lighting (tungsten)",
                [
                    (1, "Mole-Richardson Molette 1K bare", "$20"),
                    (1, "Lowell Omni-light 1K open-face tungsten fixture", "$15"),
                    (2, "ARRI 650 Plus tungsten Fresnel", "$30"),
                    (2, "ARRI 300 Plus / 350W tungsten Fresnel", "$30"),
                    (1, "ARRI 150 tungsten Fresnel", "$15"),
                ],
            ),
        ],
    ),
    (
        "IV. LIGHT MODIFIERS",
        [
            (
                "Softboxes & diffusion",
                [
                    (1, "Elinchrom Rotalux / standard 3 x 3' softbox", "$18"),
                    (2, "Elinchrom 6' x 6' large softbox / bank", "$35"),
                    (1, 'Photoflex 48" x 66" large softbox/bank', "$30"),
                    (1, "Photoflex large 7' Octabank", "$30"),
                    (4, "2 x 3' softboxes (assorted brands)", "$14"),
                    (
                        3,
                        "Chimera soft banks - 1 x 1x4', 2 x 2x4' strip / frame kits",
                        "$25",
                    ),
                    (6, "Speed rings (Elinchrom / Bowens / assorted)", "$9"),
                ],
            ),
            (
                None,
                [
                    (
                        6,
                        "Umbrellas (small / medium / large, two each) with diffusion socks",
                        "$12",
                    ),
                ],
            ),
            (
                "Hard reflectors & specialty",
                [
                    (
                        10,
                        "Elinchrom reflector set (standard, wide & Magnum-style) with grids, assorted sizes",
                        "$12",
                    ),
                    (1, "Elinchrom beauty dish with fabric / metal grids", "$25"),
                    (1, "Elinchrom Super Zoom Spot optical snoot", "$45"),
                    (1, "Mini Spot Lite tabletop focusing spot", "$18"),
                    (1, "Elinchrom bayonet snoot", "$9"),
                    (1, "Bowens-mount snoot", "$9"),
                ],
            ),
        ],
    ),
    (
        "V. CAMERA & OPTICS",
        [
            (
                "Camera bodies",
                [
                    (1, "Hasselblad 500C/M medium-format film body", "$135"),
                    (1, "Fujifilm X-T5 digital mirrorless body", "$110"),
                    (1, "Fujifilm X-T4 digital mirrorless body", "$80"),
                    (1, "Canon EOS 5D Mark II digital SLR body", "$45"),
                    (1, "Canon EOS 30D digital SLR body", "$18"),
                    (1, "Canon EOS Rebel T6 digital SLR body", "$18"),
                    (1, "Nikon F2 35mm film body", "$25"),
                    (1, "Polaroid I-2 instant camera", "$45"),
                ],
            ),
            (
                "Lenses - Hasselblad V-mount",
                [
                    (1, "Carl Zeiss Distagon T* 50mm f/4 CF", "$40"),
                    (1, "Carl Zeiss Planar T* 80mm f/2.8 CF", "$35"),
                    (1, "Carl Zeiss Sonnar T* 150mm f/4 CF", "$40"),
                ],
            ),
            (
                "Lenses - Fujifilm X-mount",
                [
                    (1, "Fujinon XF 80mm f/2.8 R LM OIS WR Macro", "$35"),
                    (1, "Fujinon XF 16-55mm f/2.8-4 R LM OIS", "$35"),
                    (1, "Fujinon XF 18-135mm f/3.5-5.6 R LM OIS WR", "$35"),
                    (1, "Fujinon XC 18-55mm f/3.5-5.6 OIS", "$20"),
                    (2, "Fujinon XF 23mm f/2 R WR", "$20"),
                    (1, "Fujinon XF 35mm f/2 R WR", "$20"),
                ],
            ),
            (
                "Lenses - Nikon F-mount",
                [
                    (1, "Nikon Reflex-Nikkor 500mm f/8", "$25"),
                    (1, "Nikon Nikkor-S-C 35mm f/2.8", "$18"),
                    (1, "Nikon Nikkor-H-C 50mm f/2", "$18"),
                    (1, "Aetna Tele Rokunar 135mm f/2.5 telephoto lens", "$14"),
                ],
            ),
            (
                "Lenses - Canon EF / EF-S",
                [
                    (1, "Canon EF 24-105mm f/4L IS USM", "$40"),
                    (1, "Canon EF 17-40mm f/4L USM", "$25"),
                    (1, "Canon EF 75-300mm f/4-5.6 III USM", "$14"),
                    (1, "Canon EF 40mm f/2.8 STM", "$9"),
                    (1, "Canon EF-S 17-85mm f/4-5.6 IS USM", "$12"),
                    (1, "Canon EF-S 18-55mm f/3.5-5.6 IS II", "$12"),
                ],
            ),
            (
                "Mount adapters",
                [
                    (1, "Hasselblad V to Fujifilm X adapter", "$9"),
                    (1, "Nikon F to Fujifilm X adapter", "$9"),
                    (1, "Canon EOS (EF/EF-S) to Fujifilm X adapter", "$9"),
                    (1, "Minolta MD to Fujifilm X adapter", "$9"),
                ],
            ),
        ],
    ),
    (
        "VI. DIGITAL, METERING & TOOLS",
        [
            (
                "Exposure metering & wireless",
                [
                    (1, "Sekonic L-508 Zoom Master light meter", "$25"),
                    (1, "Sekonic L-358 Flash Master light meter", "$18"),
                    (1, "Godox X wireless trigger system (Canon, Fujifilm, Sony)", "$10"),
                    (1, "PocketWizard Plus transceiver set", "$18"),
                ],
            ),
            (
                "Tech & calibration",
                [
                    (1, "X-Rite ColorMunki Photo spectrophotometer / calibration kit", "$25"),
                    (1, "Datacolor Spyder display calibration tool", "$14"),
                    (1, "White balance reference card (WB-CII)", "$4"),
                ],
            ),
            (
                "Camera support (tripods & heads)",
                [
                    (1, "Manfrotto 679B three-section monopod", "$12"),
                    (1, "Manfrotto 486RC2 ball head with RC2 quick release", "$12"),
                    (1, "Bogen / Manfrotto 3009 compact ball head", "$12"),
                    (1, "Triopo NB-2S ball head with quick-release plate", "$12"),
                ],
            ),
        ],
    ),
]


def image_stem(item: str) -> str:
    h = hashlib.sha256(item.encode("utf-8")).hexdigest()[:14]
    return f"eq-{h}"


BH_LINKS_PATH = ROOT / "bh_links.json"


def load_bh_links() -> dict:
    if not BH_LINKS_PATH.exists():
        return {}
    try:
        raw = json.loads(BH_LINKS_PATH.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}
    if not isinstance(raw, dict):
        return {}
    return {k: v for k, v in raw.items() if not str(k).startswith("_")}


def apply_bh_urls_to_payload(payload: dict) -> None:
    """Set bh_page_url from bh_links.json (B&H or any product page). bh_preview_url filled by resolve_bh_previews.py."""
    links = load_bh_links()
    for g in payload.get("groups", []):
        for sub in g.get("subsections", []):
            for it in sub.get("items", []):
                item = it.get("item") or ""
                row = links.get(item)
                page = ""
                if isinstance(row, str):
                    page = row.strip()
                elif isinstance(row, dict):
                    page = (
                        row.get("page") or row.get("url") or row.get("product") or ""
                    ).strip()
                it.pop("bh_product_url", None)
                it.pop("bh_image_url", None)
                it["bh_page_url"] = page
                if "bh_preview_url" not in it:
                    it["bh_preview_url"] = ""


def build_payload(*, with_placeholder_images: bool) -> dict:
    groups_out = []
    for section, subs in GROUPS:
        sub_out = []
        for sub_title, rows in subs:
            items = []
            for qty, item, price in rows:
                stem = image_stem(item)
                img = f"images/{stem}.jpg" if with_placeholder_images else ""
                items.append(
                    {
                        "quantity": qty,
                        "item": item,
                        "price": price,
                        "image": img,
                    }
                )
            sub_out.append({"title": sub_title, "items": items})
        groups_out.append({"section": section, "subsections": sub_out})

    payload = {
        "meta": {
            "source": "PHOTO_KIT_EQ_LIST.pdf (text only)",
            "notice": PDF_NOTICE,
            "title": "EQUIPMENT LIST",
            "rate_caption": "QTY  ITEM  DAY RATE",
            "image_attribution": (
                "Hover images: run sync_eq_photos.py to copy your photos from ~/Downloads/EQ list photos into images/."
            ),
        },
        "groups": groups_out,
    }
    apply_bh_urls_to_payload(payload)
    return payload


def main() -> None:
    out = ROOT / "data.json"
    payload = build_payload(with_placeholder_images=True)
    out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {out}")


if __name__ == "__main__":
    main()
