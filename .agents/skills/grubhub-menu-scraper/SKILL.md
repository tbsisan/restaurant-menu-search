---
name: grubhub-menu-scraper
description: Capture and parse Grubhub restaurant menus into project-standard raw structured JSON. Use when Codex/Antigravity/Hermes/OpenCode/etc needs to scrape a Grubhub restaurant page, recover menu data from saved Grubhub HTML or Camofox scroll artifacts, inspect Grubhub virtualized menu DOM, or produce restaurant-specific Grubhub menu JSON under external-data/menu-scraping with raw/intermediate files under menus/raw without LLM canonicalization.
---

# Grubhub Menu Scraper

## Overview

Use this skill to extract Grubhub restaurant menus from rendered browser pages into the project menu layout. Grubhub menus are often lazy-loaded and virtualized, so capture menu data from rendered browser state while scrolling, not from the first saved HTML alone.

## Output Contract

Write the final menu JSON here:

```text
external-data/menu-scraping/<restaurant-name>/menus/grubhub-menu-<restaurant-name>.json
```

Write raw and intermediate artifacts here:

```text
external-data/menu-scraping/<restaurant-name>/menus/raw/
```

Use a stable restaurant slug for `<restaurant-name>` such as `camino_real_wyandotte`. Check if a menu storage directory already exists. If there is ambiguity to the restaurants real name, look for directories matching reasonable patterns. If no directories exist, create the needed directories. Keep source-specific artifacts separate from DoorDash, Uber Eats, and official-site artifacts.

## Workflow

1. Use Camofox with `humanize=True`.
2. Set browser context for the restaurant/local area:
   - `Camoufox(headless=not args.headful, humanize=True)`
   - `locale="en-US"`
   - `timezone_id="America/Detroit"` for Downriver/Detroit-area spikes
   - `geolocation={"latitude": target_lat, "longitude": target_lon}`
   - `permissions=["geolocation"]`
3. Find the real Grubhub restaurant URL. Prefer Google's restaurant side panel/order flow when available because it can reveal Grubhub, DoorDash, Uber Eats, and custom ordering URLs.
4. Open the Grubhub restaurant page, wait for render, and save evidence artifacts to `menus/raw/`: screenshot, rendered HTML when practical, visible text, and any DOM observation JSON.
5. Do bounded discovery before extraction. Inventory headings, buttons, links, roles, and `data-*` attributes; inspect small parent chains around candidate menu nodes. Do not ingest large HTML into context.
6. Scroll vertically through the menu until repeated scroll stops produce no new categories/items. Grubhub commonly keeps only part of the menu mounted at a time.
7. Extract menu sections and items from the rendered DOM. Preserve raw names, descriptions, price strings, platform ids, category ids, and raw button/card text.
8. Dedupe within each section by platform item id plus name plus price. Do not collapse items that appear in both `Best Sellers` and their normal category.
9. Save the final JSON using the schema below. Do not run LLM canonicalization in this skill.

## Final JSON Shape

Use this shape for `grubhub-menu-<restaurant-name>.json`:

```json
{
  "source": "grubhub",
  "restaurant": {
    "name": "Camino Real Mexican Grill",
    "slug": "camino_real_wyandotte",
    "platform_name": "Camino Real Mexican Grill",
    "url": "https://www.grubhub.com/restaurant/...",
    "address": "3851 Fort St, Wyandotte, MI 48192"
  },
  "menu": {
    "sections": [
      {
        "name": "Tacos",
        "platform_section_id": "23089111485",
        "items": [
          {
            "platform_item_id": "23089111566",
            "name": "Hard Shell Taco Dinner",
            "description": "3 hard shell taco served...",
            "price_text": "$13.59",
            "raw_text": "Hard Shell Taco Dinner ... $13.59",
            "source_category_id": "23089111485"
          }
        ]
      }
    ]
  },
  "raw_artifacts": [
    "external-data/menu-scraping/camino_real_wyandotte/menus/raw/grubhub-scroll-extracted-menu-raw.json"
  ]
}
```

Keep prices as strings because Grubhub uses modifiers such as `$10.99+`. Preserve typos and marketplace wording in raw extraction.

## Helper Script

Use the normalizer when a scroll extraction already has `sections[].items[]` like the Camino Real spike:

```bash
python .agents/skills/grubhub-menu-scraper/scripts/normalize_grubhub_scroll_raw.py \
  --raw external-data/menu-scraping/<restaurant-name>/menus/raw/grubhub-scroll-extracted-menu-raw.json \
  --restaurant-slug <restaurant-name> \
  --restaurant-name "Restaurant Name" \
  --url "https://www.grubhub.com/restaurant/..." \
  --address "street, city, state zip" \
  --out external-data/menu-scraping/<restaurant-name>/menus/grubhub-menu-<restaurant-name>.json
```

The helper is intentionally conservative: it reshapes raw extraction into the final project schema but does not infer missing descriptions, normalize names, parse option groups, or canonicalize prices.

## Grubhub Layout Reference

For DOM details learned from the Camino Real Grubhub spike, read `references/grubhub-virtualized-menu-layout.md` before working with a live or saved Grubhub page.

Key reminders:

- Category navigation often uses `li[role="tab"]`.
- Menu item cards often appear as `button.restaurant-menu-item__button` inside `article.restaurant-menu-item`.
- Item/category ids may live on ancestor nodes, not inside the item card.
- Later sections may be mounted through virtualized scrolling under containers such as `data-testid="regular-sections"` or `data-testid="menu-items-container"`.
- Initial HTML may contain only featured content, so visible page text or first-render HTML can be incomplete.

## Pitfalls

- Do not use the Grubhub search page as the menu source.
- Do not treat a partial first-page HTML capture as complete menu coverage.
- Do not paste or inspect huge HTML chunks in model context. Use parser scripts, bounded neighborhoods, `rg` snippets, browser DOM evaluation, or inspect element.
- Do not merge Grubhub output into aggregate DoorDash/Uber Eats/official-site files.
- Do not canonicalize with an LLM here; this skill produces raw source-specific menu JSON.
