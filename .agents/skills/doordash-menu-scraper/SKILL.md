---
name: doordash-menu-scraper
description: Capture and parse DoorDash restaurant menus into structured raw artifacts, including full modifier/option data (sizes, toppings, required-vs-optional groups, per-size pricing). Use when scraping DoorDash, DoorDash-backed order.online/custom.order.online pages, or recovering better menu data from saved DoorDash HTML; covers the graphql/itemPage route for options and the older JSON-LD route as fallback.
---

# DoorDash Menu Scraper

## Overview

There are two routes. **Prefer the itemPage GraphQL route.** The JSON-LD route
is the fallback, kept because it still works on saved HTML and on
`order.online`-style surfaces.

| | itemPage GraphQL | JSON-LD |
|---|---|---|
| Modifier groups / options | yes, complete | **none at all** |
| Per-size topping pricing | yes, in one response | none |
| Category coverage | complete | drops whole categories |
| Needs a live browser | yes | no (works on saved HTML) |

JSON-LD carries only `name` / `description` / `offers.price`. It also silently
dropped four whole categories on a sampled restaurant. If the task needs options
or trustworthy categories, JSON-LD is not sufficient.

## Route A: itemPage GraphQL (preferred)

Endpoint, called same-origin from an already-open store page so cookies and
fingerprint come along:

```
POST https://www.doordash.com/graphql/itemPage?operation=itemPage
```

**Only `storeId` + `itemId` matter.** The real page also sends a base64
`cursorContext.itemCursor`, a `consumerId` and an `x-csrftoken` - all omissible,
and no sign-in is needed. `storeId` is the numeric id in the store URL;
`itemId` is `data-item-id` on each `[data-testid="MenuItem"]` card.

Query captured verbatim at
`external-data/menu-scraping/doordash_spike/itempage-query.graphql`.

### Workflow

1. Start camofox headed or headless per the `camofox-startup` skill.
2. Open the store page under its own `--user` profile, with the target's real
   geolocation and timezone.
3. Collect items, then harvest option data:

```bash
python external-data/scripts/spike_doordash_network_capture.py \
  --user dd-<store>-spike open "https://www.doordash.com/store/<storeId>/"
python external-data/scripts/spike_doordash_network_capture.py \
  --user dd-<store>-spike items
python external-data/scripts/spike_doordash_network_capture.py \
  --user dd-<store>-spike harvest <storeId> path/to/<store>-itempage-harvest.json
python external-data/scripts/parse_doordash_itempage.py \
  path/to/<store>-itempage-harvest.json path/to/<store>-itempage-parsed.json
python external-data/scripts/spike_doordash_network_capture.py \
  --user dd-<store>-spike close
```

`harvest` takes roughly 15-20 min for a ~116-item store under default pacing.
Run it in the background rather than in a foreground call that will time out.

### Response shape

`data.itemPage.optionLists[]` - `name`, `subtitle`, `isOptional`,
`minNumOptions`, `maxNumOptions`, `numFreeOptions`, `selectionNode`
(`single_select` / `multi_select`), and `options[]` with `name`, `unitAmount`
(**integer cents**), `nestedExtrasList`.

**Size-dependent pricing arrives inline.** Each option in a `Sizes` group carries
its own `nestedExtrasList` holding the modifier groups priced for that size - the
entire size x topping matrix in one response, no clicking. This is the case that
forces a click-per-size on Rezku. Observed nesting is 2 levels deep; write
recursive consumers anyway.

## Route B: JSON-LD (fallback)

Extract every `script[type="application/ld+json"]` from a rendered store page and
confirm `@type: "Menu"` with `hasMenuSection`. Use for saved HTML or when options
are not needed.

```bash
python .claude/skills/doordash-menu-scraper/scripts/extract_doordash_jsonld.py \
  --html path/to/rendered-doordash-page.html \
  --response path/to/output-doordash-jsonld-response.json \
  --parsed path/to/output-doordash-parsed.json \
  --text path/to/doordash-menu.txt
```

`parse_doordash_jsonld.py` needs a `--ratings` DOM extraction to work around the
"Most Ordered" duplicate rollup and the dropped categories. The itemPage route
needs neither: keying by `data-item-id` folds carousel duplicates automatically.

## Known pitfalls

- **App-install sheet blocks the menu.** camofox randomizes screen/viewport per
  profile; a narrow one (~720px) triggers DoorDash's mobile layout, which pops a
  "Browse <store> in app" sheet (`[data-testid="LAYER-MANAGER-SHEET"]`) over the
  page. Left up, the virtualized grid never mounts and item collection returns
  **zero items with no error**. Dismiss by clicking its "Keep using web" button -
  not by removing the node or pressing Escape, since DoorDash records the choice
  and stops re-showing it. `dismiss_interstitials()` handles this automatically.
- **The menu is a virtualized grid.** Only ~10 cards are mounted at once, so a
  single `querySelectorAll` misses nearly everything. Scroll top-to-bottom
  accumulating into a map keyed by item id.
- **In-page fetch/XHR hooks record nothing.** DoorDash's bundle captures its
  `fetch` reference before any post-load injection can patch it. To observe real
  traffic use browser-level Playwright tracing (`POST /tabs/{id}/trace/start`
  with `snapshots: true`); the trace zip's `resources/*.json` hold full bodies.
- **Cross-sell groups are not modifiers.** Groups with `type == "item"`
  ("Recommended Beverages", "Add Drinks With DoubleDash") list *other menu items*
  as upsells. Keep them out of the options/search index. `type` is the reliable
  discriminator; `nextCursor` is not.
- **`dietaryTagsList` is always empty** (checked across 1,443 options on two
  restaurants). Dietary flags must be keyword-derived from option names.
- **Card price is often not buyable.** 98 of 116 items on one store had a
  required group, so the real floor is card price + cheapest required selection.
  `parse_doordash_itempage.py` computes `price_min`/`price_max` for this.
- A Cloudflare "Just a moment" page or a search results page is not a menu.
- If extraction finds `Restaurant`/`Organization`/`FAQPage`/`BreadcrumbList` but
  no `Menu`, the page is incomplete or the wrong URL.

## Detection posture

Requests are same-origin from a real browser session, which is the part that
usually matters. Residual risk is behavioral: harvesting produces itemPage calls
with none of the telemetry a real modal-open fires, and rate is the loudest
signal. Keep `--pacing human` (the default: log-normal gaps, periodic 45-130s
breaks, shuffled fetch order), one profile per restaurant, and spread very large
stores across sessions. Nothing was rate-limited or challenged in testing, but
absence of a block is not evidence of not being logged.

## Reference

Full spike findings, validation numbers and schema rationale:
`external-data/menu-scraping/doordash-menu-scraping-notes.md`.
Older JSON-LD workflow detail: `references/doordash-jsonld-workflow.md`.
