#!/usr/bin/env python3
"""Measure seed retention and source distance for the fixed outpainting sweep."""

import argparse
import json
from pathlib import Path

import numpy as np
from PIL import Image


ROOT = Path("external-data/menu-scraping/image_gen_spike")
SOURCE = ROOT / "fal-source-s01-square-1024.png"
DEFAULT_OUTPUT = ROOT / "outpaint_image_apps_v2_anchor_shapes_1024_2026-08-10"
CASES = {
    "center-square-320": (352, 352, 672, 672),
    "center-square-512": (256, 256, 768, 768),
    "left-half-512": (0, 0, 512, 1024),
    "center-strip-128": (448, 0, 576, 1024),
    "center-strip-256": (384, 0, 640, 1024),
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("output", nargs="?", type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args()
    output = args.output
    source = np.asarray(Image.open(SOURCE).convert("RGB"), dtype=np.float32)
    report = {}
    for name, (left, top, right, bottom) in CASES.items():
        result_image = Image.open(output / f"{name}.png").convert("RGB")
        if result_image.size != (source.shape[1], source.shape[0]):
            result_image = result_image.resize((source.shape[1], source.shape[0]), Image.Resampling.LANCZOS)
        result = np.asarray(result_image, dtype=np.float32)
        difference = np.abs(source - result).mean(axis=2)
        seed = np.zeros(source.shape[:2], dtype=bool)
        seed[top:bottom, left:right] = True
        generated = ~seed
        report[name] = {
            "seed_coverage_pct": float(seed.mean() * 100),
            "whole_mae": float(difference.mean()),
            "seed_mae": float(difference[seed].mean()),
            "generated_region_mae": float(difference[generated].mean()),
            "seed_exact_pixel_pct": float((difference[seed] == 0).mean() * 100),
            "whole_within_10_pct": float((difference <= 10).mean() * 100),
        }
    destination = output / "metrics.json"
    destination.write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
