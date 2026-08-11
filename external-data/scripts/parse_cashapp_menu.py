#!/usr/bin/env python3
"""Parse a Cash App (cash.app) local-ordering menu DOM extraction.

Like Square, Cash App has no JSON-LD or embedded state - this reads a DOM
pass over `[data-testid^="item-tile-container-"]` cards grouped by their
enclosing `[data-testid^="menu-item-grid-"]` section. On the sampled
restaurant, all items were mounted at once (no scroll-driven lazy loading
observed), unlike Square/DoorDash/Grubhub.

There's no featured/best-seller rollup category here. Availability
(sold-out) isn't handled here either - it's only relevant once we add
ordering, not for a menu scrape - but see
external-data/menu-scraping/sold-out-detection-notes.md for how to detect
it when that's needed: an out-of-stock item shows "Sold out" text, its
add-to-cart button is disabled, and it has no price at all.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="DOM extraction: {result: [{item_id, section, name, description, price, is_sold_out}, ...]}")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    response = json.loads(args.input.read_text())
    entries = response.get("result") or []

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in entries:
        name = entry.get("name")
        if not name:
            continue
        section_name = entry.get("section") or "Uncategorized"
        if section_name not in sections:
            sections[section_name] = []
            order.append(section_name)
        parsed_item: dict[str, Any] = {
            "title": name,
            "ingredients_or_description": entry.get("description") or "",
            "price": entry.get("price"),
        }
        sections[section_name].append(parsed_item)

    output = {
        "source": {"response_path": str(args.input)},
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items)")


if __name__ == "__main__":
    main()
