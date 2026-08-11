#!/usr/bin/env python3
"""Run Flux 2 Flash/Turbo edits from a 128px thumbnail to 512px output."""

from __future__ import annotations

import asyncio
import argparse
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import fal_client


ENV_FILE = Path.home() / "Projects/model-labs/.env.local"
SOURCE = Path("external-data/menu-scraping/image_gen_spike/reframe_thumbnail_128_flux_512_2026-08-10/source-128.png")
BASELINE_OUT_DIR = SOURCE.parent
SEPARATE_ORDER_OUT_DIR = Path(
    "external-data/menu-scraping/image_gen_spike/reframe_thumbnail_128_flux_separate_order_512_2026-08-10"
)
BASELINE_PROMPT = (
    "can you redo this image that is a tad more zoomed in and from a slightly more overhead perspective. "
    "Keep everything the same the lighting and food quality etc. It is a plate of nachos with orange "
    "and white melted cheese and shredded chicken."
)
SEPARATE_ORDER_PROMPT = (
    "Redo this as a separate order of the same menu item made by the same cook. Keep the same plate, "
    "restaurant setting, lighting, camera quality, overall portion, and ingredients, but naturally adjust "
    "the dish so the chip arrangement, melted orange and white cheese coverage, and shredded chicken "
    "placement are visibly different. Make it a tad more zoomed in and from a slightly more overhead "
    "perspective. Use only tortilla chips, orange and white melted cheese, and shredded chicken."
)
DIFFERENT_COOK_MISSING_NACHO_PROMPT = (
    "Redo this as a different preparation of the same menu item made by a different cook. Keep the same "
    "plate, restaurant setting, lighting, camera quality, ingredients, and a similar portion, but make the "
    "chip arrangement, melted orange and white cheese coverage, and shredded chicken placement clearly "
    "different. One nacho was taken from the plate just before the photo, leaving a small natural gap in "
    "the pile; do not show a hand or person. Make it a tad more zoomed in and from a slightly more overhead "
    "perspective. Use only tortilla chips, orange and white melted cheese, and shredded chicken."
)
DIFFERENT_COOK_PROMPT = (
    "Redo this as a different preparation of the same menu item made by a different cook. Keep the same "
    "plate, restaurant setting, lighting, camera quality, ingredients, and a similar portion, but make the "
    "chip arrangement, melted orange and white cheese coverage, and shredded chicken placement clearly "
    "different. Make it a tad more zoomed in and from a slightly more overhead perspective. Use only "
    "tortilla chips, orange and white melted cheese, and shredded chicken."
)
MISSING_NACHO_PROMPT = (
    "Redo this image while keeping the same plate, restaurant setting, lighting, camera quality, ingredients, "
    "overall portion, and food preparation as similar as possible. One nacho was taken from the plate just "
    "before the photo, leaving a small natural empty gap in the pile; the removed nacho is not visible, and "
    "no hand or person is visible. Make it a tad more zoomed in and from a slightly more overhead perspective. "
    "Use only tortilla chips, orange and white melted cheese, and shredded chicken."
)
SEED = 20260810
MODELS = [
    {"name": "flux-2-flash-edit", "endpoint": "fal-ai/flux-2/flash/edit", "guidance_scale": 2.5, "estimated_cost_usd": 0.010},
    {"name": "flux-2-turbo-edit", "endpoint": "fal-ai/flux-2/turbo/edit", "guidance_scale": 2.5, "estimated_cost_usd": 0.016},
]


def load_key() -> str:
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() in {"FAL_KEY", "FAL_API_KEY"}:
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"FAL_KEY or FAL_API_KEY not found in {ENV_FILE}")


def download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=180) as response:
        destination.write_bytes(response.read())


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--variant",
        choices=(
            "baseline",
            "separate-order",
            "different-cook-missing-nacho",
            "different-cook",
            "missing-nacho",
        ),
        default="baseline",
    )
    parser.add_argument("--source", type=Path, default=SOURCE)
    parser.add_argument("--source-size", type=int, default=128)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument("--only-flash", action="store_true")
    parser.add_argument("--seed", type=int, default=SEED)
    parser.add_argument("--prompt-file", type=Path)
    args = parser.parse_args()
    prompt = {
        "baseline": BASELINE_PROMPT,
        "separate-order": SEPARATE_ORDER_PROMPT,
        "different-cook-missing-nacho": DIFFERENT_COOK_MISSING_NACHO_PROMPT,
        "different-cook": DIFFERENT_COOK_PROMPT,
        "missing-nacho": MISSING_NACHO_PROMPT,
    }[args.variant]
    if args.prompt_file:
        prompt = args.prompt_file.read_text().strip()
    out_dir = args.output_dir or (
        SEPARATE_ORDER_OUT_DIR if args.variant == "separate-order" else BASELINE_OUT_DIR
    )
    source = args.source
    models = MODELS[:1] if args.only_flash else MODELS
    os.environ["FAL_KEY"] = load_key()
    if not source.exists():
        raise SystemExit(f"Missing thumbnail: {source}")
    out_dir.mkdir(parents=True, exist_ok=True)
    image_url = await fal_client.upload_file_async(source)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(source),
        "source_size": {"width": args.source_size, "height": args.source_size},
        "output_size": {"width": 512, "height": 512},
        "prompt": prompt,
        "variant": args.variant,
        "prompt_file": str(args.prompt_file) if args.prompt_file else None,
        "seed": args.seed,
        "models": models,
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    async def run(model: dict) -> dict:
        arguments = {
            "prompt": prompt,
            "image_urls": [image_url],
            "image_size": {"width": 512, "height": 512},
            "guidance_scale": model["guidance_scale"],
            "seed": args.seed,
            "num_images": 1,
            "enable_prompt_expansion": False,
            "enable_safety_checker": True,
            "output_format": "png",
            "sync_mode": False,
        }
        request_id = None

        async def on_enqueue(value: str) -> None:
            nonlocal request_id
            request_id = value
            (out_dir / f"{model['name']}-queued.json").write_text(
                json.dumps({"request_id": value, "endpoint": model["endpoint"]}, indent=2) + "\n"
            )

        try:
            result = await fal_client.subscribe_async(
                model["endpoint"], arguments=arguments, on_enqueue=on_enqueue, client_timeout=900
            )
            image = result["images"][0]
            await asyncio.to_thread(download, image["url"], out_dir / f"{model['name']}.png")
            record = {"request_id": request_id, "model": model, "arguments": arguments, "result": result}
        except Exception as exc:
            record = {"request_id": request_id, "model": model, "arguments": arguments, "error": repr(exc)}
        (out_dir / f"{model['name']}.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    records = await asyncio.gather(*(run(model) for model in models))
    summary = {
        "completed": sum("result" in record for record in records),
        "failed": sum("error" in record for record in records),
        "estimated_max_cost_usd": sum(model["estimated_cost_usd"] for model in models),
    }
    (out_dir / "results.json").write_text(json.dumps({**summary, "records": records}, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    asyncio.run(main())
