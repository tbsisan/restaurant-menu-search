#!/usr/bin/env python3
"""Create square sharp/blurred thumbnail inputs for cross-item Flux tests."""

from pathlib import Path

from PIL import Image, ImageFilter


ROOT = Path("external-data/menu-scraping/image_gen_spike")
OUT = ROOT / "reframe_cross_item_inputs_2026-08-11"
ITEMS = {
    "botana": {
        "source": ROOT / "source-02.jpg",
        "crop": (0, 150, 504, 654),
    },
    "rice-bowl": {
        "source": ROOT / "source-03.jpg",
        "crop": (112, 0, 784, 672),
    },
}
VARIANTS = (
    (64, 0),
    (64, 1),
    (128, 0),
    (128, 2),
    (256, 2),
    (256, 3),
    (256, 4),
    (256, 5),
    (256, 6),
    (256, 7),
    (256, 8),
    (512, 2),
    (512, 4),
    (512, 6),
    (512, 8),
    (512, 12),
    (512, 16),
)


def main() -> None:
    for slug, spec in ITEMS.items():
        item_dir = OUT / slug
        item_dir.mkdir(parents=True, exist_ok=True)
        square = Image.open(spec["source"]).convert("RGB").crop(spec["crop"])
        square.save(item_dir / "source-square.png")
        for size, blur in VARIANTS:
            image = square.resize((size, size), Image.Resampling.LANCZOS)
            if blur:
                image = image.filter(ImageFilter.GaussianBlur(radius=blur))
            suffix = "sharp" if blur == 0 else f"blur{blur}"
            image.save(item_dir / f"source-{size}-{suffix}.png")


if __name__ == "__main__":
    main()
