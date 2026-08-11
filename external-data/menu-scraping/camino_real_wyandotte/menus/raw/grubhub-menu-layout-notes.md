# Grubhub Menu Layout Spike Notes

Method: from-scratch bounded discovery. Started with generic page inventory: visible text, tag counts, `data-*` attribute names, roles, headings, buttons, and links. Then inspected small parent chains around the generic discoveries: `role="tab"` category nodes and contentful priced buttons. Finally used scroll-only Camofox snapshots to observe lazy-loaded sections.

## Layout Model

- Category navigation appears as `li` elements with `role="tab"`; each visible tab text is a menu category.
- Category tab ids look like `menuNavCategory23089111487`; item row `data-testid` values include the same category id suffix, for example `Item23089111829-23089111487`.
- The item id/category id attribute lives on an ancestor `Item...` div above the `article`, not necessarily inside the article.
- Menu item cards appear as contentful `button.restaurant-menu-item__button` nodes, wrapped in `article.restaurant-menu-item` nodes.
- The card text contains name, optional description/badge text, and price. Names are in heading tags; prices may be heading text or only a trailing dollar pattern in the full button text.
- Initial/featured content uses a nested `div.menuSection` container. Lazy-loaded scrolled content is a virtualized flat stream under `data-testid="regular-sections"` / `data-testid="menu-items-container"`.
- Lazy section headers use `div.menuVirtualizedSection`, but their item rows are often sibling groups in the virtualized stream, not nested descendants of that header.
- The page lazy-loads/virtualizes sections during vertical scroll. The initial saved HTML only contained `Best Sellers`; scrolling exposed other sections and item cards.
- `Best Sellers` remains present across snapshots, so extraction must dedupe items across scroll stops.

## Scroll Evidence

- `step-00` y=0: Best Sellers (6)
- `step-01` y=850: Best Sellers (6), Tortas & Mexican Sub (5), Tacos (15)
- `step-02` y=1580: Best Sellers (6), Tortas & Mexican Sub (5), Tacos (15)
- `step-03` y=2310: Best Sellers (6), Tortas & Mexican Sub (5), Tacos (15), Appetizers (11)
- `step-04` y=3040: Best Sellers (6), Appetizers (9), Burritos (5)
- `step-05` y=3770: Best Sellers (6), Appetizers (9), Burritos (5), Chimichangas (2), Tostadas (2), Quesadillas (4)
- `step-06` y=4500: Best Sellers (6), Appetizers (9), Burritos (5), Chimichangas (2), Tostadas (2), Quesadillas (4), Enchiladas (4)
- `step-07` y=5230: Best Sellers (6), Enchiladas (4), Traditional Dinners (3), Combinations (4)
- `step-08` y=5960: Best Sellers (6), Enchiladas (4), Traditional Dinners (3), Combinations (4), Vegetarian (4), What's on the Grill (4)
- `step-09` y=6690: Best Sellers (6), Enchiladas (4), Traditional Dinners (3), Combinations (4), Vegetarian (4), What's on the Grill (4), Fajitas (5), Seafood (4)
- `step-10` y=7420: Best Sellers (6), Fajitas (5), Seafood (4), Caldos (5)
- `step-11` y=8150: Best Sellers (6), Fajitas (5), Seafood (4), Caldos (5), Sides (11)
- `step-12` y=8880: Best Sellers (6), Fajitas (5), Seafood (4), Caldos (5), Sides (11), Desserts (8)
- `step-13` y=9610: Best Sellers (6), Desserts (8), Beverages (13)
- `step-14` y=10340: Best Sellers (6), Desserts (8), Beverages (13), Breakfast Menu (5)
- `step-15` y=11070: Best Sellers (6), Breakfast Menu (5)
- `step-16` y=11800: Best Sellers (6)
- `step-17` y=12530: Best Sellers (6)

## Extracted Coverage

- Best Sellers: 6 items
- Tortas & Mexican Sub: 5 items
- Tacos: 15 items
- Appetizers: 11 items
- Burritos: 5 items
- Chimichangas: 2 items
- Tostadas: 2 items
- Quesadillas: 4 items
- Enchiladas: 4 items
- Traditional Dinners: 3 items
- Combinations: 4 items
- Vegetarian: 4 items
- What's on the Grill: 4 items
- Fajitas: 5 items
- Seafood: 4 items
- Caldos: 5 items
- Sides: 11 items
- Desserts: 8 items
- Beverages: 13 items
- Breakfast Menu: 5 items
