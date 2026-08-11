#!/usr/bin/env python3
"""Extract PDF text with PyMuPDF using raw and block-oriented modes."""

from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
from typing import Any

import fitz


def clean(text: str) -> str:
    text = re.sub(r"[\x00-\x08\x0b-\x1f\x7f]", "", text)
    return re.sub(r"[ \t]+", " ", text).strip()


def block_text(block: dict[str, Any]) -> str:
    lines: list[str] = []
    for line in block.get("lines", []):
        spans = line.get("spans", [])
        text = clean("".join(span.get("text", "") for span in spans))
        if text:
            lines.append(text)
    return "\n".join(lines)


def extract_blocks(page: fitz.Page) -> list[dict[str, Any]]:
    blocks: list[dict[str, Any]] = []
    for block in page.get_text("dict", sort=False).get("blocks", []):
        if block.get("type") != 0:
            continue
        text = block_text(block)
        if not text:
            continue
        x0, y0, x1, y1 = block.get("bbox", (0, 0, 0, 0))
        max_size = 0.0
        for line in block.get("lines", []):
            for span in line.get("spans", []):
                max_size = max(max_size, float(span.get("size", 0.0)))
        blocks.append(
            {
                "page": page.number + 1,
                "bbox": [round(float(v), 2) for v in (x0, y0, x1, y1)],
                "x_center": round(float((x0 + x1) / 2), 2),
                "font_size": round(max_size, 2),
                "text": text,
            }
        )
    return blocks


def page_blocks_to_text(page: fitz.Page, blocks: list[dict[str, Any]]) -> str:
    if not blocks:
        return ""
    mid_x = page.rect.width / 2

    # Menus are often laid out as left/right columns. Preserve columns when the
    # page appears split; otherwise use natural top-to-bottom ordering.
    left = [b for b in blocks if b["x_center"] < mid_x]
    right = [b for b in blocks if b["x_center"] >= mid_x]
    if left and right and len(left) >= 3 and len(right) >= 3:
        ordered = sorted(left, key=lambda b: (b["bbox"][1], b["bbox"][0]))
        ordered += sorted(right, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    else:
        ordered = sorted(blocks, key=lambda b: (b["bbox"][1], b["bbox"][0]))
    return "\n\n".join(b["text"] for b in ordered)


def extract_pdf(input_pdf: Path, output_prefix: Path) -> None:
    fitz.TOOLS.reset_mupdf_warnings()
    fitz.TOOLS.mupdf_display_errors(False)
    fitz.TOOLS.mupdf_display_warnings(False)
    try:
        with fitz.open(input_pdf) as doc:
            raw_pages = [page.get_text().rstrip() for page in doc]
            block_pages: list[str] = []
            all_blocks: list[dict[str, Any]] = []
            for page in doc:
                blocks = extract_blocks(page)
                all_blocks.extend(blocks)
                block_pages.append(page_blocks_to_text(page, blocks).rstrip())
    finally:
        fitz.TOOLS.mupdf_display_errors(True)
        fitz.TOOLS.mupdf_display_warnings(True)

    output_prefix.parent.mkdir(parents=True, exist_ok=True)
    output_prefix.with_suffix(".fitz-raw.txt").write_text(
        "\n\n\f\n\n".join(page for page in raw_pages if page).rstrip() + "\n",
        encoding="utf-8",
    )
    output_prefix.with_suffix(".fitz-blocks.txt").write_text(
        "\n\n\f\n\n".join(page for page in block_pages if page).rstrip() + "\n",
        encoding="utf-8",
    )
    output_prefix.with_suffix(".fitz-blocks.json").write_text(
        json.dumps(all_blocks, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_pdf", type=Path)
    parser.add_argument("output_prefix", type=Path)
    args = parser.parse_args()
    extract_pdf(args.input_pdf, args.output_prefix)
    print(f"Wrote {args.output_prefix}.fitz-raw.txt and {args.output_prefix}.fitz-blocks.txt")


if __name__ == "__main__":
    main()
