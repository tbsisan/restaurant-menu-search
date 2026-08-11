---
name: camofox-startup
description: Start the camofox-browser (redf0x1 fork) server and open a tab ready for a scraping run. Use whenever a task needs a running Camofox instance for restaurant menu/review scraping or any other browser-automation research in this project.
---

# Camofox Startup

## Overview

Use this skill to bring the camofox-browser server (the redf0x1 fork, installed on `PATH` as `camofox`/`camofox-browser`, default port 9377) up and ready for a scraping spike. Default to headless. Switch to headed only when the user explicitly asks for headed/headful.

## Workflow

1. Check for an already-running server first: `camofox server status`. Reuse it when it reports `status: running`.
2. Start fresh with humanize on and headless as the default mode:
   ```
   CAMOFOX_HUMANIZE=true camofox server start --background
   ```
3. When the user asks for headed/headful instead, add `CAMOFOX_HEADLESS=false` to that same start command. On this Crostini (Penguin) box, real headed rendering needs `/tmp/.X0-lock` present so the server recognizes the real display; create it first with:
   ```
   printf '%10d\n' $(pgrep -f 'sommelier.*x-display=0') > /tmp/.X0-lock
   ```
4. Give each distinct research target (a restaurant, region, or task) its own `--user <id>` on `open` — that gives it its own persistent profile, cookies, and browser fingerprint. If uncertain, reuse the recentmost profile.
5. Set geolocation for the target area in the same request that opens the first tab. For exact coordinates (preferred), call the REST API directly:
   ```
   curl -X POST http://localhost:9377/tabs -H "Content-Type: application/json" -d '{
     "userId": "<spike-id>", "sessionKey": "default", "url": "<target-url>",
     "locale": "en-US", "timezoneId": "America/Detroit",
     "geolocation": { "latitude": 42.197513, "longitude": -83.269677 }
   }'
   ```
   Use the target's real coordinates and timezone for spikes outside the Detroit/Downriver area.
6. Leave `CAMOFOX_ALLOW_WEBGL`, `CAMOFOX_SCREEN_WIDTH`, and `CAMOFOX_SCREEN_HEIGHT` unset. The defaults keep WebGL enabled with a realistic spoofed fingerprint and generate a fresh, internally-consistent screen/viewport fingerprint per profile — exactly what a real scraping spike wants.
7. Confirm the tab came up with `camofox get-tabs` (or check the `tabId` returned by `open`/the API call) before handing off to the scraping logic.
