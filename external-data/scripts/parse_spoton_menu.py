#!/usr/bin/env python3
"""Parse a scrape_spoton_menu.py capture and fold "Picked For You" in.

Like Uber Eats' carousel/DoorDash's "Most Ordered"/Grubhub's "Best
Sellers"/AppFront's "Best Sellers", SpotOn rolls its top items into their
own "Picked For You" category that duplicates items already listed under
their real category. Like AppFront, SpotOn items have no durable id
available in the card markup, so this matches "Picked For You" duplicates
to their real-category copy by exact name - see scrape_spoton_menu.py's
docstring for why, and the risk that entails (two differently-configured
items sharing a name would incorrectly merge).

Availability (sold-out) isn't folded into the output here either - it's
only relevant once ordering is added, not for a menu scrape - but see
external-data/menu-scraping/sold-out-detection-notes.md for the signal
scrape_spoton_menu.py already captures (`is_sold_out` in the raw input).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

PICKED_FOR_YOU = "Picked For You"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Output of scrape_spoton_menu.py")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    capture = json.loads(args.input.read_text())
    entries = capture.get("result") or []

    picked_names = {e["name"] for e in entries if e.get("section") == PICKED_FOR_YOU and e.get("name")}

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in entries:
        if entry.get("section") == PICKED_FOR_YOU:
            continue
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
        if name in picked_names:
            parsed_item["special"] = "picked for you"
        sections[section_name].append(parsed_item)

    output = {
        "source": {
            "response_path": str(args.input),
            "url": capture.get("final_url") or capture.get("source_url") or "",
        },
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    picked_count = sum(
        1 for section in output["menu_sections"] for item in section["items"] if item.get("special") == "picked for you"
    )
    print(f"Wrote {args.output} ({section_count} sections, {item_count} items, {picked_count} picked for you)")


if __name__ == "__main__":
    main()
