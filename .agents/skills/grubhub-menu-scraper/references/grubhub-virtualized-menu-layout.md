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
- Item row `data-testid` values included the category id suffix, for example `Item23089111829-23089111487`.
- The item id/category id attribute lived on an ancestor `Item...` div above the `article`, not necessarily inside the article.
- Menu item cards appeared as contentful `button.restaurant-menu-item__button` nodes wrapped in `article.restaurant-menu-item` nodes.
- Card text contained item name, optional description/badge text, and price. Names were in heading tags; prices could be heading text or only a trailing dollar pattern in the full button text.
- Initial/featured content used a nested `div.menuSection` container.
- Lazy-loaded scrolled content appeared as a virtualized flat stream under containers like `data-testid="regular-sections"` and `data-testid="menu-items-container"`.
- Lazy section headers used `div.menuVirtualizedSection`, but item rows were often sibling groups in the virtualized stream, not nested descendants of that header.
- `Best Sellers` stayed present across scroll snapshots, so extraction needed deduplication.

## Extraction Strategy

1. Capture category tabs and their ids.
2. Scroll from top to bottom in fixed increments.
3. At each stop, extract visible section headers and visible item cards.
4. For each item card, climb ancestors to find platform item id and category id.
5. Map category ids back to tab labels when possible.
6. Dedupe within each section by `(platform_item_id, name, price_text)`.
7. Stop after reaching the bottom and seeing no new category/item pairs for multiple scroll stops.

## Camino Real Coverage Observed

The scroll pass exposed 20 categories and 120 item rows:

- Best Sellers: 6
- Tortas & Mexican Sub: 5
- Tacos: 15
- Appetizers: 11
- Burritos: 5
- Chimichangas: 2
- Tostadas: 2
- Quesadillas: 4
- Enchiladas: 4
- Traditional Dinners: 3
- Combinations: 4
- Vegetarian: 4
- What's on the Grill: 4
- Fajitas: 5
- Seafood: 4
- Caldos: 5
- Sides: 11
- Desserts: 8
- Beverages: 13
- Breakfast Menu: 5

Use this as a sanity check pattern, not a universal Grubhub category list.
