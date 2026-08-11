#!/usr/bin/env python3
"""Run the five anchor-shape cases against fal Image Apps V2 Outpaint."""

from __future__ import annotations

import asyncio
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import fal_client


ENV_FILE = Path.home() / "Projects/model-labs/.env.local"
CROP_DIR = Path("external-data/menu-scraping/image_gen_spike/outpaint_anchor_crops_1024")
OUT_DIR = Path("external-data/menu-scraping/image_gen_spike/outpaint_image_apps_v2_anchor_shapes_1024_2026-08-10")
PROMPT = (
    "Continue this fragment into a coherent informal restaurant photo of one plate of nachos "
    "with corn tortilla chips, melted orange and white cheese, and shredded seasoned chicken. "
    "Match its lighting, exposure, color, focus, background, perspective, and shadows while "
    "creating natural new food and plate geometry. Use only those ingredients. No jalapenos, "
    "peppers, avocado, guacamole, sour cream, pico de gallo, text, utensils, hands, or extra "
    "plates. Blend the join seamlessly."
)
SEED = 20260810
CASES = [
    {"name": "center-square-320", "expand_left": 352, "expand_right": 352, "expand_top": 352, "expand_bottom": 352},
    {"name": "center-square-512", "expand_left": 256, "expand_right": 256, "expand_top": 256, "expand_bottom": 256},
    {"name": "left-half-512", "expand_left": 0, "expand_right": 512, "expand_top": 0, "expand_bottom": 0},
    {"name": "center-strip-128", "expand_left": 448, "expand_right": 448, "expand_top": 0, "expand_bottom": 0},
    {"name": "center-strip-256", "expand_left": 384, "expand_right": 384, "expand_top": 0, "expand_bottom": 0},
]


def load_key() -> str:
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    for line in ENV_FILE.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "FAL_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"FAL_KEY not found in {ENV_FILE}")


def download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=180) as response:
        destination.write_bytes(response.read())


async def main() -> None:
    os.environ["FAL_KEY"] = load_key()
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    urls = await asyncio.gather(*(fal_client.upload_file_async(CROP_DIR / f"{case['name']}.png") for case in CASES))
    manifest = {
        "endpoint": "fal-ai/image-apps-v2/outpaint",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "prompt": PROMPT,
        "seed": SEED,
        "cases": CASES,
    }
    (OUT_DIR / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")

    async def run(case: dict, image_url: str) -> dict:
        arguments = {
            "image_url": image_url,
            "prompt": PROMPT,
            "seed": SEED,
            "num_images": 1,
            "enable_safety_checker": True,
            "sync_mode": False,
            "output_format": "png",
            "zoom_out_percentage": 0,
            **{key: case[key] for key in ("expand_left", "expand_right", "expand_top", "expand_bottom")},
        }
        request_id = None

        async def on_enqueue(value: str) -> None:
            nonlocal request_id
            request_id = value
            (OUT_DIR / f"{case['name']}-queued.json").write_text(
                json.dumps({"request_id": value, "case": case}, indent=2) + "\n"
            )

        try:
            result = await fal_client.subscribe_async(
                "fal-ai/image-apps-v2/outpaint",
                arguments=arguments,
                on_enqueue=on_enqueue,
                client_timeout=900,
            )
            image = result["images"][0]
            destination = OUT_DIR / f"{case['name']}.png"
            await asyncio.to_thread(download, image["url"], destination)
            record = {"request_id": request_id, "case": case, "arguments": arguments, "result": result}
        except Exception as exc:
            record = {"request_id": request_id, "case": case, "arguments": arguments, "error": repr(exc)}
        (OUT_DIR / f"{case['name']}.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    records = await asyncio.gather(*(run(case, url) for case, url in zip(CASES, urls)))
    summary = {"completed": sum("result" in record for record in records), "failed": sum("error" in record for record in records)}
    (OUT_DIR / "results.json").write_text(json.dumps({**summary, "records": records}, indent=2) + "\n")
    print(json.dumps(summary))


if __name__ == "__main__":
    asyncio.run(main())
