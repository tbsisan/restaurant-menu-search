#!/usr/bin/env python3
"""Create fixed, production-plausible source crops for outpainting tests."""

import argparse
from pathlib import Path

from PIL import Image


CASES = {
    "center-square-320": (352, 352, 672, 672),
    "center-square-512": (256, 256, 768, 768),
    "left-half-512": (0, 0, 512, 1024),
    "center-strip-128": (448, 0, 576, 1024),
    "center-strip-256": (384, 0, 640, 1024),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("out_dir", type=Path)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGB")
    if source.size != (1024, 1024):
        raise SystemExit(f"expected a 1024x1024 source, got {source.size}")
    args.out_dir.mkdir(parents=True, exist_ok=True)
    for name, box in CASES.items():
        crop = source.crop(box)
        path = args.out_dir / f"{name}.png"
        crop.save(path)
        print(f"{path}: {crop.width}x{crop.height}, {crop.width * crop.height / 1024**2 * 100:.2f}% of canvas")


if __name__ == "__main__":
    main()
