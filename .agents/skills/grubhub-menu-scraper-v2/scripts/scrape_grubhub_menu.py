#!/usr/bin/env python3
"""Scrape a Grubhub restaurant menu via a running camofox-browser server.

No LLM involved: the DOM structure this relies on was validated against a
live Grubhub page (see references/grubhub-virtualized-menu-layout.md). This
mechanically reproduces the skill's scroll/extract/dedupe workflow, which is
pure plumbing and doesn't need model judgment.

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

# Must stay in sync with the "Extraction Snippet" section of ../SKILL.md.
EXTRACT_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('article.restaurant-menu-item')).map(article => {
  const btn = article.querySelector('button.restaurant-menu-item__button') || article;
  const wrapper = article.closest('[data-testid^="Item"]');
  const testid = wrapper ? wrapper.getAttribute('data-testid') : '';
  const m = /^Item(\d+)-(.+)$/.exec(testid || '');
  const wrapperItemId = m ? m[1] : '';
  const categorySegment = m ? m[2] : '';
  const text = btn.innerText.trim();
  const nameNode = article.querySelector('[data-testid="menu-item-name-container"] h6, h3, h4');
  const name = (nameNode ? nameNode.innerText : '') || text.split('\n')[0] || '';
  const categoryName = categorySegment === 'popularItems'
    ? 'Best Sellers'
    : (wrapper ? (wrapper.getAttribute('impressionid') || '') : '');
  return {
    id: btn.getAttribute('impressionid') || wrapperItemId || '',
    category_id: categorySegment || '',
    category_name: categoryName,
    name: name,
    description: (article.querySelector('[data-testid="menu-item-description"]') || {}).innerText || '',
    button_text: text,
    price: (article.querySelector('[data-testid="menu-item-price"]') || {}).innerText
      || (text.match(/\$[\d.]+\+?/) || [''])[0],
  };
}))
""".strip()

SCROLL_JS = "window.scrollBy(0, Math.round(window.innerHeight * 0.7)); null"

CATEGORY_TABS_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('li[role="tab"]')).map(el => (el.innerText || '').trim()).filter(Boolean))
""".strip()


class CamofoxClient:
    def __init__(self, server: str, user_id: str) -> None:
        self.server = server.rstrip("/")
        self.user_id = user_id

    def _post(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(f"{self.server}{path}", json={"userId": self.user_id, **body}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def _get(self, path: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = requests.get(f"{self.server}{path}", params={"userId": self.user_id, **(params or {})}, timeout=30)
        resp.raise_for_status()
        return resp.json()

    def health(self) -> bool:
        try:
            resp = requests.get(f"{self.server}/health", timeout=5)
            return resp.ok
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
        resp = requests.get(
            f"{self.server}/tabs/{tab_id}/screenshot",
            params={"userId": self.user_id},
            timeout=30,
        )
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


def resolve_url(args: argparse.Namespace) -> tuple[str, dict[str, Any]]:
    if args.url:
        return args.url, {}

    sources_path = args.sources_file or (menu_dir(args.restaurant_slug) / "sources.json")
    if sources_path.exists():
        sources = json.loads(sources_path.read_text(encoding="utf-8"))
        grubhub = (sources.get("platforms") or {}).get("grubhub") or {}
        if grubhub.get("url"):
            return grubhub["url"], sources

    print(
        f"No --url given and no platforms.grubhub.url in {sources_path}.\n"
        "Pass --url explicitly, or run restaurant source discovery first.",
        file=sys.stderr,
    )
    sys.exit(2)


def menu_dir(slug: str) -> Path:
    return ROOT / "external-data" / "menu-scraping" / slug


def clean(value: Any) -> str:
    if value is None:
        return ""
    return re.sub(r"\s+", " ", str(value)).strip()


def dedupe_key(item: dict[str, Any]) -> tuple[str, str, str, str]:
    category_key = item.get("category_id") or item.get("category_name") or ""
    return (category_key, item.get("id", ""), item.get("name", ""), item.get("price", ""))


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

    client = CamofoxClient(args.server, args.user or f"grubhub-{args.restaurant_slug}")
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(url, lat, lon, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass

        shot = client.screenshot(tab_id)
        if shot:
            (raw_dir / f"grubhub-{args.restaurant_slug}-evidence.png").write_bytes(shot)

        category_tabs = client.evaluate(tab_id, CATEGORY_TABS_JS) or []

        accumulator: dict[tuple[str, str, str, str], dict[str, Any]] = {}
        stalls = 0
        stop = 0
        while stalls < args.max_stalls and stop < args.max_scrolls:
            stop += 1
            items = client.evaluate(tab_id, EXTRACT_JS) or []
            new_keys = 0
            for item in items:
                key = dedupe_key(item)
                if key not in accumulator:
                    new_keys += 1
                accumulator[key] = item
            stalls = stalls + 1 if new_keys == 0 else 0
            print(f"  stop {stop}: mounted={len(items)} new={new_keys} total_unique={len(accumulator)} stalls={stalls}")
            client.evaluate(tab_id, SCROLL_JS)
            time.sleep(1.0)

        seen_categories = {item.get("category_name") for item in accumulator.values() if item.get("category_name")}
        missing_tabs = [t for t in category_tabs if t not in seen_categories and "Best Seller" not in t]
        if missing_tabs:
            print(f"  warning: category tabs with no extracted items: {missing_tabs}", file=sys.stderr)

    finally:
        client.close_tab(tab_id)
        client.close_session()

    raw_items = list(accumulator.values())
    raw_path = raw_dir / "grubhub-scroll-extracted-menu-raw.json"
    raw_path.write_text(json.dumps({"items": raw_items, "category_tabs": category_tabs}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    sections: dict[str, dict[str, Any]] = {}
    for item in raw_items:
        section_key = item.get("category_id") or item.get("category_name") or "unknown"
        section = sections.setdefault(
            section_key,
            {"name": item.get("category_name") or section_key, "platform_section_id": item.get("category_id") or section_key, "items": []},
        )
        section["items"].append(
            {
                "platform_item_id": clean(item.get("id")),
                "name": clean(item.get("name")),
                "description": clean(item.get("description")),
                "price_text": clean(item.get("price")),
                "raw_text": clean(item.get("button_text")),
                "source_category_id": clean(item.get("category_id") or item.get("category_name")),
            }
        )

    output = {
        "source": "grubhub",
        "captured_at": datetime.now(timezone.utc).isoformat(),
        "restaurant": {
            "name": args.restaurant_name,
            "slug": args.restaurant_slug,
            "platform_name": args.restaurant_name,
            "url": url,
            "address": args.address or "",
        },
        "menu": {"sections": list(sections.values())},
        "raw_artifacts": [str(raw_path.relative_to(ROOT))],
        "extraction_notes": {"method": "Grubhub scroll extraction (scripted, no LLM)", "canonicalized": False},
    }

    out_path = out_dir / "menus" / f"grubhub-menu-{args.restaurant_slug}.json"
    out_path.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    item_count = sum(len(s["items"]) for s in output["menu"]["sections"])
    print(f"Wrote {out_path.relative_to(ROOT)} — {len(output['menu']['sections'])} sections, {item_count} items")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--restaurant-slug", required=True)
    parser.add_argument("--restaurant-name", required=True)
    parser.add_argument("--address", default="")
    parser.add_argument("--url", default="", help="Grubhub restaurant URL. Falls back to sources.json if omitted.")
    parser.add_argument("--sources-file", type=Path, default=None)
    parser.add_argument("--latitude", type=float, default=None)
    parser.add_argument("--longitude", type=float, default=None)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="", help="camofox profile id (default: grubhub-<slug>)")
    parser.add_argument("--max-stalls", type=int, default=3)
    parser.add_argument("--max-scrolls", type=int, default=60)
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
