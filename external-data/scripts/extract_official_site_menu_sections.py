#!/usr/bin/env python3
"""Extract unique official-site menu sections as plain visible text."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

from bs4 import BeautifulSoup

from extract_official_site_menu_section import clean_text, first_text, section_text


DEFAULT_INPUT_DIR = Path("external-data/menu-scraping/official_site")
DEFAULT_OUTPUT_DIR = Path("external-data/menu-scraping/official_site/text/sections")
DEFAULT_COMBINED_OUTPUT = Path("external-data/menu-scraping/official_site/text/all-other-sections-text.txt")
DEFAULT_MANIFEST = Path("external-data/menu-scraping/official_site/text/sections-manifest.json")


def normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip().lower()


def slugify(text: str, fallback: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")
    return slug or fallback


def iter_sections(input_dir: Path):
    for path in sorted(input_dir.glob("*.html")):
        soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
        for section in soup.select(".menu-section"):
            body = section_text(section)
            if not body:
                continue
            title = first_text(section, ".menu-section-title")
            yield path, title, body


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input-dir", type=Path, default=DEFAULT_INPUT_DIR)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--combined-output", type=Path, default=DEFAULT_COMBINED_OUTPUT)
    parser.add_argument("--manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--exclude-title", action="append", default=["Lunch $10"])
    args = parser.parse_args()

    seen: dict[str, dict] = {}
    for source, title, body in iter_sections(args.input_dir):
        if title in args.exclude_title:
            continue
        key = hashlib.sha256(normalize_text(body).encode("utf-8")).hexdigest()
        if key in seen:
            seen[key]["source_pages"].append(source.name)
            continue
        seen[key] = {
            "title": title,
            "body": body,
            "source_pages": [source.name],
        }

    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.combined_output.parent.mkdir(parents=True, exist_ok=True)
    args.manifest.parent.mkdir(parents=True, exist_ok=True)

    manifest = []
    combined_parts = []
    used_slugs: set[str] = set()
    for index, item in enumerate(seen.values(), start=1):
        digest = hashlib.sha256(normalize_text(item["body"]).encode("utf-8")).hexdigest()[:8]
        slug = slugify(item["title"], f"section-{digest}")
        if slug in used_slugs:
            slug = f"{slug}-{digest}"
        used_slugs.add(slug)

        output = args.output_dir / f"{index:02d}-{slug}.txt"
        output.write_text(f"{item['body'].strip()}\n", encoding="utf-8")
        combined_parts.append(item["body"].strip())
        manifest.append(
            {
                "title": item["title"],
                "file": str(output),
                "source_pages": item["source_pages"],
                "chars": len(item["body"]),
            }
        )

    args.combined_output.write_text("\n\n\n".join(combined_parts).strip() + "\n", encoding="utf-8")
    args.manifest.write_text(json.dumps(manifest, indent=2), encoding="utf-8")

    print(f"wrote {len(manifest)} sections")
    print(args.combined_output)
    print(args.manifest)


if __name__ == "__main__":
    main()
