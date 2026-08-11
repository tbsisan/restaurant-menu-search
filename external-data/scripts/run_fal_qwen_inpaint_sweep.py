#!/usr/bin/env python3
"""Run a small concurrent parameter sweep against fal Qwen inpainting."""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

import fal_client


DEFAULT_ENV = Path.home() / "Projects/model-labs/.env.local"
DEFAULT_SOURCE = Path("external-data/menu-scraping/image_gen_spike/fal-source-s01-square-512.png")
DEFAULT_STAGE1_MASK = Path("external-data/menu-scraping/image_gen_spike/fal-mask-s01-anchor30-small-circles-512.png")
DEFAULT_STAGE2_MASK = Path("external-data/menu-scraping/image_gen_spike/fal-mask-s01-anchor30-small-circles-inverse-512.png")
DEFAULT_OUT = Path("external-data/menu-scraping/image_gen_spike/qwen_two_stage_sweep_512_2026-08-10")

PROMPT = (
    "Reconstruct the missing portions of the original image as one coherent plate of nachos. "
    "Continue directly from the preserved image fragments and match their exact photographic "
    "style, camera angle, lighting, exposure, color balance, focus, texture, plate, background, "
    "and shadows. The dish contains corn tortilla chips, melted orange and white cheese, and "
    "shredded seasoned chicken. Preserve the original composition and visual character. Blend "
    "all boundaries seamlessly with no visible circles, seams, or mask artifacts. Do not "
    "beautify, restyle, rearrange, or add ingredients, text, utensils, hands, or additional plates."
)

# Production-plausible exclusions derived from ingredients absent from the menu description,
# rather than visual guesses about the source photograph.
NEGATIVE_PROMPT = "jalapeños, peppers, avocado, guacamole, extra toppings"

CASES = [
    {"name": "g2_s45_t080", "guidance_scale": 2.0, "num_inference_steps": 45, "strength": 0.80},
    {"name": "g2_s45_t090", "guidance_scale": 2.0, "num_inference_steps": 45, "strength": 0.90},
    {"name": "g1_s45_t098", "guidance_scale": 1.0, "num_inference_steps": 45, "strength": 0.98},
    {"name": "g2_s45_t098", "guidance_scale": 2.0, "num_inference_steps": 45, "strength": 0.98},
    {"name": "g3_s45_t098", "guidance_scale": 3.0, "num_inference_steps": 45, "strength": 0.98},
    {"name": "g4_s45_t098", "guidance_scale": 4.0, "num_inference_steps": 45, "strength": 0.98},
    {"name": "g2_s30_t098", "guidance_scale": 2.0, "num_inference_steps": 30, "strength": 0.98},
    {"name": "g2_s50_t098", "guidance_scale": 2.0, "num_inference_steps": 50, "strength": 0.98},
    {"name": "g2_s45_t093", "guidance_scale": 2.0, "num_inference_steps": 45, "strength": 0.93},
    {"name": "g2_s45_t100", "guidance_scale": 2.0, "num_inference_steps": 45, "strength": 1.0},
    {"name": "g5_s45_t080", "guidance_scale": 5.0, "num_inference_steps": 45, "strength": 0.80},
    {"name": "g5_s45_t090", "guidance_scale": 5.0, "num_inference_steps": 45, "strength": 0.90},
    {"name": "g5_s45_t098", "guidance_scale": 5.0, "num_inference_steps": 45, "strength": 0.98},
    {"name": "g5_s45_t100", "guidance_scale": 5.0, "num_inference_steps": 45, "strength": 1.0},
]


def load_key(path: Path) -> str:
    if os.environ.get("FAL_KEY"):
        return os.environ["FAL_KEY"]
    for line in path.read_text().splitlines():
        key, sep, value = line.partition("=")
        if sep and key.strip() == "FAL_KEY":
            return value.strip().strip('"').strip("'")
    raise SystemExit(f"FAL_KEY not found in {path}")


def download(url: str, destination: Path) -> None:
    with urllib.request.urlopen(url, timeout=180) as response:
        destination.write_bytes(response.read())


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--env", type=Path, default=DEFAULT_ENV)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--stage1-mask", type=Path, default=DEFAULT_STAGE1_MASK)
    parser.add_argument("--stage2-mask", type=Path, default=DEFAULT_STAGE2_MASK)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT)
    parser.add_argument("--case", action="append", choices=[case["name"] for case in CASES])
    parser.add_argument("--stage1-only", action="store_true")
    parser.add_argument("--size", type=int, default=512)
    args = parser.parse_args()
    selected_cases = [case for case in CASES if not args.case or case["name"] in args.case]
    run_tag = "-".join(args.case) if args.case else None

    os.environ["FAL_KEY"] = load_key(args.env)
    args.out_dir.mkdir(parents=True, exist_ok=True)

    source_url, stage1_mask_url, stage2_mask_url = await asyncio.gather(
        fal_client.upload_file_async(args.source),
        fal_client.upload_file_async(args.stage1_mask),
        fal_client.upload_file_async(args.stage2_mask),
    )

    manifest = {
        "endpoint": "fal-ai/qwen-image-edit/inpaint",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source": str(args.source),
        "stage1_mask": str(args.stage1_mask),
        "stage2_mask": str(args.stage2_mask),
        "prompt": PROMPT,
        "negative_prompt": NEGATIVE_PROMPT,
        "fixed": {
            "seed": 20260810,
            "acceleration": "none",
            "image_size": {"width": args.size, "height": args.size},
            "output_format": "png",
            "num_images": 1,
        },
        "cases": selected_cases,
    }
    manifest_name = f"manifest-{run_tag}.json" if run_tag else "manifest.json"
    (args.out_dir / manifest_name).write_text(json.dumps(manifest, indent=2) + "\n")

    async def run_case(case: dict) -> dict:
        record = {"case": case, "stages": []}
        base_arguments = {
            "prompt": PROMPT,
            "negative_prompt": NEGATIVE_PROMPT,
            "image_size": {"width": args.size, "height": args.size},
            "num_inference_steps": case["num_inference_steps"],
            "guidance_scale": case["guidance_scale"],
            "strength": case["strength"],
            "seed": 20260810,
            "acceleration": "none",
            "num_images": 1,
            "output_format": "png",
            "enable_safety_checker": True,
        }

        async def run_stage(stage: int, image_url: str, mask_url: str) -> dict:
            request_id = None

            async def on_enqueue(value: str) -> None:
                nonlocal request_id
                request_id = value
                queued = {"case": case, "stage": stage, "request_id": value}
                (args.out_dir / f"{case['name']}-stage{stage}-queued.json").write_text(
                    json.dumps(queued, indent=2) + "\n"
                )

            arguments = {**base_arguments, "image_url": image_url, "mask_url": mask_url}
            result = await fal_client.subscribe_async(
                "fal-ai/qwen-image-edit/inpaint",
                arguments=arguments,
                on_enqueue=on_enqueue,
                client_timeout=900,
            )
            image = result["images"][0]
            suffix = ".png" if "png" in image.get("content_type", "") else ".jpg"
            await asyncio.to_thread(
                download, image["url"], args.out_dir / f"{case['name']}-stage{stage}{suffix}"
            )
            stage_record = {
                "stage": stage,
                "request_id": request_id,
                "arguments": arguments,
                "result": result,
            }
            (args.out_dir / f"{case['name']}-stage{stage}.json").write_text(
                json.dumps(stage_record, indent=2) + "\n"
            )
            return stage_record

        try:
            stage1 = await run_stage(1, source_url, stage1_mask_url)
            record["stages"].append(stage1)
            if not args.stage1_only:
                stage2 = await run_stage(2, stage1["result"]["images"][0]["url"], stage2_mask_url)
                record["stages"].append(stage2)
        except Exception as exc:
            record["error"] = repr(exc)
        (args.out_dir / f"{case['name']}.json").write_text(json.dumps(record, indent=2) + "\n")
        return record

    records = await asyncio.gather(*(run_case(case) for case in selected_cases))
    summary = {
        "completed": sum(len(row.get("stages", [])) == (1 if args.stage1_only else 2) for row in records),
        "failed": sum("error" in row for row in records),
        "records": records,
    }
    results_name = f"results-{run_tag}.json" if run_tag else "results.json"
    (args.out_dir / results_name).write_text(json.dumps(summary, indent=2) + "\n")
    print(json.dumps({"completed": summary["completed"], "failed": summary["failed"], "out_dir": str(args.out_dir)}))


if __name__ == "__main__":
    asyncio.run(main())
