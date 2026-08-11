---
name: grubhub-menu-scraper-v2
description: Capture and parse Grubhub restaurant menus into project-standard raw structured JSON, using the camofox-browser REST server (see camofox-startup skill) and DOM `evaluate` extraction instead of full-page HTML dumps. Use when Codex/Antigravity/Hermes/OpenCode/etc needs to scrape a Grubhub restaurant page or produce restaurant-specific Grubhub menu JSON under external-data/menu-scraping with raw/intermediate files under menus/raw without LLM canonicalization. Supersedes grubhub-menu-scraper for this project's current tooling.
---

# Grubhub Menu Scraper (v2)

## Overview

Use this skill to extract Grubhub restaurant menus from rendered browser pages into the project menu layout. Grubhub menus are lazy-loaded and virtualized, so extract while scrolling, not from the first render alone. Pull structured data out of the page with JS (`evaluate`), not by saving and parsing full-page HTML — Grubhub HTML is large and mostly noise.

## Output Layout

Write the final menu JSON here:

```text
external-data/menu-scraping/<restaurant-name>/menus/grubhub-menu-<restaurant-name>.json
```

Write raw and intermediate artifacts here:

```text
external-data/menu-scraping/<restaurant-name>/menus/raw/
```

Use a stable restaurant slug for `<restaurant-name>` such as `camino-real-wyandotte`. Check for an existing menu storage directory (including plausible name variants) before creating one. Keep Grubhub artifacts separate from DoorDash, Uber Eats, and official-site artifacts.

## Source Resolution

Resolve the Grubhub restaurant URL in this order, cheapest/most-trusted first:

1. **Passed-in URL.** If the caller already gave you a concrete `grubhub.com/restaurant/...` URL, use it directly and skip discovery entirely.
2. **`sources.json`.** Otherwise check `external-data/menu-scraping/<restaurant-name>/sources.json` for a `platforms.grubhub.url` entry. If present, use it.
3. **Google search fallback.** Otherwise discover it yourself: navigate to a Google search for the restaurant name+city+grubhub and check the order panel/"Order online" surface first — it often surfaces Grubhub (and DoorDash/Uber Eats) URLs directly. Otherwise check for a grubhub link in the results. Fall back to a direct Grubhub search if it doesn't.

If you had to fall back to step 3, upsert what you found into `sources.json` (create it if it doesn't exist) so later runs — for this or any other platform skill — can skip discovery. Don't overwrite entries for other platforms already in the file:

```json
{
  "restaurant": {
    "name": "Camino Real Mexican Grill",
    "slug": "camino-real-wyandotte",
    "address": "3851 Fort St, Wyandotte, MI 48192",
    "latitude": 42.19351025,
    "longitude": -83.1795100375
  },
  "platforms": {
    "grubhub": {
      "url": "https://www.grubhub.com/restaurant/...",
      "found_via": "google-order-panel",
      "resolved_at": "2026-07-01T12:00:00Z"
    },
    "doordash": { "url": "..." },
    "ubereats": { "url": "..." },
    "official_site": { "url": "..." }
  }
}
```

This file is shared across platform skills (`doordash-menu-scraper`, `grubhub-reviews-scraper`, etc.) — treat it as reference data you read and extend, not something you own exclusively.

## Workflow

1. Use the `camofox-startup` skill to get a running Camofox tab using headless mode unless headed/headful is requested. Give this restaurant its own `--user` profile, and set locale/timezone/geolocation for its market in the same request that opens the tab.
2. Resolve the Grubhub restaurant URL per Source Resolution above.
3. Navigate to the Grubhub restaurant page and let it render. Save one screenshot as evidence. Do not save full HTML as the default artifact — only capture it if JS extraction below fails and you need to debug selectors by hand.
4. Extract category tabs (`li[role="tab"]`) once, up front. Each item card already carries its own category name via the wrapper's `impressionid` (see Extraction Snippet), so this is a completeness cross-check — confirm every tab you saw here also shows up as a `category_name` on at least one extracted item — not the primary way of labeling items.
5. Loop: `evaluate` the extraction snippet below to pull currently-mounted sections/items as JSON, merge into an accumulator keyed by `(category_id or category_name, platform_item_id, name, price_text)` — deliberately scoped per category, not globally, since "Best Sellers" legitimately duplicates items that also live in their real category and both copies belong in the final output — then scroll by evaluating `window.scrollBy(0, Math.round(window.innerHeight * 0.7))` (see note below on why, not the tab's `scroll` endpoint, and why the step is viewport-relative rather than a fixed pixel amount). Stop after 3 consecutive scrolls add no new keys; that flatline is also what it looks like once you've scrolled past the end of the menu into the About/Reviews/FAQ content below it, so it's a reliable signal either way, not evidence something broke.
6. Save the accumulated raw JSON to `menus/raw/`.
7. Reshape into the final schema below and write it to `menus/grubhub-menu-<restaurant-name>.json`. Do not run LLM canonicalization in this skill.

## Extraction Snippet

Run this via the tab's `evaluate` endpoint after each scroll stop. It returns only mounted sections/items, not the page HTML:

```js
Array.from(document.querySelectorAll('article.restaurant-menu-item')).map(article => {
  const btn = article.querySelector('button.restaurant-menu-item__button') || article;
  const wrapper = article.closest('[data-testid^="Item"]');
  const testid = wrapper ? wrapper.getAttribute('data-testid') : '';
  // Category segment isn't always numeric (e.g. "popularItems", or a name-slug) —
  // capture whatever follows the item id instead of requiring digits.
  const [, wrapperItemId, categorySegment] = /^Item(\d+)-(.+)$/.exec(testid || '') || [];
  const text = btn.innerText.trim();
  const nameNode = article.querySelector('[data-testid="menu-item-name-container"] h6, h3, h4');
  // "Best Sellers"/pinned cards use simpler markup with no dedicated name
  // container at all — fall back to the first line of the button text.
  const name = (nameNode ? nameNode.innerText : '') || text.split('\n')[0] || '';
  // Pinned "Best Sellers" items report impressionid="popular_items" (a
  // technical value, not a display label) — map the known category_id to the
  // real label instead of surfacing the raw token as a section name.
  const categoryName = categorySegment === 'popularItems'
    ? 'Best Sellers'
    : (wrapper ? (wrapper.getAttribute('impressionid') || '') : '');
  return {
    // The button's own impressionid is the item id directly — prefer it over
    // parsing the wrapper's data-testid, and fall back only if it's missing.
    id: btn.getAttribute('impressionid') || wrapperItemId || '',
    category_id: categorySegment || '',
    // The wrapper's impressionid is the human-readable category name (e.g.
    // "Tortas & Mexican Sub") — no separate tab-to-id mapping needed.
    category_name: categoryName,
    name: name,
    description: (article.querySelector('[data-testid="menu-item-description"]') || {}).innerText || '',
    button_text: text,
    // Prefer the dedicated price node — a full-button-text regex can mismatch
    // if a description happens to mention a dollar amount (e.g. an accidental
    // in-store price). Only fall back to the regex if that node is missing.
    price: (article.querySelector('[data-testid="menu-item-price"]') || {}).innerText
      || (text.match(/\$[\d.]+\+?/) || [''])[0],
  };
});
```

Category ids for "Best Sellers"-style pinned sections, and possibly others, may not be numeric (`popularItems`, or a name-slug) — capture whatever string is there rather than requiring digits, since a strict numeric regex silently drops the item id too, not just the category. `impressionid` means different things depending on which element you read it from (item id on the button, category name on the wrapper) — don't assume it's the same field everywhere on the page. Confirm selectors on the live page before depending on them; see `references/grubhub-virtualized-menu-layout.md` for the layout this was learned from and how to re-derive it if Grubhub's markup has changed.

Scroll via `evaluate` (`window.scrollBy(0, Math.round(window.innerHeight * 0.7))`), not the tab's dedicated `scroll` endpoint — on a live restaurant page the endpoint left `window.scrollY` at `0` across 8 consecutive calls (verified directly), while `evaluate`-driven scrolling moved the page and mounted new items correctly.

Scale the step off the live `window.innerHeight` rather than a fixed pixel amount. `camofox-startup` deliberately leaves each profile's screen/viewport fingerprint randomized (observed anywhere from ~720px to ~1150px tall across profiles), so a constant step tuned against one viewport will either under-shoot on a short viewport — spending far more scroll/evaluate round-trips than needed re-scanning mostly the same content — or, more importantly, over-shoot on a tall one, jumping past whatever window the virtualizer keeps mounted around the current scroll position and genuinely missing items. `0.7` leaves ~30% overlap between consecutive extraction windows regardless of which viewport the profile got; re-evaluate `window.innerHeight` on every step rather than caching it once, since it also self-corrects if the page reflows mid-run.

## Final JSON Shape

```json
{
  "source": "grubhub",
  "captured_at": "2026-06-30T19:25:02Z",
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
  ],
  "extraction_notes": {
    "method": "Grubhub scroll extraction",
    "canonicalized": false
  }
}
```

Keep prices as strings — Grubhub uses modifiers such as `$10.99+`. Preserve typos and marketplace wording in raw extraction; don't clean up names/descriptions here.

## Helper Script

If a raw extraction already has `sections[].items[]` but doesn't exactly match the shape above (missing fields, different key names, needs dedup), reshape it conservatively instead of hand-editing:

```bash
python .agents/skills/grubhub-menu-scraper-v2/scripts/normalize_grubhub_scroll_raw.py \
  --raw external-data/menu-scraping/<restaurant-name>/menus/raw/grubhub-scroll-extracted-menu-raw.json \
  --restaurant-slug <restaurant-name> \
  --restaurant-name "Restaurant Name" \
  --url "https://www.grubhub.com/restaurant/..." \
  --address "street, city, state zip" \
  --out external-data/menu-scraping/<restaurant-name>/menus/grubhub-menu-<restaurant-name>.json
```

It does not infer missing descriptions, normalize names, parse option groups, or canonicalize prices — it only reshapes and dedupes.

## Pitfalls

- Do not use the Grubhub search page as the menu source.
- Do not treat first-render content as complete — Grubhub keeps only part of the menu mounted at a time.
- Do not save full-page HTML as the primary artifact or extraction input; use `evaluate` to pull structured data directly. Full HTML is a debug-only fallback.
- Do not merge Grubhub output into aggregate DoorDash/Uber Eats/official-site files.
- Do not canonicalize with an LLM here; this skill produces raw source-specific menu JSON.
- "Best Sellers" (or similarly pinned) sections stay mounted across every scroll stop and legitimately duplicate items that also live in their real category (confirmed: 6 of 120 entries in the Camino Real capture are exactly this). Dedupe *within* each category/section by `(platform_item_id, name, price_text)`; do not dedupe globally across sections, or you'll wrongly drop the Best Sellers copy (or its real-category copy) of each of those items.
- A stale `sources.json` URL that 404s, redirects to a generic search page, or otherwise fails to render a real menu is not proof the restaurant has no Grubhub listing — fall back to a fresh Google discovery search (step 3 of Source Resolution) before concluding that, and correct the file with what you find.
- Do not derive price by regexing the full button text as the primary method — a description can legitimately contain a `$` amount (e.g. an accidentally-included in-store price), which the regex can't tell apart from the real price. Use the dedicated `[data-testid="menu-item-price"]` node first; only regex the button text if that node is missing.
