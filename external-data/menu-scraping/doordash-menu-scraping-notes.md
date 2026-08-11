# DoorDash Menu Scraping Notes

## Main Lesson

The useful DoorDash menu output comes from embedded JSON-LD, not from plain visible text or the accessibility snapshot.

The Maria's Mexican Grill spike produced good structured output by saving the rendered page's `script[type="application/ld+json"]` contents into:

- `external-data/menu-scraping/doordash_spike/marias-mexican-grill-doordash-jsonld-response.json`

Then it ran:

- `external-data/scripts/parse_doordash_jsonld.py`

That parser produced:

- `external-data/menu-scraping/doordash_spike/marias-mexican-grill-doordash-parsed.json`

The accessibility snapshot was useful for page evidence, visible ratings/reviews, and debugging, but it was not the source of the clean section/item menu.

## Recommended Workflow

1. Use Camofox with `humanize=True` for DoorDash and DoorDash-backed ordering surfaces.
2. Launch Camofox and set the browser context for the target local area:
   - `Camoufox(headless=not args.headful, humanize=True)`
   - `locale="en-US"`
   - `timezone_id="America/Detroit"`
   - `geolocation={"latitude": target_lat, "longitude": target_lon}`
   - `permissions=["geolocation"]`
3. Open the actual restaurant store URL, not only a search results page.
4. Wait for the page to render, scroll enough to load menu content, and save:
   - HTML
   - screenshot
   - accessibility snapshot or visible text, if available
   - JSON-LD scripts
5. Extract all `script[type="application/ld+json"]` contents.
6. Confirm JSON-LD contains `@type: "Menu"` with `hasMenuSection`.
7. Parse `Menu > hasMenuSection > hasMenuItem` into:
   - section
   - item title
   - description
   - price
8. Save separate outputs per source. Do not collapse DoorDash, Grubhub, Uber Eats, and official-site menus into one file except as an optional debug aggregate.

## Useful DoorDash URL Sources

Google's restaurant side panel/order flow can expose actual ordering providers and store URLs. Look for:

- Order online
- Order pickup
- Order delivery

The `custom.order.online` page is DoorDash-backed and may expose the same style of JSON-LD as `doordash.com`.

## Camino Real Recovery

The first Camino Real DoorDash text file was weak because it used visible page text. The better recovery came from extracting JSON-LD from:

- `external-data/menu-scraping/camino_real_wyandotte_spike/google-order-panel-en-store-camino-real-mexican-grill-wyandotte-238625-1415914-eb5b612085.html`

That produced:

- `external-data/menu-scraping/camino_real_wyandotte_spike/camino-real-wyandotte-doordash-jsonld-response.json`
- `external-data/menu-scraping/camino_real_wyandotte_spike/camino-real-wyandotte-doordash-parsed.json`
- `external-data/menu-scraping/camino_real_wyandotte_spike/doordash-menu.txt`

The structured Camino Real DoorDash parse found 16 sections and 91 items.

---

# Update (2026-08-03): the itemPage GraphQL endpoint supersedes JSON-LD

The JSON-LD route above is now the *fallback*, not the recommended path. JSON-LD
carries only `name` / `description` / `offers.price` per MenuItem - no modifier
groups at all - and it was already known to drop whole categories. Both problems
go away with `/graphql/itemPage`.

## How this was found

Spike script: `external-data/scripts/spike_doordash_network_capture.py`
(subcommands: `open`, `record`, `probe`, `items`, `click`, `dump`, `harvest`, `close`).

1. Monkeypatching `window.fetch` + `XMLHttpRequest` *after* page load recorded
   **zero** requests even though clicking an item clearly loaded modifier data.
   DoorDash's bundle captures its `fetch` reference before any post-load
   injection can patch it - so in-page hooks are not a usable interception
   technique here. Do not retry that approach.
2. What worked: browser-level capture via camofox's Playwright tracing
   (`POST /tabs/{id}/trace/start` with `snapshots: true`, then `/trace/stop`).
   The trace zip's `trace.network` + `resources/*.json` hold full request and
   response bodies. That surfaced the real call.

## The endpoint

```
POST https://www.doordash.com/graphql/itemPage?operation=itemPage
content-type: application/json
x-experience-id: doordash
apollographql-client-name: @doordash/app-consumer-production-ssr-client
apollographql-client-version: 3.0
```

Query captured verbatim to
`external-data/menu-scraping/doordash_spike/itempage-query.graphql` (18KB).

Confirmed live: **only `storeId` and `itemId` matter.** The real page also sends
a base64 `cursorContext.itemCursor` blob, a `consumerId` and an `x-csrftoken` -
all three are omissible, and no sign-in is required. Called same-origin from the
already-open store page so cookies/fingerprint come along for free.

`storeId` is the numeric id in the store URL. `itemId` comes from
`data-item-id` on each `[data-testid="MenuItem"]` card.

## Response shape

`data.itemPage.optionLists[]` - everything the item modal renders:

- `name`, `subtitle` ("Select 1", "Select up to 3")
- `isOptional`, `minNumOptions`, `maxNumOptions`, `numFreeOptions`
  (`numFreeOptions` covers the "choose TWO sides, both free" case)
- `selectionNode`: `single_select` | `multi_select`
- `options[]`: `name`, `unitAmount` (**integer cents**), `description`,
  `defaultQuantity`, `dietaryTagsList`, `nestedExtrasList`

`data.itemPage.itemHeader` gives the item's own name/description/`unitAmount`.

This makes DoorDash *cheaper* than the DOM-clicking platforms: required-vs-
optional is an explicit boolean instead of parsed rule text (cf. Rezku's
"must pick N" string parsing), and prices are exact integers.

## Scraping the store page

Categories are `h2`, item names are `h3`, cards are `[data-testid="MenuItem"]`
with `data-item-id`. The menu is a **virtualized grid** - only ~10 cards are
mounted at a time, so a single `querySelectorAll` misses almost everything.
`collect_items()` scrolls top-to-bottom accumulating into a page-level map keyed
by item id.

Useful side effect: keying by id auto-folds the "Most Ordered" / "Featured
Items" carousel duplicates into their real category, with no name matching
needed (unlike parse_doordash_jsonld.py's `--ratings` workaround). Because the
scroll runs top-to-bottom and later writes win, the real category always
overwrites the carousel's label.

## Validation run

Maria's Mexican Grill (store 2702259), 2026-08-03:
`marias-mexican-grill-itempage-harvest.json` - 56 unique items, 9 sections,
282 option groups, 1238 options (716 priced), **0 failures**, ~2.1MB.

Sections include `Additional Sides`, `Beverages`, `Kids Menu` and `Single Items`
- all four of which were **missing entirely from the JSON-LD**. This route fixes
the known category-dropping bug.

## Nested / size-dependent modifiers: CONFIRMED WORKING (2026-08-03)

Tested against Hungry Howie's Wyandotte (store 26041747), item "Build Your Own"
(17515684686) - artifact:
`doordash_spike/hungry-howies-build-your-own-itempage.json`

**The single itemPage response contains the entire size x topping price matrix.**
No clicking, no follow-up request, no cursor needed. Each option in the `Sizes`
group carries its own `nestedExtrasList` holding the full modifier groups priced
*for that size*:

```
Meats            Junior   Small  Medium   Large  X-Large
  Pepperoni        1.37    1.71    1.94    2.29     2.52
  Bacon            2.28    2.55    2.90    3.43     3.89
Veggies
  Mushroom         1.37    1.71    1.94    2.29     2.52
```

This is exactly the case that forced scrape_rezku_menu.py to click through every
size and re-read the modal after each one. On DoorDash it is one request, and
the result is *more* complete than the Rezku click-through (which can only
observe one size at a time).

Observed structure: nesting is **2 levels deep** - top-level `optionLists`, then
`options[].nestedExtrasList[].options[]`. No level-3 nesting was present. Code
consuming this should still recurse rather than hard-code two levels.

Correction to an earlier hypothesis: the `$isNested` query variable and
`nextCursor` field are **not** how nested modifiers are fetched - nested groups
arrive inline. `nextCursor` appears on cross-sell options (the "Recommended
Sides And Apps" / "Recommended Beverages" upsell groups, which point at other
*items*), not on modifier options.

## Detection posture

The request is same-origin from a real browser session with real cookies and
fingerprint, which is the part that usually matters. The residual risk is
behavioral, not cryptographic:

- The real client always sends a base64 `cursorContext.itemCursor`; omitting it
  is a cheap tell. It decodes to plain JSON and is fully constructible -
  `{itemId, storeId, menuId, categoryId, store_name, order_protocol, ...}` -
  where `menuId` is the trailing path segment of the store URL. Worth populating
  if this ever moves past spike status.
- Item modals normally fire analytics/telemetry beacons alongside the itemPage
  call. Harvesting produces itemPage calls with no accompanying telemetry - a
  correlation an anti-bot system can key on.
- Rate is the loudest signal: the validation run did 56 item fetches in ~3 min
  from one session. No human opens 56 modals that fast.

Mitigations in rough order of value: keep the randomized human delays (already
in `harvest`), spread large stores across sessions/profiles, populate
`cursorContext`, and prefer one profile per restaurant (per camofox-startup).
Nothing here was rate-limited or challenged during the spike - but absence of a
block is not evidence of not being logged.

## Parser: parse_doordash_itempage.py

Turns a `harvest` capture into project-standard menu JSON. Full schema rationale
lives in that script's docstring; the decisions worth knowing here:

- **`options` keeps DoorDash's tree** rather than flattening to Rezku's
  `price_by_size`. Flattening is lossy on DoorDash because *availability* varies
  by size, not just price (Gluten Free Crust exists only on Small; Stuffed Crust
  only on Medium/Large, at different prices). A merged list can't distinguish
  "not offered at this size" from "free at this size".
- Each item gets three layers: `options` (tree, drives the picker),
  `option_index` (one flat row per option carrying `available_when` +
  `price_by_parent`, drives search), and `dietary_badges` (drives result-card
  badges, carrying the same availability detail so card and picker agree).
- **`price` is base + cheapest *required* configuration**, not the card price.
  Maria's "Fajita (DINNER)" advertises $17.00 but every protein choice is
  required and the cheapest is +$2.00, so the real floor is $19.00.
  `price_min`/`price_max` bound the required-only range (optional groups are
  unbounded and meaningless as a range).
- Cross-sell groups (`type == "item"`) are split into `cross_sell`, never
  `options` - otherwise a DoubleDash six-pack reads as a taco topping.

Validation: `marias-mexican-grill-itempage-parsed.json` (56 items, 0 nested) and
`hungry-howies-byo-parsed.json` (1 item, 5 options with nested groups, gluten
free badge resolved to Small only).

## Full-store validation: Hungry Howie's Wyandotte (2026-08-04)

`hungry-howies-itempage-harvest.json` -> `hungry-howies-itempage-parsed.json`
116 items, 13 sections, **0 failures**, 157 options carrying nested groups.

- Nesting is **2 levels deep across all 116 items** - no level-3 anywhere. The
  only group that ever carries nested modifiers is `Sizes` (90 items). The
  recursion is still depth-agnostic, but "size is the nesting axis" holds for
  every item on this store.
- 98 of 116 items have at least one required group, so the card price is the
  wrong headline for most of the menu - `price_min` matters broadly, not just
  for pizzas.
- 216 cross-sell groups (720 upsell items) were split into `cross_sell` and kept
  out of `options`/`option_index`. Without that split those 720 would have
  polluted the search index.
- Gluten free resolved on 9 items, all in `Pizzas`, all `Small` only at +$3.45.
- Consistency check: "Build Your Own" fetched standalone on 2026-08-03 and again
  inside this harvest produced **byte-identical** option trees and price ranges.

### Pacing

`harvest --pacing human` (default) replaces the old flat uniform(0.9, 2.2) gap,
which was itself a fingerprint. Log-normal body plus two interruption layers:
median 2.0s, mean 8.2s, p95 57s, 11 gaps over 30s per ~116 items, and a 45-130s
break every 12-22 items. Fetch order is **shuffled** (menu_position is recorded
and results are re-sorted before writing) - walking a menu strictly top-to-bottom
is a machine tell no delay distribution fixes, and it made every session's
request sequence identical for a given store. `--pacing fast` restores the flat
behaviour for spot checks.

This run: 116 requests over ~18 min, no challenge, no rate limiting.

## Cross-store validation: Jet's Pizza Lincoln Park (2026-08-08)

`jets-pizza-itempage-harvest.json` -> `jets-pizza-itempage-parsed.json`
60 items, 10 sections, **0 failures**, ~9 min.

**The "size is the nesting axis" invariant from Howie's does NOT generalize.**
Jet's has *zero* nested option groups despite being a pizza restaurant. Merchants
model size differently, and all three shapes below appear on DoorDash:

1. **Sizes group + nested modifiers** (Howie's): one item, a `Sizes` group, each
   size carrying its own modifier groups priced for that size.
2. **Size baked into separate items** (Jet's "Build Your Own Jet's Pizza"):
   "Small Thin Crust", "Large Thin Crust", "X-Large Cheese Pizza" are 13 distinct
   top-level items, each with flat modifier groups. No nesting anywhere.
3. **A per-item variant group** (Jet's specialty pizzas): a required group named
   `Choose an option - <Item Name>` holding size/crust variants as flat options -
   e.g. Super Special: "Small Thin Crust (4 Pieces)" +$0.00 through
   "Party Tray (24 Pieces)" +$53.75.

`parse_doordash_itempage.py` handled all three unchanged - the nested path and
the flat path both already existed. But **downstream consumers cannot assume a
`Sizes` group exists**, and comparing sizes at a shape-2 merchant means grouping
sibling *items* by name pattern, which is a different problem from walking a
nested tree. That grouping is not implemented.

Dietary badges: gluten_free=13, cauliflower_crust=13. At Jet's, gluten free
appears two ways - as an option inside the specialty-pizza variant group
("Gluten Free (4 Pieces)" +$1.00), and as a standalone item ("Gluten Free
Pizza"). The badge caught the option form on 13 specialty pizzas. Shape 2 means
the standalone item is found by title, not by option, so a UI that only reads
`option_index` would miss it.

Also confirmed here: the `LAYER-MANAGER-SHEET` app-install interstitial (see
Known pitfalls in the skill) - it blocked the menu and made item collection
return **zero items with no error**.
