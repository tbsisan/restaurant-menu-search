# Sold-out / availability detection notes

Not implemented in the current menu-scrape parsers - only relevant once
we add ordering. Recorded here so the detection approach doesn't need to be
re-discovered later.

## Recommended approach

Markup for "sold out" varies per platform and can change without notice, so
the safest universal signal is a keyword search over the *whole* item card's
`textContent` (name, description, price, tags - everything), rather than
depending on a specific class name or testid: look for "sold out",
"out of stock", "unavailable", "86'd" (case-insensitive). Use a platform-
specific signal (below) as a faster/more precise check when known, and the
keyword search as a fallback for unfamiliar platforms/markup changes.

## Confirmed per-platform signals

- **Cash App**: item card contains the text "Sold out"; its
  `button[data-testid^="item-tile-add-"]` is `disabled`; no price is
  rendered at all for the item.
- **Toast**: a dedicated tag element inside `[data-testid="menu-item-tags"]`
  reads "OUT OF STOCK" (`.itemTag`, arbitrary background/text color set
  inline). Unlike Cash App, the price is still shown, just with an extra
  `outOfStock` class on the price `<span>` (`.price.outOfStock`).
- **Uber Eats / DoorDash / Grubhub / Square**: not checked yet.
