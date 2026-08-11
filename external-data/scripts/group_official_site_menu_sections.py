#!/usr/bin/env python3
"""Group extracted official-site menu sections into logical plain-text inputs."""

from __future__ import annotations

import json
from pathlib import Path


MANIFEST = Path("external-data/menu-scraping/official_site/text/sections-manifest.json")
OUTPUT_DIR = Path("external-data/menu-scraping/official_site/text/section-groups")

GROUPS = [
    ("01-daily-specials", ["01-tuesday.txt", "02-wednesday.txt", "03-thursday.txt", "04-friday.txt", "05-saturday.txt", "06-sunday.txt"]),
    ("02-common-sides-salsa", ["07-salsa.txt", "09-additional-sides.txt", "12-dinner-sides.txt", "15-lunch-sides.txt"]),
    ("03-desserts-beverages", ["08-dessert.txt", "14-dessert-a7664dce.txt", "10-beverages.txt"]),
    ("04-dinner", ["11-dinner.txt"]),
    ("05-family-pack", ["13-section-61ee86b2.txt"]),
    ("06-mini-signature", ["16-mini-marias-6.txt", "17-signature-items.txt"]),
]


def main() -> None:
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))
    by_name = {Path(item["file"]).name: Path(item["file"]) for item in manifest}

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    grouped_manifest = []
    for group_name, file_names in GROUPS:
        parts = []
        for file_name in file_names:
            parts.append(by_name[file_name].read_text(encoding="utf-8").strip())
        output = OUTPUT_DIR / f"{group_name}.txt"
        output.write_text("\n\n\n".join(parts).strip() + "\n", encoding="utf-8")
        grouped_manifest.append(
            {
                "group": group_name,
                "file": str(output),
                "section_files": file_names,
                "chars": output.stat().st_size,
            }
        )

    manifest_output = OUTPUT_DIR / "section-groups-manifest.json"
    manifest_output.write_text(json.dumps(grouped_manifest, indent=2), encoding="utf-8")
    print(f"wrote {len(grouped_manifest)} groups")
    print(manifest_output)


if __name__ == "__main__":
    main()
