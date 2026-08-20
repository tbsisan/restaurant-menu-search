#!/usr/bin/env python3
"""Parse a Toast Online Ordering menu DOM extraction and tag "Featured Items".

Toast (toasttab.com, and the same app embedded on a restaurant's own domain
under /order) has no ratings/reviews, only a "Featured Items" rollup section
at the top of the menu - the same duplicate-category pattern as Uber Eats'
carousel, DoorDash's "Most Ordered", and Grubhub's "Best Sellers".

Unlike Grubhub's badge, Toast doesn't mark the item card itself when it's
featured; the only signal is which items appear inside the
`div.menu.paddedContent.featuredItems` container. But each item carries a
durable UUID in its "add-to-cart-<uuid>" testid/href
(`/order/<restaurant-slug>/item-<name-slug>_<uuid>`), and that same UUID is
reused on the duplicate card in the item's real category - so matching is
still id-based, not name-based.

The whole menu is small enough that Toast mounts every item card at once
(no virtualized/lazy scrolling observed). The companion scraper then opens each
distinct item card and records `option_groups` from its configuration modal.

Availability (sold-out) isn't handled here - only relevant once we add
ordering, not for a menu scrape - but see
external-data/menu-scraping/sold-out-detection-notes.md for how to detect
it when that's needed: a `[data-testid="menu-item-tags"] .itemTag` reading
"OUT OF STOCK", and the price `<span>` gets an extra `outOfStock` class
(price is still shown, unlike Cash App which omits it entirely).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

FEATURED_ITEMS = "Featured Items"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="DOM extraction: {result: [{item_id, section, name, description, price}, ...]}")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    response = json.loads(args.input.read_text())
    entries = response.get("result") or []
    # Older artifacts predate the flag and always captured options, so absent
    # means True.  When False, `options` is omitted entirely rather than
    # emitted empty - an empty list would claim the item has no modifiers.
    options_captured = response.get("options_captured", True)

    featured_ids = {e["item_id"] for e in entries if e.get("section") == FEATURED_ITEMS and e.get("item_id")}

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in entries:
        if entry.get("section") == FEATURED_ITEMS:
            continue
        section_name = entry.get("section") or ""
        if section_name not in sections:
            sections[section_name] = []
            order.append(section_name)
        parsed_item: dict[str, Any] = {
            "title": entry.get("name") or "",
            "ingredients_or_description": entry.get("description") or "",
            "price": entry.get("price"),
        }
        if options_captured:
            parsed_item["options"] = entry.get("option_groups") or []
        if entry.get("item_id") in featured_ids:
            parsed_item["special"] = "featured item"
        if entry.get("modal_error"):
            parsed_item["configuration_error"] = entry["modal_error"]
        sections[section_name].append(parsed_item)

    output = {
        "source": {"response_path": str(args.input), "options_captured": options_captured},
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    featured_count = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("special") == "featured item"
    )
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items, {featured_count} featured)")


if __name__ == "__main__":
    main()
