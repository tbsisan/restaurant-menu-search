#!/usr/bin/env python3
"""Parse a Grubhub scroll-extracted menu dump and tag "Best Seller" items.

Grubhub has no JSON-LD menu, so the source here is the DOM scroll-extraction
described in .agents/skills/grubhub-menu-scraper-v2/references (one JSON file
with `sections[].items[]`, each item keyed by its durable Grubhub item id).

Like Uber Eats' "Featured items" carousel and DoorDash's "Most Ordered"
section, Grubhub rolls its best sellers up into their own pseudo-category
("Best Sellers") that duplicates items already listed under their real
category. That rollup is dropped from the output; instead, matching items in
their real category get "special": "best seller".

Matching is done by durable item id, not by name: Grubhub renders a
"Best Seller" badge (`[data-testid="flatten-item-popular-item"]`) directly on
an item's card in its *real* category section (not just in the rollup), so
--badges should point at a DOM extraction of {item_id, is_best_seller} pairs
read straight off that badge. This avoids matching dishes by name, which can
collide for same-named items with different configurations or typos.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BEST_SELLERS = "Best Sellers"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Raw scroll-extracted menu JSON")
    parser.add_argument("output", type=Path)
    parser.add_argument(
        "--badges",
        type=Path,
        default=None,
        help="DOM badge extraction: {result: [{item_id, is_best_seller}, ...]}",
    )
    args = parser.parse_args()

    raw = json.loads(args.input.read_text())

    best_seller_ids: set[str] = set()
    if args.badges is not None:
        badges_response = json.loads(args.badges.read_text())
        for entry in badges_response.get("result") or []:
            if entry.get("is_best_seller") and entry.get("item_id"):
                best_seller_ids.add(str(entry["item_id"]))
    else:
        # Fall back to the incidental "Best Seller" text Grubhub concatenates
        # into button_text when no separate badge extraction is available.
        for section in raw.get("sections", []):
            if section.get("title") == BEST_SELLERS:
                continue
            for item in section.get("items", []):
                if "Best Seller" in (item.get("button_text") or ""):
                    best_seller_ids.add(str(item.get("id")))

    parsed_sections: list[dict[str, Any]] = []
    for section in raw.get("sections", []):
        if section.get("title") == BEST_SELLERS:
            continue
        items = []
        for item in section.get("items", []):
            parsed_item: dict[str, Any] = {
                "title": item.get("name") or "",
                "ingredients_or_description": item.get("description") or "",
                "price": item.get("price"),
            }
            if str(item.get("id")) in best_seller_ids:
                parsed_item["special"] = "best seller"
            items.append(parsed_item)
        parsed_sections.append({"section": section.get("title") or "", "items": items})

    output = {
        "source": {
            "response_path": str(args.input),
            "badges_path": str(args.badges) if args.badges is not None else "",
        },
        "menu_sections": parsed_sections,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    best_seller_count = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("special") == "best seller"
    )
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items, {best_seller_count} best sellers)")


if __name__ == "__main__":
    main()
