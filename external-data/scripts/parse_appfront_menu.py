#!/usr/bin/env python3
"""Parse a scrape_appfront_menu.py capture and fold "Best Sellers" in.

Like Uber Eats' carousel/DoorDash's "Most Ordered"/Grubhub's "Best Sellers",
AppFront rolls its top items into their own "Best Sellers" category that
duplicates items already listed under their real category. Unlike those
platforms, AppFront items have no durable id available without clicking each
one open, so this matches "Best Sellers" duplicates to their real-category
copy by exact name - see scrape_appfront_menu.py's docstring for why, and the
risk that entails (two differently-configured items sharing a name would
incorrectly merge).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

BEST_SELLERS = "Best Sellers"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Output of scrape_appfront_menu.py")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    capture = json.loads(args.input.read_text())
    entries = capture.get("result") or []

    best_seller_names = {e["name"] for e in entries if e.get("section") == BEST_SELLERS and e.get("name")}

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    for entry in entries:
        if entry.get("section") == BEST_SELLERS:
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
        if name in best_seller_names:
            parsed_item["special"] = "best seller"
        sections[section_name].append(parsed_item)

    output = {
        "source": {
            "response_path": str(args.input),
            "url": capture.get("final_url") or capture.get("source_url") or "",
            "branch": capture.get("branch") or {},
        },
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
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
