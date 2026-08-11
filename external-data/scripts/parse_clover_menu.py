#!/usr/bin/env python3
"""Resolve Clover's $0.00-placeholder prices using a scrape_clover_menu.py capture.

Some items are listed at $0.00 because the real price is only set once a
required modifier is chosen (e.g. a soup's Cup/Bowl/Quart size). For each
such item, using its captured modifier groups:

  - A required group (its rule badge says "N required", not "optional") is
    the only kind that can establish a price - a customer isn't forced to
    pick from an optional add-on group, so those are read but never used to
    set the default price.
  - If every option in a required group costs the same (e.g. picking a
    flavor with no price difference), that shared price becomes the item's
    price and every option name is listed in the description.
  - Otherwise the *cheapest* option is folded into the item's price, and
    the pricier options in that same group are listed in the description
    with their price, so the data doesn't silently hide that an upgrade
    exists.
  - An item can have more than one required group (e.g. a combo with both a
    side slot and a soup slot); each group's contribution is computed the
    same way and summed.
  - A required group naming more than one pick (e.g. "2 required") is
    handled by summing that many of the cheapest options - this is a
    reasonable extrapolation of the single-required-pick case above, but
    it's never been exercised against a real "N>1 required" priced group on
    this restaurant, so treat it as best-effort.

A group's `<input>` elements are `type="radio"` when only one option can be
selected and `type="checkbox"` when more than one can. The rule badge text
should agree with that (e.g. "1 required" implies radio, "2 required"
implies checkbox) - when it doesn't, this script can't safely tell what
actually gets selected by default, so it records a review flag on the item
instead of guessing.

If an item is still $0.00 after checking every required group - either it
had no required group at all, or every required group turned out to be
free - it's left at $0.00 and flagged for manual review; that's the
restaurant's own catalog data, not something inferable from the page.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PRICE_RE = re.compile(r"\$([\d,]+\.\d{2})")


def extract_price_value(text: str | None) -> float | None:
    if not text:
        return None
    match = PRICE_RE.search(text)
    return float(match.group(1).replace(",", "")) if match else None


def parse_required_count(rule_text: str | None) -> int | None:
    """None means the group is optional (or has no rule at all) and can't establish a price."""
    if not rule_text:
        return None
    text = rule_text.lower()
    if "optional" in text:
        return None
    match = re.search(r"(\d+)", text)
    if match:
        return int(match.group(1))
    if "required" in text:
        return 1
    return None


def resolve_item_price(
    base_price: float, groups: list[dict[str, Any]]
) -> tuple[float, list[str], list[str]]:
    """Return (final_price, description_notes, review_flags)."""
    total_addon = 0.0
    notes: list[str] = []
    flags: list[str] = []

    for group in groups:
        required_count = parse_required_count(group.get("rule_text"))
        if required_count is None:
            continue

        options = [
            (opt.get("name") or "", extract_price_value(opt.get("price_text")))
            for opt in group.get("options", [])
        ]
        options = [(name, price) for name, price in options if price is not None]
        if not options:
            continue

        input_types = {opt.get("input_type") for opt in group.get("options", [])}
        expected_type = "radio" if required_count == 1 else "checkbox"
        if input_types != {expected_type}:
            flags.append(
                f"group {group.get('group_name')!r} rule says {group.get('rule_text')!r} "
                f"(implies {expected_type}) but option inputs are {sorted(t for t in input_types if t)}"
            )

        prices = [price for _, price in options]
        group_name = group.get("group_name") or "options"

        if all(price == prices[0] for price in prices):
            total_addon += prices[0]
            names = ", ".join(name for name, _ in options)
            pick_phrase = "choose one" if required_count == 1 else f"choose {required_count}"
            notes.append(f"{group_name}: {pick_phrase} - {names}")
        else:
            cheapest_n = sorted(prices)[:required_count]
            total_addon += sum(cheapest_n)
            floor_price = min(prices)
            pricier = [(name, price) for name, price in options if price > floor_price]
            pricier_text = ", ".join(f"{name} (${price:.2f})" for name, price in pricier)
            notes.append(f"{group_name}: {pricier_text} available for an extra charge")

    return base_price + total_addon, notes, flags


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input", type=Path, help="Output of scrape_clover_menu.py")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    capture = json.loads(args.input.read_text())
    items = capture.get("items") or []
    modifiers = capture.get("modifiers") or {}

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    fixed_count = 0
    still_zero_count = 0
    mismatch_count = 0

    for entry in items:
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

        is_zero = entry.get("price") is None or entry.get("price") == "$0.00"
        href = entry.get("href")
        if is_zero and href is not None and href in modifiers:
            groups = modifiers[href]
            final_price, notes, flags = resolve_item_price(0.0, groups)
            parsed_item["price"] = f"${final_price:.2f}"
            if notes:
                parsed_item["ingredients_or_description"] = "; ".join(notes)
            if flags:
                parsed_item["review_flags"] = flags
                mismatch_count += 1
            if final_price == 0.0:
                parsed_item.setdefault("review_flags", []).append(
                    "price still $0.00 after checking modifiers - no required priced option found"
                )
                still_zero_count += 1
            else:
                fixed_count += 1

        sections[section_name].append(parsed_item)

    output = {
        "source": {
            "response_path": str(args.input),
            "url": capture.get("final_url") or capture.get("source_url") or "",
            "json_ld_used": capture.get("json_ld_used", False),
        },
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    print(
        f"Wrote {args.output} ({section_count} sections, {item_count} items, "
        f"{fixed_count} $0.00 prices fixed, {still_zero_count} still $0.00 for review, "
        f"{mismatch_count} rule/input-type mismatches flagged)"
    )


if __name__ == "__main__":
    main()
