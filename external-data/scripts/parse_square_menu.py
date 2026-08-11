#!/usr/bin/env python3
"""Parse a Square Online (square.site, Weebly/EditMySite-powered) menu DOM extraction.

Square has no JSON-LD or embedded state to read - everything comes from a
DOM pass over `.grid__item` cards, matched to their nearest preceding
`.category-title__container` heading (its text has stray leading whitespace
before the actual name, so strip before splitting on newlines).

The menu is lazy-loaded on scroll like DoorDash/Grubhub (13 of 16 items were
mounted before any scrolling on the sampled restaurant), so the DOM
extraction driving this needs to scroll through the page collecting items,
not just query once.

Unlike the other platforms, there's no separate "Featured"/"Popular" rollup
category to de-duplicate - items live only under their real category. Square
does support a generic badge template (`.badge-around`, with CSS custom
properties for label text set per item) that a restaurant *could* use for
something like "Popular" or "New", but the sampled restaurant (Motz's
Burgers) has it present in the markup yet unset on every item. So "special"
just passes through whatever badge text (if any) the DOM extraction found,
rather than a fixed literal like "featured item"/"best seller".
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="DOM extraction: {result: [{category, name, description, price, badge}, ...]}")
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
        section_name = entry.get("category") or "Uncategorized"
        if section_name not in sections:
            sections[section_name] = []
            order.append(section_name)
        parsed_item: dict[str, Any] = {
            "title": name,
            "ingredients_or_description": entry.get("description") or "",
            "price": entry.get("price"),
        }
        if entry.get("badge"):
            parsed_item["special"] = entry["badge"]
        sections[section_name].append(parsed_item)

    output = {
        "source": {"response_path": str(args.input)},
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    badged_count = sum(1 for section in output["menu_sections"] for item in section["items"] if item.get("special"))
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items, {badged_count} badged)")


if __name__ == "__main__":
    main()
