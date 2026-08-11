# Research notes — DoorDash scraping and dish-image generation (August 2026)

Durable findings from two research threads:

1. **DoorDash menus** — found a far better data route than the JSON-LD one the
   project was using, built scraper/parser/normalizer around it, validated on
   4 restaurants / 375 items.
2. **Dish image generation** — tested sparse anchor masking, inpainting,
   outpainting, whole-image editing, low-resolution conditioning, blur, and
   prompt controls. No production-safe recipe generalized across dishes, but
   the failure modes and likely next directions are now much clearer.

---

## 1. DoorDash: the itemPage GraphQL route

### The finding

The old JSON-LD route (`parse_doordash_jsonld.py`) carries only
name/description/price — **no modifier/option data at all** — and silently drops
whole categories. Replaced by:

```
POST https://www.doordash.com/graphql/itemPage?operation=itemPage
```

**Only `storeId` + `itemId` are required.** The real page also sends a base64
`cursorContext.itemCursor`, a `consumerId` and an `x-csrftoken`; all three are
omissible and no sign-in is needed. Called same-origin from an already-open
store page so cookies/fingerprint come along free.

- `storeId` = numeric id in the store URL.
- `itemId` = `data-item-id` on each `[data-testid="MenuItem"]` card.
- Query captured verbatim: `external-data/menu-scraping/doordash_spike/itempage-query.graphql`

**Size-dependent modifier pricing arrives inline.** Each option in a `Sizes`
group carries its own `nestedExtrasList` priced for that size — the whole
size × topping matrix in one response. This is the case that forces a
click-per-size on Rezku.

### How it was found (do not repeat the dead end)

Monkeypatching `window.fetch`/`XMLHttpRequest` after page load records
**zero** requests — DoorDash's bundle captures its `fetch` reference before any
post-load injection. What worked: camofox's Playwright tracing
(`POST /tabs/{id}/trace/start` with `snapshots:true`), whose trace zip holds
full request/response bodies in `resources/*.json`.

### Scripts

| script | role |
|---|---|
| `external-data/scripts/spike_doordash_network_capture.py` | scrape: `open`/`items`/`harvest`/`click`/`dump`/`record`/`probe`/`close` |
| `external-data/scripts/parse_doordash_itempage.py` | harvest → project-standard menu JSON |
| `external-data/scripts/normalize_menu_sizes.py` | cross-restaurant size/title normalization |

Typical flow:

```bash
python external-data/scripts/spike_doordash_network_capture.py --user dd-<x>-spike open "https://www.doordash.com/store/<storeId>/"
python external-data/scripts/spike_doordash_network_capture.py --user dd-<x>-spike harvest <storeId> out-harvest.json --url "https://www.doordash.com/store/<storeId>/"
python external-data/scripts/parse_doordash_itempage.py out-harvest.json out-parsed.json
python external-data/scripts/normalize_menu_sizes.py out-parsed.json out-normalized.json --verbose
python external-data/scripts/spike_doordash_network_capture.py --user dd-<x>-spike close
```

`harvest` is ~15–25 min for 100–150 items under default pacing — run it
backgrounded, not in a foreground call that will time out.

### Validation

| restaurant | store id | items | shape |
|---|---|---|---|
| Maria's Mexican Grill | 2702259 | 56 | flat modifiers |
| Hungry Howie's Wyandotte | 26041747 | 116 | `Sizes` group + nested per-size |
| Jet's Pizza Lincoln Park | 258771 | 60 | size-per-item + variant groups |
| China House Detroit | 877937 | 143 | flat, menu-coded titles |

**375 items, 0 request failures.** Artifacts in
`external-data/menu-scraping/doordash_spike/` as
`<name>-itempage-{harvest,parsed}.json` + `<name>-normalized.json`.

### Four menu shapes seen (do not assume a `Sizes` group exists)

1. `Sizes` group + nested per-size modifiers (Howie's).
2. Size baked into separate items — "Small Thin Crust" / "Large Thin Crust" as
   13 distinct entries (Jet's build-your-own).
3. A per-item variant group named `Choose an option - <Item>` (Jet's specialty).
4. Size suffixes with **no siblings** — `(32qt)`, `(large)`, `(sm)` marking the
   only size sold (China House). These must **not** be merged.

`normalize_menu_sizes.py` converts 2 and 3 into shape 1, leaves 4 alone, and is
idempotent on shape 1.

### Gotchas encoded in the scripts

- **App-install sheet** (`[data-testid="LAYER-MANAGER-SHEET"]`) blocks the menu
  when a profile draws a narrow (~720px) viewport → item collection returns
  **zero items with no error**. Dismiss by clicking its "Keep using web" button.
  Note the sheet element is a *persistent layer host* present on every store
  page — check for a **visible, laid-out dismiss button**, not element presence.
- **Virtualized grid** — only ~10 cards mount at a time; must scroll
  top-to-bottom accumulating into a map keyed by item id. Side benefit: this
  auto-folds "Most Ordered"/"Featured Items" carousel duplicates.
- **Cross-sell ≠ modifiers** — groups with `type == "item"` list *other menu
  items* as upsells (720 of them on Howie's). Split into `cross_sell`, kept out
  of `options`/`option_index`. `type` is reliable; `nextCursor` is not.
- **`dietaryTagsList` is always empty** (checked across 1,443 options), so
  dietary flags are keyword-derived from option names — the weakest link, needs
  a review pass before shipping a badge.
- **Card price is often not buyable** — 98/116 Howie's items have a required
  group. `price_min`/`price_max` computed over required groups only.
- **Menu codes** — `C17.`, `S6.`, `33.`, `NO.6.` prefix 113/143 China House
  titles; extracted to `menu_code` with `original_title` kept. The pure-numeric
  case requires a trailing space so `1.50 TACO (TUESDAY)` isn't read as code
  `1`. Verified against 375 real titles; no false positives.

### Output schema (per item)

- `options` — DoorDash's **tree**, preserved (not flattened). Flattening is
  lossy because *availability* varies by size, not just price: Gluten Free Crust
  exists only on Small, Stuffed Crust only Medium/Large at different prices.
- `option_index` — flat, one row per option, with `available_when` +
  `price_by_parent`. Powers search.
- `dietary_badges` — derived, carries the same availability detail so card and
  picker agree.
- `price` / `price_min` / `price_max`, `cross_sell`, `menu_code`.

Worked example: Howie's Build Your Own → badge "Gluten free available",
`available_when: ['Small']`, `price_by_parent: {'Small': 3.45}`.

### Resilience (added after a real failure)

The camofox **browser died mid-harvest** at item 121/143 and the run lost
everything. Now: `TabLost` sentinel, `recover_tab()` (reopens under same profile),
**checkpoint every 10 items** with a `complete: true|false` flag, and `--resume`
(on by default) keyed by item id. Proven — China House resumed from a 60-item
checkpoint and finished.

### Detection posture

Requests are same-origin from a real browser with real cookies — that part is
fine. Residual risk is behavioral: no telemetry accompanies harvested calls, and
rate is the loudest signal. `--pacing human` (default) gives log-normal gaps
(median 2.0s, mean 8.2s, p95 57s), a 45–130s break every 12–22 items, and
**shuffled fetch order** (menu order is machine-tell; `menu_position` is
recorded and results re-sorted before writing). `--pacing fast` for spot checks.
Nothing was rate-limited or challenged across ~400 requests — but absence of a
block is not evidence of not being logged.

### Docs updated

- `external-data/menu-scraping/doordash-menu-scraping-notes.md` — full findings.
- `.claude/skills/doordash-menu-scraper/SKILL.md` — rewritten to lead with the
  itemPage route; JSON-LD demoted to fallback.

---

## 2. Dish-image reconstruction research

### Goal

Create menu images that are genuinely new rather than copies, while remaining
faithful to the food that a customer will actually receive. Pure text-to-image
generation is easy to differentiate but can invent ingredients, preparation,
portion, or presentation. High-fidelity editing has the opposite risk: it can
preserve too much of the source photograph.

### Approaches tested

The local experiment artifacts live under
`external-data/menu-scraping/image_gen_spike/`; that directory is intentionally
ignored by Git. Reusable runners and measurement scripts live under
`external-data/scripts/`.

1. **Sparse anchor patches and repeated reconstruction.** Kept scattered pieces
   of a source photo, removed the rest, and asked an image editor to reconstruct
   it over multiple rounds.
2. **Real mask-based inpainting.** Tested SDXL inpainting, Qwen Image Edit
   inpainting, FLUX inpainting, different mask shapes and densities, blurred
   edges, inverse masks, strength, guidance, and iteration sweeps.
3. **Outpainting from partial views.** Tried central squares, halves, and narrow
   strips with multiple model families, followed by possible inpainting of the
   original seed region.
4. **Whole-image editing and reframing.** Sent the full source or a downsampled
   thumbnail and asked for a slightly different framing or another preparation
   of the same dish.
5. **Resolution and blur sweeps.** Compared 64, 128, 256, and 512px reference
   inputs, sharp and Gaussian-blurred, on Nachos, Botana, and Rice Bowl images.
6. **Prompt controls.** Tested “same cook/different day,” localized changes,
   different preparation, visual-authority prompts, full menu descriptions, and
   explicit instructions not to add or emphasize ingredients.

### Methodology lessons

1. **Alpha alone does not remove information.** PNG stores RGB independently of
   alpha. A transparent source can still leak every original pixel if a model or
   service flattens it. Scrub or replace the RGB values of removed pixels before
   upload. This was verified locally after an early false result.
2. **Flat backgrounds inflate similarity metrics.** Large same-colour backdrop
   regions can match even when the dish is completely regenerated. Whole-image
   MAE and raw retained-pixel percentages are useful diagnostics but not
   sufficient measures of copying or visual fidelity.
3. **Mask polarity and two-stage order matter.** The intended workflow was the
   sparse 10–30% anchor mask first, followed by its inverse on the generated
   result. Confusing the inverse with the first-stage mask changes the experiment
   entirely.
4. **Blur and resolution interact nonlinearly.** Blur is not a continuous
   “difference” dial. A model may copy fuzzy structure at one level, then cross
   a threshold and semantically resynthesize a sharp image at a stronger blur.
   Equivalent proportional blur at different resolutions can still behave
   differently.
5. **Prompted ingredient names become visual suggestions.** When “jalapeño” was
   present in a menu description, FLUX repeatedly added conspicuous jalapeño
   rings even when instructed not to add or emphasize ingredients. Removing the
   ingredient list reduced that behavior but allowed worse guesses from the
   blurred image. Negation did not reliably override positive ingredient nouns.
6. **Fixed seeds expose semantic saturation.** Several differently worded
   prompts produced nearly identical outputs because the model mapped them to
   the same broad edit instruction. Numeric requests such as moving 3–5 versus
   6–10 chips were largely ignored.

### Findings

- The original sparse-anchor experiment with a general image editor either left
  visible patch geometry or regenerated a generic dish. It did not provide a
  useful fidelity/uniqueness balance.
- Real inpainting removed some boundary problems, but small masks changed too
  little and larger or inverse-mask passes introduced artifacts, blur, ingredient
  drift, or implausible structure. Results varied substantially by model.
- Outpainting from small snippets usually fell into one of two categories:
  surprisingly close to the original composition or clearly inferior food.
- Full-resolution whole-image edits were generally too close to the reference.
  Very small thumbnails could force a new preparation, but results were
  inconsistent and sometimes poor.
- On the three-dish thumbnail tests, 64–128px inputs often produced the most
  usable reconstructions. A 256px input with substantial blur could produce a
  sharper and more unique result, but also increased structural and ingredient
  hallucination. At 512px and low blur, the model began closely mimicking the
  original again.
- There was no stable blur, resolution, mask percentage, strength, guidance, or
  prompt setting that generalized across menu items. The apparent sweet spot is
  dish- and model-dependent.

### Current conclusion and return path

Getting the right balance between a genuinely new image and fidelity to reality
is hard with off-the-shelf image-edit endpoints. This research is paused, not
abandoned.

The current preferred long-term direction is to consider **fine-tuning our own
image reconstruction model** specifically for sparse food anchors. Training
pairs are easy to generate at scale: take a source food image as the target,
retain randomized masked anchor points covering roughly **10–25%** of it, scrub
all excluded pixels, and train the model to reconstruct a plausible complete
dish. Mask size, count, shape, softness, placement, and coverage can all be
randomized, yielding many training examples per source image. A useful training
and evaluation set should vary cuisine, plating, takeout containers, lighting,
camera quality, and background, and should hold out entire dishes/restaurants so
the model is tested on generalization rather than memorization.

The desired objective is not exact source recovery. It is ingredient and dish
fidelity with new chip/meat/topping geometry, natural mask integration, and low
source-expression retention. Evaluation therefore needs both similarity and
difference measures plus human review for ingredient correctness and food
plausibility.

If custom training is not practical, the fallback is to continue experimenting
with perspective changes, controlled downsampling and blur, prompt phrasing,
visible-ingredient conditioning, and newer models with explicit edit-strength
or denoising controls. Those techniques may still work as a heuristic pipeline,
but the completed sweeps do not yet justify treating any setting as production
safe.

---

## Naming

User floated "DishDash". Advised against: it's a **trademark** question not
copyright, and `-Dash` in the food-delivery vertical collides with DoorDash's
family of Dash marks (DashPass, DashMart, Dasher) in an adjacent/identical
market. Visual differentiation doesn't cure name similarity. Risk is ~zero while
private, real at public launch. Suggested direction: avoid `-Dash`/`-Eats`/
`-Grub`; lean on the search/discovery concept. Candidates floated: Forkcast,
Dishdex, Forklore, Findish, Bill of Fare, Menuscope, Cravemap, Mise.
Not lawyer advice; finalists need USPTO/domain/web clearance. Possible existing
"Dish Dash" Mediterranean restaurant (Sunnyvale CA) — unverified.

---

## Current state / immediate next steps

- No image-generation jobs are in flight.
- `external-data/menu-scraping/image_gen_spike/` contains the local generated
  images, manifests, metrics, and comparison viewers. It is reproducible
  experiment output and intentionally ignored by Git.
- Reusable image experiment scripts remain under `external-data/scripts/` and
  can be committed separately from the artifacts.
- The worktree contains several unrelated research, scraper, skill, and product
  documentation threads; commit them in coherent batches rather than one dump.

**Next, in rough priority:**
1. More restaurants for gotchas — `China 1` (store `25650917`) was queued
   specifically for **CJK item names** (`芝麻鸡`), still untested and a good
   stress test for title parsing / search indexing.
2. Decide the near-miss merge rule: Maria's `Large Side of Rice, Beans, or
   Papas` vs `Small Side of Rice, Beans, or Papas (8oz)` — blocked by the
   trailing `(8oz)`, reported not merged.
3. Sibling-item size grouping for shape-2 merchants is **not implemented** —
   needed before the size picker ships.
4. Dietary-badge keyword rules need a review pass against more restaurants.
5. Return to dish-image reconstruction later, beginning with a feasibility
   study for sparse-anchor fine-tuning rather than another broad prompt sweep.
