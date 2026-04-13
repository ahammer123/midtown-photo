#!/usr/bin/env python3
"""
Fill bh_preview_url (hover image) using B&H Photo search results.

Direct requests to bhphotovideo.com often return 403 from scripts. This tool uses
the public Jina reader mirror (r.jina.ai) to fetch search-result markdown, then
takes the first product listing's thumbnail + product URL.

Manual overrides in bh_links.json still set bh_page_url first; we try og:image on
that URL, then fall back to the same search flow if needed.

Usage:
  cd photo-kit-equipment-site
  python3 resolve_bh_previews.py              # fill missing previews only
  python3 resolve_bh_previews.py --force        # re-resolve every row
"""
from __future__ import annotations

import argparse
import json
import random
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from build_from_pdf import ROOT, apply_bh_urls_to_payload

DATA_PATH = ROOT / "data.json"
UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)

# Thumbnail markdown: [![...](IMAGE)](PRODUCT.html)
_SEARCH_CARD_RE = re.compile(
    r"\[\!\[[^\]]*\]\("
    r'(https://[^)]*(?:bhphoto|bhphotovideo)[^)]*\.(?:jpg|jpeg|png|webp)[^)]*)\)'
    r'\]\((https://www\.bhphotovideo\.com/c/product/\d+-REG/[^)\s]+\.html)\)',
    re.IGNORECASE,
)


def jina_wrap(url: str) -> str:
    u = url.strip()
    if u.startswith("https://"):
        rest = u[len("https://") :]
    elif u.startswith("http://"):
        rest = u[len("http://") :]
    else:
        rest = u
    return "https://r.jina.ai/http://" + rest


def fetch_url(url: str, timeout: float = 60.0, retries: int = 5) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    for attempt in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=timeout) as resp:
                return resp.read().decode("utf-8", errors="replace")
        except urllib.error.HTTPError as e:
            if e.code == 429 and attempt < retries - 1:
                wait = 25 * (attempt + 1) + random.uniform(2, 18)
                print(f"  rate-limited (429), waiting {wait:.0f}s…", flush=True)
                time.sleep(wait)
                continue
            print(f"  HTTP {e.code}", flush=True)
            return None
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(5 + random.uniform(0, 4))
                continue
            print(f"  {e}", flush=True)
            return None
    return None


def extract_social_image(html: str, base_url: str) -> str | None:
    patterns = [
        r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)["\']',
        r'<meta\s+content=["\']([^"\']+)["\']\s+property=["\']og:image["\']',
        r'<meta\s+name=["\']twitter:image["\']\s+content=["\']([^"\']+)["\']',
    ]
    for pat in patterns:
        m = re.search(pat, html, re.I | re.DOTALL)
        if m:
            url = m.group(1).strip()
            if url:
                return urllib.parse.urljoin(base_url, url)
    return None


def search_query_for_item(item: str) -> str:
    return item.split("(", 1)[0].strip()


def bh_search_reader_url(query: str) -> str:
    ntt = urllib.parse.quote(query, safe="")
    return jina_wrap(f"https://www.bhphotovideo.com/c/search?Ntt={ntt}")


def parse_first_listing(markdown: str) -> tuple[str | None, str | None]:
    """Return (image_url, product_page_url) from B&H search markdown."""
    m = _SEARCH_CARD_RE.search(markdown)
    if not m:
        return None, None
    img, page = m.group(1).strip(), m.group(2).strip()
    # Larger hover preview when B&H uses cdn-cgi width=
    img = re.sub(r"width=\d+", "width=800", img, count=1)
    return img, page


def resolve_preview_for_row(it: dict, *, force: bool) -> str:
    """Return 'updated', 'skipped', or 'noop'."""
    item = it.get("item") or ""
    label = item[:52]
    manual_page = (it.get("bh_page_url") or "").strip()
    have = (it.get("bh_preview_url") or "").strip()
    if have and not force:
        return "skipped"

    img_url: str | None = None
    product_url: str | None = None

    if manual_page and re.match(r"^https?://", manual_page, re.I):
        print(f"Manual page: {label}…", flush=True)
        html = fetch_url(manual_page)
        if html:
            img_url = extract_social_image(html, manual_page)
        if not img_url:
            md = fetch_url(jina_wrap(manual_page))
            if md and "security verification" not in md.lower():
                img_url, product_url = parse_first_listing(md)
            if not img_url and md:
                img_url = extract_social_image(md, manual_page)

    if not img_url:
        q = search_query_for_item(item)
        print(f"Search B&H: {q[:52]}…", flush=True)
        md = fetch_url(bh_search_reader_url(q))
        if md:
            img_url, product_url = parse_first_listing(md)

    if product_url and not manual_page:
        it["bh_page_url"] = product_url

    if img_url:
        it["bh_preview_url"] = img_url
        print(f"  OK thumbnail", flush=True)
        return "updated"

    it["bh_preview_url"] = ""
    print(f"  (no listing thumbnail)", flush=True)
    return "noop"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--force",
        action="store_true",
        help="Re-resolve every row (ignore existing bh_preview_url).",
    )
    args = ap.parse_args()

    if not DATA_PATH.exists():
        print("Missing data.json — run: python3 build_from_pdf.py", file=sys.stderr)
        sys.exit(1)

    payload = json.loads(DATA_PATH.read_text(encoding="utf-8"))
    apply_bh_urls_to_payload(payload)

    updated = skipped = noop = 0
    for g in payload.get("groups", []):
        for sub in g.get("subsections", []):
            for it in sub.get("items", []):
                r = resolve_preview_for_row(it, force=args.force)
                if r == "updated":
                    updated += 1
                elif r == "skipped":
                    skipped += 1
                else:
                    noop += 1
                DATA_PATH.write_text(
                    json.dumps(payload, indent=2) + "\n", encoding="utf-8"
                )
                time.sleep(1.85 + random.uniform(0, 0.6))

    DATA_PATH.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"Done. Updated {updated}, skipped {skipped}, no match {noop}.",
        flush=True,
    )


if __name__ == "__main__":
    main()
