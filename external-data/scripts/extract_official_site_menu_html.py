#!/usr/bin/env python3
"""Extract compact `.menus` HTML blocks from official restaurant site pages."""

from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path
from typing import Any

from bs4 import BeautifulSoup, Tag


DEFAULT_INPUT_DIR = Path("external-data/menu-scraping/official_site")
DEFAULT_OUTPUT = DEFAULT_INPUT_DIR / "text/marias-official-site-menus-html.txt"
DEFAULT_PER_PAGE_DIR = DEFAULT_INPUT_DIR / "text/menus_html"
KEEP_CLASSES = {
    "menus",
    "menu-section",
    "menu-section-title",
    "menu-section-description",
    "menu-item",
    "menu-item-title",
    "menu-item-description",
    "menu-item-price-top",
    "menu-item-price-bottom",
}


def clean_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def compact_tag(tag: Tag) -> None:
    for child in list(tag.children):
        if isinstance(child, Tag):
            compact_tag(child)

    classes = [name for name in tag.get("class", []) if name in KEEP_CLASSES]
    tag.attrs = {"class": classes} if classes else {}

    if tag.name not in {"div", "span", "p", "br"}:
        tag.unwrap()


def compact_html(block: Tag) -> str:
    clone = BeautifulSoup(str(block), "html.parser")
    root = clone.select_one(".menus")
    if root is None:
        return ""
    compact_tag(root)
    text = root.decode(formatter="minimal")
    text = re.sub(r">\s+<", ">\n<", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def block_title(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    titles = [clean_text(node.get_text(" ", strip=True)) for node in soup.select(".menu-section-title")]
    return " / ".join(title for title in titles if title) or "untitled"


def extract_page(path: Path) -> list[dict[str, Any]]:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    blocks = []
    for index, block in enumerate(soup.select(".menus"), start=1):
        html = compact_html(block)
        if not html:
            continue
        blocks.append(
            {
                "page": path.stem,
                "index": index,
                "title": block_title(html),
                "hash": hashlib.sha256(html.encode("utf-8")).hexdigest()[:16],
                "html": html,
            }
        )
    return blocks


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--per-page-dir", type=Path, default=DEFAULT_PER_PAGE_DIR)
    args = parser.parse_args()

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.per_page_dir.mkdir(parents=True, exist_ok=True)

    seen: dict[str, dict[str, Any]] = {}
    page_counts = {}
    for path in sorted(args.input_dir.glob("*.html")):
        page_blocks = extract_page(path)
        page_counts[path.stem] = len(page_blocks)
        if page_blocks:
            page_text = []
            for block in page_blocks:
                page_text.extend(
                    [
                        f"<!-- source_page: {block['page']} -->",
                        f"<!-- menu_block: {block['index']} -->",
                        f"<!-- menu_title: {block['title']} -->",
                        block["html"],
                        "",
                    ]
                )
            (args.per_page_dir / f"{path.stem}.menus.html.txt").write_text("\n".join(page_text), encoding="utf-8")

        for block in page_blocks:
            existing = seen.get(block["hash"])
            if existing:
                existing["source_pages"].append(block["page"])
            else:
                seen[block["hash"]] = {**block, "source_pages": [block["page"]]}

    combined = [
        "# Maria's Mexican Grill official site `.menus` HTML",
        "",
        "These are compact, deduplicated HTML blocks extracted from divs with class `menus`.",
        "",
    ]
    for block in seen.values():
        combined.extend(
            [
                f"<!-- source_pages: {', '.join(block['source_pages'])} -->",
                f"<!-- first_source_page: {block['page']} -->",
                f"<!-- menu_title: {block['title']} -->",
                block["html"],
                "",
            ]
        )

    args.output.write_text("\n".join(combined), encoding="utf-8")
    print(f"Wrote {args.output} ({len(seen)} unique menu blocks)")
    for page, count in sorted(page_counts.items()):
        if count:
            print(f"  {page}: {count} blocks")


if __name__ == "__main__":
    main()
