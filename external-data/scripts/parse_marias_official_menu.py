#!/usr/bin/env python3
"""Parse Maria's Mexican Grill official Squarespace menu pages."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup


DEFAULT_INPUT_DIR = Path("external-data/menu-scraping/official_site")
DEFAULT_OUTPUT = Path("external-data/menu-scraping/official_site/marias-official-menu-parsed.json")
MENU_PAGES = [
    "dailyspecials",
    "lunch",
    "dinner",
    "signatureitems",
    "minimaria",
    "familypack",
]


def clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def looks_like_price(text: str) -> bool:
    stripped = clean(text)
    return bool(stripped and "$" in stripped and len(stripped) <= 80)


def normalize_price(text: str) -> str:
    return clean(text).replace("$ ", "$")


def item_text(item: Any) -> str:
    price_top = item.select_one(".menu-item-price-top")
    if price_top:
        return clean(price_top.get_text(" ", strip=True))
    price_bottom = item.select_one(".menu-item-price-bottom")
    if price_bottom:
        return clean(price_bottom.get_text(" ", strip=True))
    return ""


def item_description(item: Any) -> str:
    desc = item.select_one(".menu-item-description")
    return clean(desc.get_text(" ", strip=True)) if desc else ""


def parse_page(path: Path) -> dict[str, Any]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    title = soup.title.get_text(" ", strip=True) if soup.title else path.stem
    parsed_sections: list[dict[str, Any]] = []

    for section in soup.select(".menu-section"):
        section_title_el = section.select_one(".menu-section-title")
        section_desc_el = section.select_one(".menu-section-description")
        section_title = clean(section_title_el.get_text(" ", strip=True)) if section_title_el else ""
        section_desc = clean(section_desc_el.get_text(" ", strip=True)) if section_desc_el else ""
        parsed_items: list[dict[str, Any]] = []

        for row in section.select(".menu-item"):
            title_el = row.select_one(".menu-item-title")
            row_title = clean(title_el.get_text(" ", strip=True)) if title_el else ""
            row_text = item_text(row)
            if not row_title:
                if parsed_items and looks_like_price(row_text) and not parsed_items[-1].get("price"):
                    parsed_items[-1]["price"] = normalize_price(row_text)
                continue

            price = normalize_price(row_text) if looks_like_price(row_text) else ""
            description_parts = [item_description(row)]
            if row_text and not price:
                description_parts.append(row_text)
            description = clean(" ".join(part for part in description_parts if part))
            parsed_items.append(
                {
                    "title": row_title,
                    "description": description,
                    "price": price,
                }
            )

        parsed_sections.append(
            {
                "section": section_title,
                "section_description": section_desc,
                "items": [item for item in parsed_items if item["title"] or item["description"] or item["price"]],
            }
        )

    return {"page": path.stem, "title": title, "sections": parsed_sections}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()

    pages = []
    for page in MENU_PAGES:
        path = args.input_dir / f"{page}.html"
        if path.exists():
            pages.append(parse_page(path))

    output = {
        "source": {
            "site": "https://mariasmexicangrillmi.com/",
            "pages": [f"https://mariasmexicangrillmi.com/{page['page']}" for page in pages],
        },
        "restaurant": {
            "name": "Maria's Mexican Grill",
            "address": "2330 West Road, Trenton, MI 48183",
            "phone": "(734) 307-7248",
            "email": "mariasmexicangrill2330@gmail.com",
        },
        "pages": pages,
    }
    args.output.write_text(json.dumps(output, indent=2, ensure_ascii=False), encoding="utf-8")
    section_count = sum(len(page["sections"]) for page in pages)
    item_count = sum(len(section["items"]) for page in pages for section in page["sections"])
    print(f"Wrote {args.output} ({len(pages)} pages, {section_count} sections, {item_count} items)")


if __name__ == "__main__":
    main()
