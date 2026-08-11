#!/usr/bin/env python3
"""Turn a scrape_rezku_menu.py capture into project-standard menu JSON.

Handles three things specific to Rezku:

  - "Popular Products" rollup: some restaurants (confirmed on Maria's
    Mexican Grill) show a "Popular Products" category up top that
    duplicates items already listed in their real category, by exact name -
    same pattern as SpotOn's "Picked For You". Dropped here rather than in
    the scraper so the raw capture stays a faithful record of the page.
  - Price ranges: a card price of "$X.XX - $Y.YY" means a size/variant
    choice sets the real price. Per this project's spec for Rezku, the
    lower bound becomes the item's price and a "Options up to $Y.YY" note
    is appended to its description.
  - $0.00 placeholder prices: resolved the same way as Clover's - a
    *required* modifier group (rule text "must pick N" / "must pick A - B")
    is the only kind that can pin down a price; if every option in it costs
    the same, that's the price, otherwise the cheapest N are folded in and
    the pricier options are called out in the description. Items scraped in
    "preview" mode (restaurant fully closed, "Start order" never reachable)
    have no modal data at all - these are left at their card price (often
    $0.00) and flagged for manual review instead of guessed at, per this
    project's "insert $0 items while making note of the missing options"
    spec for the closed-restaurant case.

Every item's full modifier/variant breakdown (when available) is preserved
verbatim in an `options` field keyed by section name - the synthesized
"Size" group for the unlabeled variant row, plus every real modifier
group's own name - each holding its option names, per-option price, and any
detail text (e.g. "6 slices, feeds 1").

For items with a size/variant row, topping/add-on prices are size-dependent
(confirmed live: a pizza topping reads $0.00 before any size is picked,
then a real per-size price once one is) - scrape_rezku_menu.py clicks
through every size and re-reads the modifier groups after each one,
capturing that as `groups_by_size`. When present, each option here carries
a `price_by_size` mapping (size name -> price) instead of a single flat
`price`, since there isn't one true price to report. Items with no size row
keep the simpler flat `price` field, since there's nothing for the price to
vary against.
"""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

PRICE_RE = re.compile(r"\$([\d,]+\.\d{2})")
POPULAR_SECTION = "Popular Products"


def extract_price_value(text: str | None) -> float | None:
    if not text:
        return None
    match = PRICE_RE.search(text)
    return float(match.group(1).replace(",", "")) if match else None


def parse_price_range(price_text: str | None) -> tuple[float | None, float | None]:
    """Returns (low, high); high is None when there's no range."""
    if not price_text:
        return None, None
    values = [float(m.replace(",", "")) for m in PRICE_RE.findall(price_text)]
    if not values:
        return None, None
    if len(values) == 1:
        return values[0], None
    return min(values), max(values)


def parse_rule(rule_text: str | None) -> tuple[bool, int | None, int | None]:
    """Returns (required, min_pick, max_pick). Seen forms: "pick any"
    (optional, unbounded), "pick up to N" (optional, capped), "must pick N"
    (required, exactly N), "must pick A - B" (required, ranged)."""
    if not rule_text:
        return False, None, None
    text = rule_text.strip().lower()
    if text.startswith("must pick"):
        nums = [int(n) for n in re.findall(r"\d+", text)]
        if len(nums) >= 2:
            return True, nums[0], nums[1]
        if nums:
            return True, nums[0], nums[0]
        return True, 1, 1
    if "up to" in text:
        nums = re.findall(r"\d+", text)
        return False, None, int(nums[0]) if nums else None
    return False, None, None


def build_options(modal: dict[str, Any] | None) -> dict[str, list[dict[str, Any]]]:
    options: dict[str, list[dict[str, Any]]] = {}
    if not modal:
        return options

    size_options = modal.get("size_options") or []
    if size_options:
        options["Size"] = [
            {
                "name": opt.get("name") or "",
                "price": extract_price_value(opt.get("price_text")),
                "detail": opt.get("detail") or "",
                "default_selected": bool(opt.get("default_selected")),
            }
            for opt in size_options
        ]

    groups_by_size = modal.get("groups_by_size") or {}
    if groups_by_size:
        # Topping prices vary by size (see module docstring) - merge each
        # size's group snapshot into one option list per group, keyed by
        # option name, with a price_by_size map instead of a flat price.
        for size_name, groups in groups_by_size.items():
            for group in groups or []:
                group_name = group.get("group_name") or "Options"
                bucket = options.setdefault(group_name, [])
                by_name = {opt["name"]: opt for opt in bucket}
                for opt in group.get("options") or []:
                    name = opt.get("name") or ""
                    price = extract_price_value(opt.get("price_text"))
                    if name in by_name:
                        by_name[name]["price_by_size"][size_name] = price
                    else:
                        entry = {
                            "name": name,
                            "price_by_size": {size_name: price},
                            "detail": opt.get("detail") or "",
                            "default_selected": bool(opt.get("default_selected")),
                        }
                        by_name[name] = entry
                        bucket.append(entry)
    else:
        for group in modal.get("groups") or []:
            group_name = group.get("group_name") or "Options"
            options[group_name] = [
                {
                    "name": opt.get("name") or "",
                    "price": extract_price_value(opt.get("price_text")),
                    "detail": opt.get("detail") or "",
                    "default_selected": bool(opt.get("default_selected")),
                }
                for opt in group.get("options") or []
            ]

    return options


def resolve_required_group_price(modal: dict[str, Any]) -> tuple[float | None, list[str], list[str]]:
    """Same folding strategy as parse_clover_menu.py's resolve_item_price,
    adapted for Rezku's rule-text shapes. Returns (price, description_notes,
    review_flags); price is None if no required group could establish one."""
    total = 0.0
    found_required = False
    notes: list[str] = []
    flags: list[str] = []

    for group in modal.get("groups") or []:
        required, min_pick, _max_pick = parse_rule(group.get("rule_text"))
        if not required:
            continue
        options = [
            (opt.get("name") or "", extract_price_value(opt.get("price_text")))
            for opt in group.get("options") or []
        ]
        options = [(name, price) for name, price in options if price is not None]
        if not options:
            continue

        found_required = True
        pick = min_pick or 1
        prices = [price for _, price in options]
        group_name = group.get("group_name") or "options"

        if all(price == prices[0] for price in prices):
            total += prices[0] * pick
            names = ", ".join(name for name, _ in options)
            notes.append(f"{group_name}: choose {pick} - {names}")
        else:
            cheapest_n = sorted(prices)[:pick]
            total += sum(cheapest_n)
            floor_price = min(prices)
            pricier = [(name, price) for name, price in options if price > floor_price]
            pricier_text = ", ".join(f"{name} (${price:.2f})" for name, price in pricier)
            notes.append(f"{group_name}: {pricier_text} available for an extra charge")

    if not found_required:
        return None, [], []
    return total, notes, flags


def fold_popular_products(sections: dict[str, list[dict[str, Any]]], order: list[str]) -> tuple[dict[str, list[dict[str, Any]]], list[str], int]:
    if POPULAR_SECTION not in sections:
        return sections, order, 0
    popular_names = {item["title"] for item in sections[POPULAR_SECTION]}
    folded = 0
    for name in list(popular_names):
        for section_name, items in sections.items():
            if section_name == POPULAR_SECTION:
                continue
            if any(it["title"] == name for it in items):
                folded += 1
                break
    del sections[POPULAR_SECTION]
    order = [s for s in order if s != POPULAR_SECTION]
    return sections, order, folded


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="Output of scrape_rezku_menu.py")
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    capture = json.loads(args.input.read_text())
    items = capture.get("items") or []
    modals = capture.get("modals") or {}
    order_mode = capture.get("order_mode") or "preview"

    sections: dict[str, list[dict[str, Any]]] = {}
    order: list[str] = []
    fixed_count = 0
    still_zero_count = 0
    missing_options_count = 0

    for index, entry in enumerate(items):
        name = entry.get("name")
        if not name:
            continue
        section_name = entry.get("section") or "Uncategorized"
        if section_name not in sections:
            sections[section_name] = []
            order.append(section_name)

        card_price_text = entry.get("price")
        low, high = parse_price_range(card_price_text)
        description = entry.get("description") or ""

        parsed_item: dict[str, Any] = {
            "title": name,
            "ingredients_or_description": description,
            "price": f"${low:.2f}" if low is not None else card_price_text,
        }
        if entry.get("is_sold_out"):
            parsed_item["is_sold_out"] = True

        modal = modals.get(str(index))

        if high is not None:
            note = f"Options up to ${high:.2f}"
            parsed_item["ingredients_or_description"] = (
                f"{description}; {note}" if description else note
            )

        if modal is not None:
            parsed_item["options"] = build_options(modal)
            is_zero = low is None or low == 0.0
            if is_zero:
                resolved_price, notes, flags = resolve_required_group_price(modal)
                if resolved_price is not None:
                    parsed_item["price"] = f"${resolved_price:.2f}"
                    if notes:
                        parsed_item["ingredients_or_description"] = (
                            "; ".join([description, *notes]) if description else "; ".join(notes)
                        )
                    if flags:
                        parsed_item["review_flags"] = flags
                    if resolved_price == 0.0:
                        parsed_item.setdefault("review_flags", []).append(
                            "price still $0.00 after checking required groups"
                        )
                        still_zero_count += 1
                    else:
                        fixed_count += 1
                else:
                    parsed_item.setdefault("review_flags", []).append(
                        "price still $0.00 - no required modifier group found to establish a price"
                    )
                    still_zero_count += 1
        else:
            parsed_item["options"] = {}
            parsed_item["missing_options"] = True
            reason = (
                "restaurant closed with no preorder slots available - could not enter "
                "Start order flow to reach item modals"
                if order_mode == "preview"
                else "item modal could not be reached"
            )
            parsed_item.setdefault("review_flags", []).append(f"options not scraped: {reason}")
            missing_options_count += 1

        sections[section_name].append(parsed_item)

    sections, order, folded_count = fold_popular_products(sections, order)

    output = {
        "source": {
            "response_path": str(args.input),
            "url": capture.get("final_url") or capture.get("source_url") or "",
            "order_mode": order_mode,
        },
        "menu_sections": [{"section": name, "items": sections[name]} for name in order],
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")

    section_count = len(output["menu_sections"])
    item_count = sum(len(section["items"]) for section in output["menu_sections"])
    print(
        f"Wrote {args.output} ({section_count} sections, {item_count} items, "
        f"{fixed_count} $0.00 prices fixed, {still_zero_count} still $0.00 for review, "
        f"{missing_options_count} items missing options, {folded_count} Popular Products duplicates folded)"
    )


if __name__ == "__main__":
    main()
