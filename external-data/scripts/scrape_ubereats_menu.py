#!/usr/bin/env python3
"""Scrape an Uber Eats restaurant menu via a running camofox-browser server.

Companion to parse_ubereats_jsonld.py, which already does the JSON-LD +
DOM-ratings merge - this script only captures the two raw inputs that
parser expects, each written in the exact {"result": [...]} shape a
camofox-browser REST `eval` call returns, so the existing parser (built
from prior interactive investigation of this platform, see its own
docstring) runs unmodified against this script's output.

Confirmed live against Camino Real Mexican Grill (Wyandotte)
(https://www.ubereats.com/store/camino-real-mexican-grill-wyandotte/QXhsSH0yVSeESCNVX6sQDQ):
counts matched the hand-captured dataset exactly - 115 items, 92 rated, 19
featured with ranks 1-3.

- Uber Eats embeds the menu's JSON-LD inside a `Restaurant` script's
  `hasMenu` field; parse_ubereats_jsonld.py reads that directly, so this
  script just dumps every `application/ld+json` script's text.
- Ratings, the "Featured items" carousel, and a separate "Popular" text
  badge are DOM-only (confirmed absent from JSON-LD). All three live on
  each item's card (`[data-testid^="store-item-<uuid>"]`):
    - Name: the first `[data-testid="item-thumbnail-label"]` block's
      `[data-testid="rich-text"]` span - not the image `alt`, which is
      missing entirely on cards with no photo.
    - Price + rating: the second `item-thumbnail-label` block holds a row
      of `rich-text` spans - price, a " • " separator, a thumbs-up icon,
      then "XX% (N)" when the item has any ratings at all.
    - Featured-carousel membership + rank: cards inside
      `li[data-testid="store-desktop-catalog-section-carousel"]` (the
      "Featured items" section's own container, confirmed to hold exactly
      the carousel's items and nothing else) are the featured set; the top
      few additionally carry a "#N most liked" leaf div somewhere in the
      card. Not every restaurant has this carousel at all.
    - Popular tag: a leaf div with the exact text "Popular", a sibling of
      the description - mutually exclusive with a rating on any single
      physical card, but the same dish name can appear on more than one
      card if it's duplicated across categories, so a name can legitimately
      end up with both after parse_ubereats_jsonld.py's merge (see that
      script's docstring for the specific example this was built from).
  This script emits one entry per physical card, duplicates across
  categories included - parse_ubereats_jsonld.py already does its own
  by-name dedup on the ratings dump, preferring the featured-carousel copy
  when a name appears more than once.

The whole menu (115 items on the sampled restaurant) was already mounted
without any scrolling, unlike DoorDash/Grubhub/Square's virtualized lists -
but this script still scrolls and polls the item count for stability before
reading it, in case a bigger menu on some other restaurant does lazy-mount.

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path
from typing import Any

import requests

JSONLD_JS = r"""
JSON.stringify(Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.textContent))
""".strip()

ITEM_COUNT_JS = 'document.querySelectorAll(\'[data-testid^="store-item-"]\').length'

EXTRACT_RATINGS_JS = r"""
(function() {
  const featuredContainer = document.querySelector('li[data-testid="store-desktop-catalog-section-carousel"]');
  const featuredTestids = new Set();
  if (featuredContainer) {
    featuredContainer.querySelectorAll('[data-testid^="store-item-"]').forEach(function(el) {
      featuredTestids.add(el.getAttribute('data-testid'));
    });
  }
  // A featured item's card shows up twice in the page - once inside the
  // carousel, once again in its real category section further down - and
  // both physical cards share the same "store-item-<uuid>" testid, since
  // it's the same underlying item. This deliberately emits one entry per
  // physical card, duplicates included: parse_ubereats_jsonld.py already
  // does its own by-name dedup on this dump, preferring whichever copy has
  // "in_featured_carousel" set, so it needs both occurrences present to
  // work exactly as it already does.
  const cards = Array.from(document.querySelectorAll('[data-testid^="store-item-"]'));
  return JSON.stringify(cards.map(function(card) {
    // Featured-carousel cards (vertical, image on top) and regular list
    // cards (horizontal, image on the right) use different DOM structure
    // entirely - only the "rich-text" testid is common to both, so scan
    // all of them in DOM order rather than relying on a shared container.
    const richTextSpans = Array.from(card.querySelectorAll('[data-testid="rich-text"]'));
    const name = richTextSpans.length ? richTextSpans[0].textContent.trim() : null;

    let price = null;
    let likePercent = null;
    let likeReviewCount = null;
    for (const span of richTextSpans.slice(1)) {
      const text = span.textContent.trim();
      const priceMatch = text.match(/^\$([\d.,]+)/);
      if (priceMatch) price = priceMatch[1];
      const ratingMatch = text.match(/(\d+)%\s*\((\d+)\)/);
      if (ratingMatch) {
        likePercent = parseInt(ratingMatch[1], 10);
        likeReviewCount = parseInt(ratingMatch[2], 10);
      }
    }

    let featuredRank = null;
    let isPopular = false;
    const leafDivs = Array.from(card.querySelectorAll('div')).filter(function(d) { return d.children.length === 0; });
    for (const div of leafDivs) {
      const text = div.textContent.trim();
      const rankMatch = text.match(/^#(\d+) most liked$/);
      if (rankMatch) featuredRank = parseInt(rankMatch[1], 10);
      if (text === 'Popular') isPopular = true;
    }

    return {
      name: name,
      in_featured_carousel: featuredTestids.has(card.getAttribute('data-testid')),
      price: price,
      featured_rank: featuredRank,
      like_percent: likePercent,
      like_review_count: likeReviewCount,
      is_popular: isPopular,
    };
  }).filter(function(entry) { return entry.name; }));
})()
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

    def click(self, tab_id: str, selector: str) -> bool:
        """Best-effort click by Playwright selector (CSS, text=, or role= engine
        syntax) - returns False rather than raising if nothing matched, since
        callers here use this for optional/defensive dismissals."""
        try:
            self._post(f"/tabs/{tab_id}/click", {"selector": selector})
            return True
        except requests.RequestException:
            return False

    def screenshot(self, tab_id: str) -> bytes | None:
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


def close_known_modals(client: CamofoxClient, tab_id: str) -> None:
    """Defensive dismissal - confirmed Uber Eats shows a non-blocking inline
    "Available at X" banner for a closed restaurant rather than a blocking
    modal, and a direct restaurant URL didn't trigger the "Allow your
    location" dialog seen on the bare ubereats.com homepage - but it's cheap
    to check for anyway in case a fresh profile behaves differently."""
    client.click(tab_id, 'role=button[name="Close" i]')


def scroll_until_stable(client: CamofoxClient, tab_id: str, max_passes: int = 15) -> int:
    """Scroll to the bottom repeatedly until the mounted item count stops
    growing across two consecutive passes (or max_passes is hit). Not
    strictly needed on the sampled restaurant - all 115 items were already
    mounted with no scrolling - but a bigger menu elsewhere may lazy-mount
    sections, so this polls for stability rather than trusting a fixed wait
    or a single read.

    Deliberately scrolls the document (`window.scrollBy`) rather than
    dispatching a mouse-wheel event at a fixed point: a wheel event scrolls
    whatever's under the cursor, and on this page that turned out to be the
    featured carousel, which clones its own slides for a seamless
    infinite-loop effect (duplicate "store-item-<uuid>" cards, one missing
    its rank badge)."""
    last_count = -1
    for _ in range(max_passes):
        count = client.evaluate(tab_id, ITEM_COUNT_JS) or 0
        if count == last_count:
            return count
        last_count = count
        client.evaluate(tab_id, "window.scrollBy(0, 2400); null")
        time.sleep(1.0)
    return last_count


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        time.sleep(2)  # let the SPA finish its initial render pass
        close_known_modals(client, tab_id)

        jsonld_scripts = client.evaluate(tab_id, JSONLD_JS) or []

        item_count = scroll_until_stable(client, tab_id)
        ratings = client.evaluate(tab_id, EXTRACT_RATINGS_JS) or []
    finally:
        client.close_tab(tab_id)
        client.close_session()

    args.jsonld_output.write_text(
        json.dumps({"result": jsonld_scripts}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    args.ratings_output.write_text(
        json.dumps({"result": ratings}, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    featured_count = sum(1 for r in ratings if r["in_featured_carousel"])
    rated_count = sum(1 for r in ratings if r["like_percent"] is not None)
    popular_count = sum(1 for r in ratings if r["is_popular"])
    print(
        f"Wrote {args.jsonld_output} ({len(jsonld_scripts)} scripts) and "
        f"{args.ratings_output} ({item_count} items, {featured_count} featured, "
        f"{rated_count} rated, {popular_count} popular)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Uber Eats restaurant page, e.g. https://www.ubereats.com/store/<slug>/<uuid>")
    parser.add_argument("jsonld_output", type=Path, help="Where to write the raw JSON-LD scripts dump")
    parser.add_argument("ratings_output", type=Path, help="Where to write the raw DOM ratings dump")
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="ubereats-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
