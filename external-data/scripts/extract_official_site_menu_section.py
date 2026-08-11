#!/usr/bin/env python3
"""Extract one compact menu section from an official-site HTML page."""

from __future__ import annotations

import argparse
import re
from pathlib import Path

from bs4 import BeautifulSoup, Tag


DEFAULT_INPUT = Path("external-data/menu-scraping/official_site/lunch.html")
DEFAULT_OUTPUT = Path("external-data/menu-scraping/official_site/text/lunch-section-text.txt")
KEEP_CLASSES = {
    "menu-section",
    "menu-section-title",
    "menu-section-description",
    "menu-item",
    "menu-item-title",
    "menu-item-description",
    "menu-item-price-top",
    "menu-item-price-bottom",
}


def compact_tag(tag: Tag) -> None:
    for child in list(tag.children):
        if isinstance(child, Tag):
            compact_tag(child)
    classes = [name for name in tag.get("class", []) if name in KEEP_CLASSES]
    tag.attrs = {"class": classes} if classes else {}
    if tag.name not in {"div", "span", "p", "br"}:
        tag.unwrap()


def compact_html(tag: Tag) -> str:
    soup = BeautifulSoup(str(tag), "html.parser")
    root = soup.select_one(".menu-section")
    if root is None:
        return ""
    compact_tag(root)
    text = root.decode(formatter="minimal")
    text = re.sub(r">\s+<", ">\n<", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def first_text(tag: Tag, selector: str) -> str:
    node = tag.select_one(selector)
    return clean_text(node.get_text(" ", strip=True)) if node else ""


def section_text(section: Tag) -> str:
    lines = []
    title = first_text(section, ".menu-section-title")
    description = first_text(section, ".menu-section-description")
    if title:
        lines.append(title)
    if description:
        lines.append(description)

    for item in section.select(".menu-item"):
        item_title = first_text(item, ".menu-item-title")
        item_description = first_text(item, ".menu-item-description")
        price_top = first_text(item, ".menu-item-price-top")
        price_bottom = first_text(item, ".menu-item-price-bottom")
        price_or_text = price_bottom or price_top

        if not item_title and price_or_text:
            lines.append(price_or_text)
            continue

        if item_title:
            lines.append("")
            lines.append(item_title)
        if item_description:
            lines.append(item_description)
        if price_or_text and price_or_text != item_description:
            lines.append(price_or_text)

    return "\n".join(lines).strip()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--section-title", default="Lunch $10")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--format", choices=["text", "html"], default="text")
    args = parser.parse_args()

    soup = BeautifulSoup(args.input.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    target = None
    for section in soup.select(".menu-section"):
        title = section.select_one(".menu-section-title")
        if title and title.get_text(" ", strip=True) == args.section_title:
            target = section
            break
    if target is None:
        raise SystemExit(f"Section not found: {args.section_title}")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    body = section_text(target) if args.format == "text" else compact_html(target)
    args.output.write_text(f"{body}\n", encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
