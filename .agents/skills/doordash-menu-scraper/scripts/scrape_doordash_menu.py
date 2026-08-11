#!/usr/bin/env python3
"""Scrape a DoorDash store menu via a running camofox-browser server.

No LLM involved: DoorDash serves the full menu as schema.org JSON-LD
(`script[type="application/ld+json"]`, `@type: "Menu"`) on first render, so
this is a single evaluate call and a parse, no scroll loop needed — unlike
Grubhub, which virtualizes its menu DOM (see scrape_grubhub_menu.py).
Validated live against Maria's Mexican Grill's DoorDash page (10 sections,
68 items recovered from one JSON-LD blob).

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[4]

JSONLD_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.textContent))
""".strip()


class CamofoxClient:
    def __init__(self, server: str, user_id: str) -> None:
        self.server = server.rstrip("/")
        self.user_id = user_id

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(f"{self.server}{path}", json={"userId": self.user_id, **body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            return requests.get(f"{self.server}/health", timeout=5).ok
        except requests.RequestException:
            return False

    def open_tab(self, url: str, lat: float, lon: float, timezone_id: str) -> str:
        resp = requests.post(
            f"{self.server}/tabs",
            json={
                "userId": self.user_id,
                "sessionKey": "default",
                "url": url,
                "locale": "en-US",
                "timezoneId": timezone_id,
                "geolocation": {"latitude": lat, "longitude": lon},
            },
            timeout=30,
        )
        resp.raise_for_status()
        return resp.json()["tabId"]

    def wait(self, tab_id: str, timeout_ms: int = 15000) -> None:
        self._post(f"/tabs/{tab_id}/wait", {"timeout": timeout_ms})

    def evaluate(self, tab_id: str, expression: str) -> Any:
        data = self._post(f"/tabs/{tab_id}/evaluate", {"expression": expression})
        result = data.get("result")
        if isinstance(result, str):
            try:
                return json.loads(result)
            except json.JSONDecodeError:
                return result
        return result

    def screenshot(self, tab_id: str) -> bytes | None:
        # The server returns a raw image/png body directly, not the
        # JSON-wrapped base64 the openapi.json spec describes.
        resp = requests.get(f"{self.server}/tabs/{tab_id}/screenshot", params={"userId": self.user_id}, timeout=30)
        resp.raise_for_status()
        return resp.content or None

    def close_tab(self, tab_id: str) -> None:
        try:
            requests.delete(f"{self.server}/tabs/{tab_id}", params={"userId": self.user_id}, timeout=10)
        except requests.RequestException:
            pass

    def close_session(self) -> None:
        try:
            requests.delete(f"{self.server}/sessions/{self.user_id}", timeout=10)
        except requests.RequestException:
            pass


def menu_dir(slug: str) -> Path:
    return ROOT / "external-data" / "menu-scraping" / slug


def resolve_url(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.url:
        return args.url, {}

    sources_path = args.sources_file or (menu_dir(args.restaurant_slug) / "sources.json")
    if sources_path.exists():
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        doordash = (sources.get("platforms") or {}).get("doordash") or {}
        if doordash.get("url"):
            return doordash["url"], sources

    print(
        f"No --url given and no platforms.doordash.url in {sources_path}.\n"
        "Pass --url explicitly, or run restaurant source discovery first.",
        file=sys.stderr,
    )
    sys.exit(2)


def flatten(value: Any) -> list[dict[str, Any]]:
    # DoorDash's hasMenuSection/hasMenuItem values can be nested lists
    # (confirmed live: a single-element list wrapping the real list).
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for child in value:
            items.extend(flatten(child))
        return items
    return []


def slugify(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "section"


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def scrape(args: argparse.Namespace) -> None:
    url, sources = resolve_url(args)
    lat = args.latitude if args.latitude is not None else ((sources.get("restaurant") or {}).get("latitude"))
    lon = args.longitude if args.longitude is not None else ((sources.get("restaurant") or {}).get("longitude"))
    if lat is None or lon is None:
        print("Missing --latitude/--longitude and none found in sources.json.", file=sys.stderr)
        sys.exit(2)

    out_dir = menu_dir(args.restaurant_slug)
    raw_dir = out_dir / "menus" / "raw"
    raw_dir.mkdir(parents=True, exist_ok=True)

    client = CamofoxClient(args.server, args.user or f"doordash-{args.restaurant_slug}")
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(url, lat, lon, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass

        shot = client.screenshot(tab_id)
        if shot:
            (raw_dir / f"doordash-{args.restaurant_slug}-evidence.png").write_bytes(shot)

        raw_scripts = client.evaluate(tab_id, JSONLD_JS) or []
    finally:
        client.close_tab(tab_id)
        client.close_session()

    response_path = raw_dir / "doordash-jsonld-response.json"
    response_path.write_text(
        json.dumps({"ok": True, "result": raw_scripts, "resultType": "array", "truncated": False, "url": url}, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    parsed_scripts = []
    for raw in raw_scripts:
        try:
            parsed_scripts.append(json.loads(raw))
        except json.JSONDecodeError:
            continue

    restaurant_ld = next((s for s in parsed_scripts if s.get("@type") == "Restaurant"), {})
    menu_ld = next((s for s in parsed_scripts if s.get("@type") == "Menu"), {})

    if not menu_ld:
        types_found = [s.get("@type") for s in parsed_scripts]
        print(
            f"No JSON-LD 'Menu' object found (types present: {types_found}). "
            "This usually means a Cloudflare interstitial, a search results page, or the wrong URL — "
            f"not proof the restaurant has no DoorDash listing. Evidence saved under {raw_dir}.",
            file=sys.stderr,
        )
        sys.exit(2)

    sections = []
    for section_ld in flatten(menu_ld.get("hasMenuSection")):
        items = []
        for item_ld in flatten(section_ld.get("hasMenuItem")):
            name = clean(item_ld.get("name"))
            if not name:
                continue
            offers = item_ld.get("offers")
            price = offers.get("price") if isinstance(offers, dict) else None
            items.append(
                {
                    # DoorDash's JSON-LD MenuItem objects carry no id field at
                    # all (confirmed live) — identity relies on name/price
                    # within a section, not a stable platform id.
                    "platform_item_id": "",
                    "name": name,
                    "description": clean(item_ld.get("description")),
                    "price_text": clean(price),
                    "raw_text": "",
                    "source_category_id": "",
                }
            )
        section_name = clean(section_ld.get("name")) or "Unnamed Section"
        sections.append({"name": section_name, "platform_section_id": slugify(section_name), "items": items})

    address = args.address
    if not address:
        addr_ld = restaurant_ld.get("address")
        if isinstance(addr_ld, dict):
            address = ", ".join(
                clean(addr_ld.get(k)) for k in ("streetAddress", "addressLocality", "addressRegion", "postalCode") if addr_ld.get(k)
            )

    output = {
        "source": "doordash",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "restaurant": {
            "name": args.restaurant_name,
            "slug": args.restaurant_slug,
            "platform_name": clean(restaurant_ld.get("name")) or args.restaurant_name,
            "url": url,
            "address": address,
        },
        "menu": {"sections": sections},
        "raw_artifacts": [str(response_path.relative_to(ROOT))],
        "extraction_notes": {
            "method": "DoorDash JSON-LD extraction (scripted, no LLM)",
            "canonicalized": False,
            "note": "DoorDash JSON-LD exposes no per-item platform id; identity relies on (section, name, price).",
        },
    }

    out_path = out_dir / "menus" / f"doordash-menu-{args.restaurant_slug}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    item_count = sum(len(s["items"]) for s in sections)
    print(f"Wrote {out_path.relative_to(ROOT)} — {len(sections)} sections, {item_count} items")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurant-slug", required=True)
    parser.add_argument("--restaurant-name", required=True)
    parser.add_argument("--address", default="")
    parser.add_argument("--url", default="", help="DoorDash store URL. Falls back to sources.json if omitted.")
    parser.add_argument("--sources-file", type=Path, default=None)
    parser.add_argument("--latitude", type=float, default=None)
    parser.add_argument("--longitude", type=float, default=None)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="", help="camofox profile id (default: doordash-<slug>)")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
