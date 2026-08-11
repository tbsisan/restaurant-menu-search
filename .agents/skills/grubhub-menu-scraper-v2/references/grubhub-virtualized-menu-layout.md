# Grubhub Virtualized Menu Layout

These notes come from the Camino Real Mexican Grill Wyandotte Grubhub spike. Confirm the layout on each new restaurant before depending on exact selectors.

## Discovery Method

Start with generic page inventory:

- visible text around the menu area
- headings
- buttons with prices
- links
- roles such as `tab`
- `data-*` attribute names and values

Then inspect small parent chains around candidate nodes. Avoid dumping full HTML into context; use bounded snippets, parser output, or browser DOM evaluation.

## Layout Model

- Category navigation appeared as `li` elements with `role="tab"`.
- Category tab ids looked like `menuNavCategory23089111487`.
- Each item is wrapped by an outer `div.menuItem` (not the `article` itself) shaped like:
  ```html
  <div class="menuItem menuItem--list ..." id="Item23089112104"
       data-testid="Item23089112104-23089111484"
       impressionid="Tortas &amp; Mexican Sub" ...>
    <article class="... restaurant-menu-item ..." data-testid="restaurant-menu-item">
      <button class="restaurant-menu-item__button" data-testid="restaurant-menu-item-button"
              impressionid="23089112104" ...>
        ...
      </button>
    </article>
  </div>
  ```
- The `data-testid` suffix after `Item<id>-` is **not always numeric** — it's a real category id for most sections but can be a non-numeric token (`popularItems`) or slug for others. Don't assume `\d+`; a regex that requires digits there will fail the whole match and silently drop the item id too, not just the category.
- `impressionid` is reused for two different things depending on which element you read it from: on the outer `div.menuItem` wrapper it's the **category display name** (e.g. `"Tortas & Mexican Sub"`), on the inner `button.restaurant-menu-item__button` it's the **numeric item id**. This is more direct than parsing `data-testid` for either value — use it as the primary source and the `data-testid` parse as a fallback/cross-check.
- Menu item cards appeared as contentful `button.restaurant-menu-item__button` nodes wrapped in `article.restaurant-menu-item` nodes.
- Name lives at `[data-testid="menu-item-name-container"] h6` inside the button. Description lives at `[data-testid="menu-item-description"]` (a `span`), as a sibling of the name container, not inside it — extract it separately rather than trying to split it out of the combined button text.
- Price has its own dedicated node: `<span data-testid="menu-item-price" itemprop="price">$13.50</span>`, inside a `div[data-testid="flattened-menu-item-price"]` sibling container. `itemprop="price"` is schema.org microdata, confirming this is the canonical price, not incidental button text. Prefer this node over regexing the full button text for a `$` pattern — a description can legitimately contain a dollar amount (e.g. an accidentally-included in-store price), which a full-text regex has no way to distinguish from the real price. Keep the regex only as a last-resort fallback if this node is ever missing.
- Initial/featured content used a nested `div.menuSection` container.
- Lazy-loaded scrolled content appeared as a virtualized flat stream under containers like `data-testid="regular-sections"` and `data-testid="menu-items-container"`.
- Lazy section headers used `div.menuVirtualizedSection`, but item rows were often sibling groups in the virtualized stream, not nested descendants of that header.
- `Best Sellers` stayed present across scroll snapshots, so extraction needed deduplication.
- The one card sampled with an `impressionid` category name (see HTML above) also had a `popular-item` class — hasn't yet been confirmed whether ordinary, non-pinned items reliably carry `impressionid` on the wrapper too. Verify this holds for a plain (non-Best-Seller) item before relying on it as a universal source.

## Extraction Strategy

1. Capture category tabs and their ids.
2. Scroll from top to bottom in increments sized off the live viewport (`window.innerHeight`), not a fixed pixel amount — Camofox randomizes the viewport per profile, and a step tuned for one viewport can under- or over-shoot on another.
3. At each stop, extract visible section headers and visible item cards.
4. For each item card, read `impressionid` off the wrapper (category name) and the button (item id) directly; fall back to parsing the wrapper's `data-testid` only if `impressionid` is missing.
5. Map category ids back to tab labels when a name wasn't already available via `impressionid`.
6. Dedupe within each section by `(platform_item_id, name, price_text)`.
7. Stop after reaching the bottom and seeing no new category/item pairs for multiple scroll stops.

## Confirmed by Live Test (2026-07-02)

Ran this against the live Camino Real Grubhub page via a camofox-browser tab to check the virtualization/dedup assumptions above:

- The tab's dedicated `POST /tabs/:id/scroll` endpoint did not move `window.scrollY` at all (8 consecutive calls, stayed at `0`). `evaluate`-driven `window.scrollBy(0, N)` worked and mounted new items as expected. Use `evaluate` for scrolling, not the `scroll` endpoint, on this page.
- "Best Sellers" (6 items) stayed mounted at every scroll position tested, top to bottom. The regular virtualized list did not: items visible at one scroll position were confirmed gone from the DOM a few scroll stops later, then did not reappear when scrolling back — this is real virtualization, not a stale assumption from the original spike.
- Once scrolled past the end of the actual menu, mounted item count collapses to just the 6 Best Sellers and stays there (confirmed via empty `data-testid="regular-sections"` and "Menu Info"/"Reviews"/"FAQs" headings at that scroll depth) — the flatline used as a stop signal is this, not a virtualizer failure.
- A scroll+accumulate pass recovered exactly 114 unique `platform_item_id`s — matching the full reference capture's unique-id count exactly (120 flattened item entries in that capture, minus the 6 Best Sellers items that are legitimately double-listed under their real category too). Confirms per-section dedup (not global dedup) is the correct behavior, and that the scroll+accumulate approach doesn't miss items when done carefully.

This layout was confirmed on one restaurant (Camino Real Mexican Grill, Wyandotte MI) via `external-data/scripts/spike_grubhub_from_google_places.py` and the saved HTML under `external-data/menu-scraping/camino_real_wyandotte_grubhub_spike/`. Treat it as a starting hypothesis, not a universal Grubhub DOM contract — re-run the discovery method above on each new restaurant before trusting these selectors.
