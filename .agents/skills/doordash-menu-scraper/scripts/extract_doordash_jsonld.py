#!/usr/bin/env python3
"""Extract and parse DoorDash JSON-LD menu data from rendered HTML."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


def flatten(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, dict):
        return [value]
    if isinstance(value, list):
        items: list[dict[str, Any]] = []
        for child in value:
            items.extend(flatten(child))
        return items
    return []


def parse_price(item: dict[str, Any]) -> str | None:
    offers = item.get("offers")
    if isinstance(offers, dict):
        price = offers.get("price")
        return str(price) if price is not None else None
    return None


def parse_menu(menu: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    for section in flatten(menu.get("hasMenuSection", [])):
        parsed_items = []
        for item in flatten(section.get("hasMenuItem", [])):
            title = item.get("name")
            if not title:
                continue
            parsed_items.append(
                {
                    "title": title,
                    "ingredients_or_description": item.get("description") or "",
                    "price": parse_price(item),
                }
            )
        sections.append({"section": section.get("name") or "", "items": parsed_items})
    return sections


def extract_jsonld(html: str) -> list[str]:
    soup = BeautifulSoup(html, "lxml")
    scripts: list[str] = []
    for script in soup.find_all("script"):
        raw = (script.string or script.get_text() or "").strip()
        if not raw or script.get("type") != "application/ld+json":
            continue
        try:
            json.loads(raw)
        except json.JSONDecodeError:
            continue
        scripts.append(raw)
    return scripts


def parse_response(response_path: Path) -> dict[str, Any]:
    response = json.loads(response_path.read_text(encoding="utf-8"))
    parsed_scripts = [json.loads(script) for script in response.get("result", [])]
    restaurant = next((s for s in parsed_scripts if s.get("@type") == "Restaurant"), {})
    menu = next((s for s in parsed_scripts if s.get("@type") == "Menu"), {})
    faq = next((s for s in parsed_scripts if s.get("@type") == "FAQPage"), {})
    return {
        "source": {
            "response_path": str(response_path),
            "source_html_path": response.get("source_html_path", ""),
            "url": restaurant.get("url") or "",
        },
        "restaurant": {
            "name": restaurant.get("name") or "",
            "address": restaurant.get("address") or {},
            "telephone": restaurant.get("telephone") or "",
            "serves_cuisine": restaurant.get("servesCuisine") or [],
            "aggregate_rating": restaurant.get("aggregateRating") or {},
            "description": restaurant.get("description") or "",
        },
        "menu_sections": parse_menu(menu),
        "faq": faq.get("mainEntity") or [],
    }


def write_text_menu(parsed: dict[str, Any], parsed_path: Path, text_path: Path) -> None:
    lines = [
        f"# {parsed.get('restaurant', {}).get('name') or 'DoorDash'} Structured Menu",
        "",
        f"Source JSON: {parsed_path}",
        f"Response path: {parsed.get('source', {}).get('response_path', '')}",
        "",
    ]
    for section in parsed.get("menu_sections", []):
        items = section.get("items") or []
        if not items:
            continue
        lines.append(f"## {section.get('section') or 'Unnamed Section'}")
        lines.append("")
        for item in items:
            title = item.get("title") or ""
            price = item.get("price") or ""
            desc = item.get("ingredients_or_description") or ""
            line = f"- {title}"
            if price:
                line += f" — {price}"
            lines.append(line)
            if desc:
                lines.append(f"  {desc}")
        lines.append("")
    text_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--html", type=Path, required=True)
    parser.add_argument("--response", type=Path, required=True)
    parser.add_argument("--parsed", type=Path, required=True)
    parser.add_argument("--text", type=Path, required=True)
    args = parser.parse_args()

    html = args.html.read_text(encoding="utf-8", errors="replace")
    scripts = extract_jsonld(html)
    response = {
        "ok": True,
        "result": scripts,
        "resultType": "array",
        "truncated": False,
        "source_html_path": str(args.html),
    }
    args.response.write_text(json.dumps(response, ensure_ascii=False), encoding="utf-8")
    parsed = parse_response(args.response)
    args.parsed.write_text(json.dumps(parsed, indent=2, ensure_ascii=False), encoding="utf-8")
    write_text_menu(parsed, args.parsed, args.text)

    section_count = len(parsed["menu_sections"])
    item_count = sum(len(section["items"]) for section in parsed["menu_sections"])
    if section_count == 0 or item_count == 0:
        raise SystemExit(
            f"No menu items parsed from {args.html}; recapture rendered store HTML with Camofox."
        )
    print(f"Wrote {args.parsed} ({section_count} sections, {item_count} items)")


if __name__ == "__main__":
    main()
