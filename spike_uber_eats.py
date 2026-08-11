#!/usr/bin/env python3
"""
Spike: Load Uber Eats with headed Camofox browser.
Uses patterns from DoorDash spike: humanize=True, geolocation, locale, timezone.
"""

import asyncio
import argparse
from pathlib import Path
from typing import Any

from camoufox import AsyncCamoufox


async def close_known_modals(page: Any) -> None:
    """Dismiss dialogs that would otherwise sit on top of the page. Uber
    Eats itself shows a non-blocking inline "Available at X" banner for a
    closed restaurant (confirmed live, no modal to close there), but a
    fresh profile's first visit pops an "Allow your location" dialog with
    its own Close button - dismiss that so it doesn't obscure the
    screenshot or block later clicks if this script grows past a snapshot."""
    try:
        await page.get_by_role("button", name="Close").first.click(timeout=2000)
    except Exception:
        pass


async def main():
    parser = argparse.ArgumentParser(description="Spike Uber Eats with headed Camofox")
    parser.add_argument("--headful", action="store_true", help="Run headed (default: True)")
    parser.add_argument("--lat", type=float, default=42.3314, help="Latitude (default: Detroit area)")
    parser.add_argument("--lon", type=float, default=-83.0458, help="Longitude (default: Detroit area)")
    parser.add_argument("--url", type=str, default="https://www.ubereats.com", help="Starting URL")
    args = parser.parse_args()

    artifacts_dir = Path("artifacts/uber_eats_spike")
    artifacts_dir.mkdir(parents=True, exist_ok=True)

    async with AsyncCamoufox(
        headless=not args.headful,
        humanize=True,
        locale="en-US",
        timezone_id="America/Detroit",
        geoip=True,
    ) as browser:
        context = await browser.new_context(
            geolocation={"latitude": args.lat, "longitude": args.lon},
            permissions=["geolocation"],
            locale="en-US",
            timezone_id="America/Detroit",
        )
        page = await context.new_page()

        print(f"Navigating to {args.url}...")
        await page.goto(args.url, wait_until="networkidle", timeout=60000)

        # Wait for page to settle
        await page.wait_for_timeout(3000)
        await close_known_modals(page)

        # Save screenshot
        screenshot_path = artifacts_dir / "uber_eats_initial.png"
        await page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved: {screenshot_path}")

        # Save HTML
        html_path = artifacts_dir / "uber_eats_initial.html"
        html_content = await page.content()
        html_path.write_text(html_content)
        print(f"HTML saved: {html_path} ({len(html_content)} chars)")

        # Print page title and URL
        print(f"Page title: {await page.title()}")
        print(f"Final URL: {page.url}")

        # Keep browser open for manual inspection
        print("\nBrowser is open. Press Ctrl+C to close.")
        try:
            await asyncio.Event().wait()
        except KeyboardInterrupt:
            print("\nClosing...")


if __name__ == "__main__":
    asyncio.run(main())