#!/usr/bin/env python3
"""Scrape a Rezku Online Ordering menu (order.rezku.com) via a running camofox-browser server.

Rezku's cover page (`/<id>/cover`) offers two entry points:

  - "Start order" - only clickable (not `disabled`) when the restaurant has
    an actual pickup/delivery slot available right now or the user has
    picked a valid future date+time from the Date/Time `<select>`s on that
    same cover page. Once inside, every item is a real Angular route
    (`/product/add/<id>`) with its full modifier/variant data - required
    size choices, add-on groups, etc.
  - "View menu" - always clickable, but items in this preview mode are
    inert: clicking an `app-menu-item` button does nothing (confirmed live -
    no modal, no navigation). This is the only path available when the
    restaurant is closed with no preorder slots either, and it only exposes
    the same summary data already visible on each item's card (name,
    price/price-range, description) - no modifier/variant detail.

This script always tries "Start order" first (after selecting the first
available preorder date+time if the restaurant is closed for same-day
orders but still "open for preorders" - confirmed live: picking a future
date on the cover page's Date `<select>` populates the Time `<select>` and
un-disables "Start order"). If "Start order" is unavailable, it falls back
to "View menu" and marks every item's `options` as unresolved - matches this
project's fallback pattern for platforms with a modal-gated detail view
(see also scrape_clover_menu.py for the $0.00-placeholder-price version of
this same problem).

Menu structure once inside (either mode), confirmed against Stefano's Pizza
and Subs (https://order.rezku.com/8a9f1d4d-dae4-4a70-a62b-71e6ed789435,
10 categories/91 items, all mounted on one page, no virtualization) and
Maria's Mexican Grill (https://order.rezku.com/c355d3a8-0c6e-48f0-87fb-a19aae29ab6b,
has a "Popular Products" rollup category at the top):

  - Category headers are `span.h-menu` elements; items are `app-menu-item`.
    Matched by nearest-preceding DOM position, same interleaving pattern
    used for Clover/Square/Toast/AppFront/SpotOn.
  - A "Popular Products" category (when present) duplicates items from
    other real categories by exact name - confirmed on Maria's ("Rice
    Bowl", "Chimichanga Dinner", etc. appear both there and in their real
    section). Folded away in parse_rezku_menu.py the same way SpotOn's
    "Picked For You" rollup is, rather than here, so the raw capture stays
    a faithful record of what the page actually rendered.
  - Card price text is either a single "$X.XX" or a range "$X.XX - $Y.YY"
    (a size/variant choice is required to pin down the exact price) -
    parse_rezku_menu.py resolves this to a base price + "Options up to $Y"
    note, per this project's spec for price-range items.

Item modal (`/product/add/<id>`, only reachable via "Start order"):

  - Title: first `p.h5.mb-0` inside `app-product-builder`.
  - Description: `p.small.text-body-secondary.mb-3` right after the title
    (present but empty for items with no description).
  - Size/variant choice (e.g. Small/Large/Thick Pan/Gluten Free): a plain
    row of `button.btn-modifier-radio` NOT wrapped in an `app-modifier-group`
    - confirmed this is genuinely unlabeled in the DOM (no header element at
    all), unlike every other modifier group, so this script synthesizes the
    label "Size" for it. Not every item has one (confirmed on "Cheese
    Slice", a single-price item: zero such buttons, zero modifier groups).
  - Real modifier groups: `app-modifier-group` elements, each with a
    `.h-modifier` header (e.g. "Sandwich Cheese") and a rule line
    (`p.small.text-body-secondary.ms-auto.mb-0`) whose text has been seen
    in three shapes - "pick any" (optional/unlimited), "pick up to N"
    (optional, capped), "must pick N" / "must pick A - B" (required,
    min/max) - parse_rezku_menu.py is the one that interprets these.
  - Every option, in both the variant row and modifier groups, is a
    `button.btn-modifier-radio` or `button.btn-modifier-check` whose name/
    price/detail text is read by stripping the price/detail spans
    (`.btn-modifier-small.text-body-secondary`, the `.fw-normal` one being
    the detail e.g. "6 slices, feeds 1") out of a clone and reading what's
    left, rather than relying on nesting (the variant row's buttons and the
    modifier-group buttons nest their image/name differently, but both use
    this same span convention). A pre-selected default (confirmed on
    Italian Sub's "Provolone") carries an `active` class on the button.
  - Modifier-group option *prices are size-dependent* when an item has a
    size/variant row - confirmed live on Cheese Pizza: every Pizza Meats
    topping reads $0.00 before any size is picked, then $1.25 once "Small"
    is selected, $1.90 for "Large" or "Thick Pan" (group names, rule text,
    and option identities stay the same across sizes - only the price
    changes). So for any item with a size row, this script clicks through
    every size option and re-reads the modifier groups after each click,
    rather than reading them once in whatever the modal's initial/no-size-
    picked state happens to be - that initial-state price is not a real
    price for a topping, it is Rezku's un-costed placeholder before a size
    is chosen. Sizes are clicked via a JS-side `.click()` on the exact
    button element (matched by its position in the same "not inside
    app-modifier-group" list used to read them) rather than a `has-text`
    selector, since a topping option can share a size's name by coincidence
    and `has-text` would then match the wrong element.

Every click/navigation is preceded by a randomized human-paced delay, same
convention as the other scrapers in this project.

Requires the camofox-browser server already running (see the camofox-startup
skill / `camofox server start`).
"""

from __future__ import annotations

import argparse
import json
import random
import sys
import time
from pathlib import Path
from typing import Any

import requests

EXTRACT_BASE_MENU_JS = r"""
(function() {
  const headers = Array.from(document.querySelectorAll('.h-menu'));
  const cards = Array.from(document.querySelectorAll('app-menu-item'));
  const all = [
    ...headers.map(function(h) { return { type: 'header', el: h, text: h.textContent.trim() }; }),
    ...cards.map(function(c) { return { type: 'item', el: c }; }),
  ];
  all.sort(function(a, b) { return (a.el.compareDocumentPosition(b.el) & Node.DOCUMENT_POSITION_FOLLOWING) ? -1 : 1; });
  let current = null;
  const results = [];
  for (const entry of all) {
    if (entry.type === 'header') {
      current = entry.text;
      continue;
    }
    const card = entry.el;
    const nameEl = card.querySelector('p.h6');
    const descEl = card.querySelector('.card-body p.small.text-body-secondary');
    const priceEl = card.querySelector('.card-footer p.small.fw-bold');
    const isSoldOut = /sold out|unavailable|86'd|out of stock/i.test(card.textContent);
    results.push({
      section: current,
      name: nameEl ? nameEl.textContent.trim() : null,
      description: descEl ? descEl.textContent.trim() : '',
      price: priceEl ? priceEl.textContent.trim() : null,
      is_sold_out: isSoldOut,
    });
  }
  return JSON.stringify(results);
})()
""".strip()

# Shared by every modal-scraping JS snippet below - duplicated per snippet
# (rather than defined once) because each is its own standalone evaluate()
# call with no shared JS state between them.
EXTRACT_OPTION_JS_HELPER = r"""
  function extractOption(btn) {
    const smalls = Array.from(btn.querySelectorAll('.btn-modifier-small'));
    const priceEl = smalls.find(function(e) { return !e.classList.contains('fw-normal'); });
    const detailEl = smalls.find(function(e) { return e.classList.contains('fw-normal'); });
    const clone = btn.cloneNode(true);
    Array.from(clone.querySelectorAll('.btn-modifier-small, app-product-image, .ratio')).forEach(function(e) { e.remove(); });
    return {
      name: clone.textContent.trim(),
      price_text: priceEl ? priceEl.textContent.trim() : '',
      detail: detailEl ? detailEl.textContent.trim() : '',
      default_selected: btn.classList.contains('active'),
    };
  }
  function variantButtons() {
    return Array.from(document.querySelectorAll('button.btn-modifier-radio'))
      .filter(function(b) { return !b.closest('app-modifier-group'); });
  }
""".strip()

# Title/description/size_options only - read once per item. Size option
# prices are the size choices themselves, not affected by which size is
# picked, so unlike the modifier groups they don't need re-reading.
EXTRACT_HEADER_JS = f"""
(function() {{
  {EXTRACT_OPTION_JS_HELPER}
  const builder = document.querySelector('app-product-builder');
  if (!builder) return JSON.stringify(null);
  const titleEl = builder.querySelector('p.h5.mb-0');
  const descEl = builder.querySelector('p.small.text-body-secondary.mb-3');
  return JSON.stringify({{
    title: titleEl ? titleEl.textContent.trim() : null,
    description: descEl ? descEl.textContent.trim() : '',
    size_options: variantButtons().map(extractOption),
  }});
}})()
""".strip()

# Modifier groups only - re-run after each size click, since a topping's
# price depends on which size is currently selected (see module docstring).
EXTRACT_GROUPS_JS = f"""
(function() {{
  {EXTRACT_OPTION_JS_HELPER}
  const groups = Array.from(document.querySelectorAll('app-modifier-group')).map(function(g) {{
    const headerEl = g.querySelector('.h-modifier');
    const ruleEl = g.querySelector('p.small.text-body-secondary.ms-auto.mb-0');
    const options = Array.from(g.querySelectorAll('button.btn-modifier-check, button.btn-modifier-radio')).map(extractOption);
    return {{
      group_name: headerEl ? headerEl.textContent.trim() : '',
      rule_text: ruleEl ? ruleEl.textContent.trim() : '',
      options: options,
    }};
  }});
  return JSON.stringify(groups);
}})()
""".strip()


def click_variant_js(index: int) -> str:
    """Click the item's Nth size/variant button (top-level, not inside an
    app-modifier-group) directly via JS rather than a `has-text` selector -
    a topping option can coincidentally share a size's name."""
    return f"""
    (function() {{
      {EXTRACT_OPTION_JS_HELPER}
      const btns = variantButtons();
      if (!btns[{index}]) return false;
      btns[{index}].click();
      return true;
    }})()
    """.strip()

ITEM_COUNT_JS = "document.querySelectorAll('app-menu-item').length"


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

    def navigate(self, tab_id: str, url: str) -> bool:
        try:
            self._post(f"/tabs/{tab_id}/navigate", {"url": url})
            return True
        except requests.RequestException:
            return False

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
        try:
            self._post(f"/tabs/{tab_id}/click", {"selector": selector})
            return True
        except requests.RequestException:
            return False

    def wait_for_selector(self, tab_id: str, selector: str, timeout_ms: int = 8000, poll_ms: int = 300) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        check_js = f"!!document.querySelector({json.dumps(selector)})"
        while time.monotonic() < deadline:
            if self.evaluate(tab_id, check_js):
                return True
            time.sleep(poll_ms / 1000)
        return False

    def wait_for_url_contains(self, tab_id: str, fragment: str, timeout_ms: int = 8000, poll_ms: int = 300) -> bool:
        deadline = time.monotonic() + timeout_ms / 1000
        while time.monotonic() < deadline:
            if fragment in (self.evaluate(tab_id, "location.href") or ""):
                return True
            time.sleep(poll_ms / 1000)
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


def human_delay(min_s: float = 0.9, max_s: float = 2.2) -> None:
    """Pause like someone reading the page before their next click/navigation."""
    time.sleep(random.uniform(min_s, max_s))


def try_enable_start_order(client: CamofoxClient, tab_id: str) -> bool:
    """Best-effort: if "Start order" is disabled for today, step the Date
    select forward to the next few days looking for one with pickup times,
    then pick its first time slot. Restaurants that are genuinely closed
    (no preorder slots at all in that window either) are left alone - the
    caller falls back to "View menu" in that case, which is the behavior
    this whole function exists to test/exercise per the closed-restaurant
    test case for this script."""
    is_enabled_js = """
    (function() {
      const btn = Array.from(document.querySelectorAll('button')).find(b => b.textContent.trim() === 'Start order');
      return btn ? !btn.disabled : false;
    })()
    """
    if client.evaluate(tab_id, is_enabled_js):
        return True

    # option.value is truthy even for the placeholder (Angular's select
    # value accessor renders unset/null-bound options as the literal string
    # "0: null", not an empty string) - so the placeholder can't be filtered
    # out by truthiness. It's always index 0 ("Choose an order date..." /
    # "Choose an order time...") on every restaurant sampled, so it's
    # skipped positionally instead.
    date_options_js = "JSON.stringify(Array.from(document.querySelectorAll('select'))[0] ? Array.from(document.querySelectorAll('select')[0].options).slice(1).map(o => o.value) : [])"
    candidate_values = client.evaluate(tab_id, date_options_js) or []

    for value in candidate_values[:6]:
        human_delay(0.6, 1.4)
        set_date_js = f"""
        (function() {{
          const s = document.querySelectorAll('select')[0];
          s.value = {json.dumps(value)};
          s.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return s.value;
        }})()
        """
        client.evaluate(tab_id, set_date_js)
        time.sleep(1.0)

        time_values_js = "JSON.stringify(Array.from(document.querySelectorAll('select'))[1] ? Array.from(document.querySelectorAll('select')[1].options).slice(1).map(o => o.value) : [])"
        time_values = client.evaluate(tab_id, time_values_js) or []
        if not time_values:
            continue

        human_delay(0.5, 1.2)
        set_time_js = f"""
        (function() {{
          const s = document.querySelectorAll('select')[1];
          s.value = {json.dumps(time_values[0])};
          s.dispatchEvent(new Event('change', {{ bubbles: true }}));
          return s.value;
        }})()
        """
        client.evaluate(tab_id, set_time_js)
        time.sleep(1.0)
        if client.evaluate(tab_id, is_enabled_js):
            return True

    return False


def enter_order_flow(client: CamofoxClient, tab_id: str) -> str:
    """Returns 'full' if "Start order" was used (modal access available),
    'preview' if this fell back to "View menu" (list-only, no modals)."""
    human_delay(1.2, 2.2)
    if try_enable_start_order(client, tab_id):
        human_delay(0.8, 1.6)
        if client.click(tab_id, 'button:has-text("Start order")'):
            client.wait_for_selector(tab_id, "app-menu-item", timeout_ms=10000)
            return "full"

    human_delay(0.6, 1.4)
    client.click(tab_id, "button.btn-outline-middlegray.flex-grow-1")
    client.wait_for_selector(tab_id, "app-menu-item", timeout_ms=10000)
    return "preview"


def scrape_item_modal(client: CamofoxClient, tab_id: str, index: int) -> dict[str, Any] | None:
    human_delay()
    if not client.click(tab_id, f"app-menu-item button.card >> nth={index}"):
        return None
    if not client.wait_for_url_contains(tab_id, "/product/add/", timeout_ms=8000):
        return None
    time.sleep(0.5)
    header = client.evaluate(tab_id, EXTRACT_HEADER_JS)
    if header is None:
        return None

    size_options = header.get("size_options") or []
    groups_by_size: dict[str, Any] = {}
    if size_options:
        # Topping/add-on prices depend on which size is selected (confirmed
        # live - see module docstring), so each size has to be clicked in
        # turn and the modifier groups re-read after each one.
        for size_index, size_opt in enumerate(size_options):
            size_name = size_opt.get("name") or f"size_{size_index}"
            human_delay(0.5, 1.1)
            if not client.evaluate(tab_id, click_variant_js(size_index)):
                continue
            time.sleep(0.6)
            groups_by_size[size_name] = client.evaluate(tab_id, EXTRACT_GROUPS_JS) or []
        # Representative single snapshot (whatever size was clicked last) -
        # kept for items with no size row at all, where groups_by_size is
        # empty and this is the only group data available.
        groups = next(iter(groups_by_size.values()), [])
    else:
        groups = client.evaluate(tab_id, EXTRACT_GROUPS_JS) or []

    modal = {
        "title": header.get("title"),
        "description": header.get("description") or "",
        "size_options": size_options,
        "groups": groups,
        "groups_by_size": groups_by_size,
    }

    human_delay(0.5, 1.2)
    client.click(tab_id, 'button:has-text("Back to Menu")')
    client.wait_for_selector(tab_id, "app-menu-item", timeout_ms=8000)
    return modal


def scrape(args: argparse.Namespace) -> None:
    client = CamofoxClient(args.server, args.user)
    if not client.health():
        print(f"camofox-browser server not reachable at {args.server}. Start it first (camofox-startup skill).", file=sys.stderr)
        sys.exit(2)

    tab_id = client.open_tab(args.url, args.latitude, args.longitude, args.timezone)
    try:
        client.wait(tab_id, timeout_ms=15000)
        human_delay(1.5, 2.5)

        order_mode = enter_order_flow(client, tab_id)
        items = client.evaluate(tab_id, EXTRACT_BASE_MENU_JS) or []

        modals: dict[str, Any] = {}
        if order_mode == "full":
            item_count = client.evaluate(tab_id, ITEM_COUNT_JS) or len(items)
            for i in range(item_count):
                modal = scrape_item_modal(client, tab_id, i)
                if modal is not None:
                    modals[str(i)] = modal

        final_url = client.evaluate(tab_id, "location.href")
    finally:
        client.close_tab(tab_id)
        client.close_session()

    output = {
        "source_url": args.url,
        "final_url": final_url,
        "order_mode": order_mode,
        "items": items,
        "modals": modals,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len({it["section"] for it in items if it.get("section")})
    print(
        f"Wrote {args.output} ({section_count} sections, {len(items)} items, "
        f"order_mode={order_mode}, {len(modals)} item modals captured)"
    )


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("url", help="Rezku cover page, e.g. https://order.rezku.com/<id>/cover")
    parser.add_argument("output", type=Path)
    parser.add_argument("--latitude", type=float, default=42.197513)
    parser.add_argument("--longitude", type=float, default=-83.269677)
    parser.add_argument("--timezone", default="America/Detroit")
    parser.add_argument("--server", default="http://localhost:9377")
    parser.add_argument("--user", default="rezku-scraper", help="camofox-browser profile id")
    args = parser.parse_args()
    scrape(args)


if __name__ == "__main__":
    main()
