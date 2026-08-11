#!/usr/bin/env python3
"""Run the full nachos reframe prompt through four budget fal edit models at 512px."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import fal_client


ENV_FILE = Path.home() / "Projects/model-labs/.env.local"
SOURCE = Path("external-data/menu-scraping/image_gen_spike/fal-source-s01-square-1024.png")
OUT_DIR = Path("external-data/menu-scraping/image_gen_spike/reframe_full_source_fal_budget_512_2026-08-10")
PROMPT = (
    "can you redo this image that is a tad more zoomed in and from a slightly more overhead perspective. "
    "Keep everything the same the lighting and food quality etc. It is a plate of nachos with orange "
    "and white melted cheese and shredded chicken."
)
SEED = 20260810
MODELS = [
    {
        "name": "z-image-turbo-i2i",
        "endpoint": "fal-ai/z-image/turbo/image-to-image",
        "arguments": {"strength": 0.6, "num_inference_steps": 8, "acceleration": "regular"},
        "estimated_cost_usd": 0.005,
    },
    {
        "name": "flux-2-flash-edit",
        "endpoint": "fal-ai/flux-2/flash/edit",
        "arguments": {"guidance_scale": 2.5},
        "estimated_cost_usd": 0.01,
    },
    {
        "name": "flux-2-turbo-edit",
        "endpoint": "fal-ai/flux-2/turbo/edit",
        "arguments": {"guidance_scale": 2.5},
        "estimated_cost_usd": 0.016,
    },
    {
        "name": "qwen-image-edit",
        "endpoint": "fal-ai/qwen-image-edit",
        "arguments": {"num_inference_steps": 30, "guidance_scale": 4, "acceleration": "regular", "negative_prompt": " "},
        "estimated_cost_usd": 0.03,
    },
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
    os.environ["FAL_KEY"] = load_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    image_url = await fal_client.upload_file_async(SOURCE)
    manifest = {
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(SOURCE),
        "prompt": PROMPT,
        "image_size": {"width": 512, "height": 512},
        "seed": SEED,
        "models": MODELS,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    async def run(model: dict) -> dict:
        image_field = "image_url" if model["endpoint"] in {
            "fal-ai/z-image/turbo/image-to-image", "fal-ai/qwen-image-edit"
        } else "image_urls"
        arguments = {
            "prompt": PROMPT,
            image_field: image_url if image_field == "image_url" else [image_url],
            "image_size": {"width": 512, "height": 512},
            "seed": SEED,
            "num_images": 1,
            "enable_safety_checker": True,
            "output_format": "png",
            "sync_mode": False,
            **model["arguments"],
        }
        if model["endpoint"] != "fal-ai/qwen-image-edit":
            arguments["enable_prompt_expansion"] = False
        request_id = None

        async def on_enqueue(value: str) -> None:
            nonlocal request_id
            request_id = value
            (OUT_DIR / f"{model['name']}-queued.json").write_text(
                json.dumps({"request_id": value, "endpoint": model["endpoint"]}, indent=2) + "\n"
            )

        try:
            result = await fal_client.subscribe_async(
                model["endpoint"], arguments=arguments, on_enqueue=on_enqueue, client_timeout=900
            )
            image = result["images"][0]
            await asyncio.to_thread(download, image["url"], OUT_DIR / f"{model['name']}.png")
            record = {"request_id": request_id, "model": model, "arguments": arguments, "result": result}
        except Exception as exc:
            record = {"request_id": request_id, "model": model, "arguments": arguments, "error": repr(exc)}
        (OUT_DIR / f"{model['name']}.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    records = await asyncio.gather(*(run(model) for model in MODELS))
    summary = {
        "completed": sum("result" in record for record in records),
        "failed": sum("error" in record for record in records),
        "estimated_max_cost_usd": sum(model["estimated_cost_usd"] for model in MODELS),
    }
    (OUT_DIR / "results.json").write_text(json.dumps({**summary, "records": records}, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    asyncio.run(main())
