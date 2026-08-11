#!/usr/bin/env python3
"""Create uniformly distributed 20% anchor masks for the inpainting spike."""

from pathlib import Path

import numpy as np
from PIL import Image, ImageFilter


SIZE = 1024
OUT = Path("external-data/menu-scraping/image_gen_spike")


def circle_mask() -> np.ndarray:
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 26.35
    for row in range(8):
        cy = 64 + row * 128
        for column in range(12):
            cx = round((column + 0.5) * SIZE / 12)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return mask


def soft_circle_mask_15pct() -> np.ndarray:
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 22.82
    for row in range(8):
        cy = 64 + row * 128
        for column in range(12):
            cx = round((column + 0.5) * SIZE / 12)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=8)))


def soft_circle_mask_10pct() -> np.ndarray:
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 18.63
    for row in range(8):
        cy = 64 + row * 128
        for column in range(12):
            cx = round((column + 0.5) * SIZE / 12)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=10)))


def soft_circle_mask_half_size_double_count() -> np.ndarray:
    """Use 192 circles at half the 10% mask's radius, yielding about 5% coverage."""
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 18.63 / 2
    for row in range(12):
        cy = round((row + 0.5) * SIZE / 12)
        for column in range(16):
            cx = round((column + 0.5) * SIZE / 16)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=10)))


def soft_circle_mask_half_size_double_count_blur5() -> np.ndarray:
    """Match the 10% mask's circle-radius-to-blur ratio at about 5% coverage."""
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 18.63 / 2
    for row in range(12):
        cy = round((row + 0.5) * SIZE / 12)
        for column in range(16):
            cx = round((column + 0.5) * SIZE / 16)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=5)))


def soft_circle_mask_2_5pct_blur3_5() -> np.ndarray:
    """Halve the 5% mask's area while retaining its 192-circle distribution."""
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = (18.63 / 2) / np.sqrt(2)
    for row in range(12):
        cy = round((row + 0.5) * SIZE / 12)
        for column in range(16):
            cx = round((column + 0.5) * SIZE / 16)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=3.5)))


def soft_circle_mask_2_5pct_96_count_blur3_5() -> np.ndarray:
    """Halve the 5% circle count without making anchors sub-latent in size."""
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    radius = 18.63 / 2
    for row in range(8):
        cy = 64 + row * 128
        for column in range(12):
            cx = round((column + 0.5) * SIZE / 12)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=3.5)))


def soft_grid_circle_mask(rows: int, columns: int, radius: float, blur: float) -> np.ndarray:
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    yy, xx = np.ogrid[:SIZE, :SIZE]
    for row in range(rows):
        cy = round((row + 0.5) * SIZE / rows)
        for column in range(columns):
            cx = round((column + 0.5) * SIZE / columns)
            disk = (xx - cx) ** 2 + (yy - cy) ** 2 <= radius**2
            mask[disk] = 0
    return np.asarray(Image.fromarray(mask, mode="L").filter(ImageFilter.GaussianBlur(radius=blur)))


def vertical_line_mask() -> np.ndarray:
    mask = np.full((SIZE, SIZE), 255, dtype=np.uint8)
    # Eight evenly spaced bars totaling 204 columns, or 19.92% of the canvas.
    widths = [26, 25, 26, 25, 26, 25, 26, 25]
    for index, width in enumerate(widths):
        center = 64 + index * 128
        start = center - width // 2
        mask[:, start : start + width] = 0
    return mask


def save(name: str, values: np.ndarray) -> None:
    path = OUT / name
    Image.fromarray(values, mode="L").save(path)
    inverse_path = path.with_name(path.stem + "-inverse.png")
    Image.fromarray(255 - values, mode="L").save(inverse_path)
    black = float(np.mean(values == 0) * 100)
    gray = float(np.mean((values > 0) & (values < 255)) * 100)
    effective = float(np.mean((255 - values.astype(np.float32)) / 255) * 100)
    print(f"{path}: {black:.4f}% black, {gray:.4f}% gray, {effective:.4f}% effective")


save("fal-mask-s01-anchor20-small-circles-1024.png", circle_mask())
save("fal-mask-s01-anchor20-vertical-lines-1024.png", vertical_line_mask())
save("fal-mask-s01-anchor15-small-circles-blur8-1024.png", soft_circle_mask_15pct())
save("fal-mask-s01-anchor10-small-circles-blur10-1024.png", soft_circle_mask_10pct())
save(
    "fal-mask-s01-anchor05-half-circles-double-count-blur10-1024.png",
    soft_circle_mask_half_size_double_count(),
)
save(
    "fal-mask-s01-anchor05-half-circles-double-count-blur5-1024.png",
    soft_circle_mask_half_size_double_count_blur5(),
)
save(
    "fal-mask-s01-anchor025-circles-blur3p5-1024.png",
    soft_circle_mask_2_5pct_blur3_5(),
)
save(
    "fal-mask-s01-anchor025-96-circles-blur3p5-1024.png",
    soft_circle_mask_2_5pct_96_count_blur3_5(),
)
save(
    "fal-mask-s01-anchor15-384-circles-blur4-1024.png",
    soft_grid_circle_mask(rows=16, columns=24, radius=11.26, blur=4),
)
save(
    "fal-mask-s01-anchor25-96-circles-blur10p3-1024.png",
    soft_grid_circle_mask(rows=8, columns=12, radius=29.47, blur=10.3),
)
save(
    "fal-mask-s01-anchor25-384-circles-blur5p2-1024.png",
    soft_grid_circle_mask(rows=16, columns=24, radius=14.85, blur=5.2),
)
