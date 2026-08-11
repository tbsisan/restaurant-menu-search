#!/usr/bin/env python3
"""Retain only inpainting anchor pixels and fade everything else to transparency."""

import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("source", type=Path)
    parser.add_argument("mask", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()

    source = Image.open(args.source).convert("RGB")
    mask = Image.open(args.mask).convert("L")
    if source.size != mask.size:
        raise SystemExit(f"size mismatch: {source.size=} {mask.size=}")

    rgb = np.asarray(source, dtype=np.uint8)
    # The Qwen mask uses black for preserved anchors and white for regeneration.
    # Invert it to make anchor strength the source image's alpha channel.
    alpha = 255 - np.asarray(mask, dtype=np.uint8)
    # PNG can retain hidden RGB under transparent pixels. Scrub that channel by
    # preblending toward white, so dropping/ignoring alpha cannot reveal the source.
    weight = alpha.astype(np.float32)[..., None] / 255
    scrubbed_rgb = np.rint(rgb * weight + 255 * (1 - weight)).astype(np.uint8)
    rgba = np.dstack((scrubbed_rgb, alpha))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    Image.fromarray(rgba, mode="RGBA").save(args.output)
    print(
        f"{args.output}: mode=RGBA, effective opaque coverage="
        f"{float(alpha.astype(np.float32).mean() / 255 * 100):.4f}%, "
        f"fully transparent={float((alpha == 0).mean() * 100):.4f}%"
    )


if __name__ == "__main__":
    main()
