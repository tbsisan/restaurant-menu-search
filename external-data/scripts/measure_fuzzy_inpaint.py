#!/usr/bin/env python3
"""Measure source preservation across a grayscale, feathered inpainting mask."""

import argparse
import json

import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("mask")
    parser.add_argument("result")
    args = parser.parse_args()

    source = np.asarray(Image.open(args.source).convert("RGB"), dtype=np.float32)
    result = np.asarray(Image.open(args.result).convert("RGB"), dtype=np.float32)
    mask = np.asarray(Image.open(args.mask).convert("L"), dtype=np.float32)
    if source.shape != result.shape or source.shape[:2] != mask.shape:
        raise SystemExit(f"shape mismatch: {source.shape=}, {result.shape=}, {mask.shape=}")

    difference = np.abs(source - result).mean(axis=2)
    anchor_weight = (255 - mask) / 255
    generated_weight = mask / 255

    def weighted_mean(weight: np.ndarray) -> float:
        return float(np.sum(difference * weight) / np.sum(weight))

    def region_stats(selection: np.ndarray) -> dict[str, float]:
        values = difference[selection]
        return {
            "coverage_pct": float(selection.mean() * 100),
            "mae": float(values.mean()),
            "within_10_pct": float((values <= 10).mean() * 100),
            "within_25_pct": float((values <= 25).mean() * 100),
        }

    report = {
        "effective_anchor_coverage_pct": float(anchor_weight.mean() * 100),
        "weighted_anchor_mae": weighted_mean(anchor_weight),
        "weighted_generated_mae": weighted_mean(generated_weight),
        "dark_core": region_stats(mask <= 32),
        "feather": region_stats((mask > 32) & (mask < 223)),
        "white_field": region_stats(mask >= 223),
        "threshold_anchor": region_stats(mask < 128),
        "threshold_generated": region_stats(mask >= 128),
        "whole_image": region_stats(np.ones(mask.shape, dtype=bool)),
    }
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
