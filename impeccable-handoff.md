# Impeccable Handoff

Last updated: 2026-06-23

## Current project context

- `PRODUCT.md` exists and the project register is `product`.
- `DESIGN.md` exists as a seed design system.
- No frontend implementation files were present during the shape runs.
- The repo is still in planning/shaping mode rather than implementation mode.

## Confirmed shape: `search-results`

This direction is confirmed and ready for later implementation.

### Screen intent

- Mobile-first dish search results screen.
- User already knows the dish/craving and wants to compare nearby versions quickly.
- Tone: trustworthy local utility tool, not delivery-app marketing.

### Confirmed layout direction

- Dense ledger/list rhythm.
- Strict three-column row structure.
- No row numbering.

### Row structure

1. Left column
- Restaurant-first possessive title, e.g. `Tanuki Ramen's Spicy Miso Ramen`
- Restaurant should carry slightly stronger emphasis than the dish portion.
- Short ingredient/description line.
- Compact supporting metadata such as distance and rating.

2. Middle column
- Dedicated price comparison column.
- Direct pickup price is primary.
- DoorDash price is secondary, smaller, and crossed out or visually muted.

3. Right column
- Compact `Order pickup` action.

### Visual direction

- Flat product UI.
- Off-white/light neutral canvas.
- Deep ink text.
- Thin gray dividers.
- One sans family.
- Restrained but lively warm accent system in the yellow/orange/red range.
- Restaurant emphasis should be mostly typographic, not loud color treatment.

### Notes to carry forward

- Long possessive titles will need truncation/wrapping rules.
- The price comparison is a core product differentiator and should remain visible at the row level.
- Savings treatment should stay credible and quiet, not promotional.

### Resume command

- `$impeccable craft search-results`

## Landing page shape status: in progress

Only the above-the-fold landing screen was explored. No final brief was locked.

### Landing direction already established

- This should feel like a `tool homepage with food cues`, not a generic delivery-app landing page.
- Value props to emphasize above the fold:
  - cheaper pickup prices / no restaurant cut
  - more restaurants than delivery apps
  - better dish-level search
- Some food-led probes were explored, but the strongest lane remained UI/tool-first.

### Six-panel landing probe summary

- `A`: strongest pure search-first utility hero
- `C`: strongest direct price-proof hero
- `D`: strongest proof of better search / broader restaurant coverage
- `E`: best way to introduce the AI phone-agent concept without centering the whole hero on it
- `B`: useful food-support direction
- `F`: more consumer-food-like, but closest to generic ordering-app territory

### Best hybrid direction for the next round

Combine:

- `A` search-first structure
- `C` price proof
- `D` broader coverage / stronger search evidence
- a small amount of `B` food support, but not `F`'s heavier food presence

### Unresolved landing questions

- How much real food imagery should remain in the final hero?
- Whether price proof should be the primary headline or a secondary evidence module.
- Whether the AI phone-agent concept should appear above the fold or just be hinted at.

### Resume command

- `$impeccable shape landing`

## Best way to resume later

If you want to continue the results screen:

- run `$impeccable craft search-results`
- mention this handoff file if needed

If you want to continue the landing page:

- run `$impeccable shape landing`
- mention this handoff file and ask to continue from the saved probe summary

## Useful file references

- `PRODUCT.md`
- `DESIGN.md`
- `impeccable-handoff.md`
