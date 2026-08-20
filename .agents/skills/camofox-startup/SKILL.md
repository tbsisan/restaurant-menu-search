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

## Link inventory

Prefer Camofox's link inventory over ad-hoc DOM extraction when you need to
discover a page's navigation or provider links:

```
camofox --user <user-id> get-links <tab-id>
```

The REST equivalent is:

```
GET /tabs/<tab-id>/links?userId=<user-id>&limit=1000&offset=0
```

The response contains `links` with `text` and `url`, plus pagination. Use this
first for Google result/Local-page links and provider discovery. Take an
accessibility snapshot only when an actual button or modal interaction is
needed (for example, opening Google’s `Order pickup` chooser).

For buttons on a normal Google Search results page, get a fresh ref from the
latest snapshot and immediately call the REST click endpoint:

```bash
curl -X POST http://localhost:9377/tabs/<tab-id>/click \
  -H 'Content-Type: application/json' \
  -d '{"userId":"<user-id>","ref":"e38"}'
```

Refs are snapshot-specific and may be stale after navigation or other DOM
changes. A successful click returns HTTP 200 with `{"ok":true,"url":"..."}`.
Do not use `curl -f` while diagnosing a click because it hides Camofox's JSON
error body. A CSS selector may be supplied as `selector` instead of `ref`.

## Google Maps place panels

Google Maps can switch into an accessibility-oriented view when an
accessibility snapshot is requested. That collapses the live place panel and
can close or destabilize a headed session. On a Maps place page, **do not use
`snapshot`**. Keep the panel open; inspect and click its visible `Order
online`/`Order pickup` control through the normal browser interaction path.

If Maps closes or the tab disappears, restart Camofox and open a new tab with
the **same** `userId` and `sessionKey: "default"` so its persistent profile is
reused. Do not mistake a persistent profile for a guarantee that a tab stays
alive.

## Bot-check protocol

If Google or another target shows a bot-check, CAPTCHA, "unusual traffic", or
similar challenge in a headed session:

1. **Stop immediately.** Do not navigate, search again, click around the
   challenge, create another profile, restart Camofox, or try to work around it.
2. Leave the headed tab and its profile open exactly as-is, then tell the user
   that manual navigation is required.
3. Resume automation only after the user explicitly says they have cleared the
   challenge. Reuse that same tab/profile and proceed at a human-scale pace.

Closing the tab or stopping the server is appropriate only if the user asks to
abandon the challenged session; doing so otherwise discards their opportunity to
clear it manually.
