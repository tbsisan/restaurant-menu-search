#!/usr/bin/env python3
"""Extract compact visible text from saved official-site HTML pages."""

from __future__ import annotations

import argparse
from pathlib import Path

from bs4 import BeautifulSoup


def visible_text(path: Path) -> str:
    soup = BeautifulSoup(path.read_text(encoding="utf-8", errors="ignore"), "html.parser")
    for tag in soup(["script", "style", "noscript", "svg"]):
        tag.decompose()
    lines = [line.strip() for line in soup.get_text("\n").splitlines() if line.strip()]
    return "\n".join(lines) + "\n"


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("input_dir", type=Path)
    parser.add_argument("output_dir", type=Path)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for path in sorted(args.input_dir.glob("*.html")):
        output = args.output_dir / f"{path.stem}.txt"
        output.write_text(visible_text(path), encoding="utf-8")
        print(output)


if __name__ == "__main__":
    main()
