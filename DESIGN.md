<!-- SEED: re-run /impeccable document once there's code to capture the actual tokens and components. -->
---
name: Restaurant Menu Search
description: A dish-level local menu search engine with lower prices and more restaurants.
---

# Design System: Restaurant Menu Search

## 1. Overview

**Creative North Star: "The Neighborhood Dish Ledger"**

The Neighborhood Dish Ledger is a visual system built around utility, speed, and community trust. Borrowing from the raw functional layout of Craigslist and Hacker News, its updated with the typographic precision of modern developer tools like Linear, this system rejects visual clutter in favor of rapid information retrieval. The landing page can have more blingand be visually interesting. The search results however is designed to look like a tool more than a marketplace.

The main results page explicitly rejects the visual vocabulary of corporate delivery platforms. There are no bloated food cards, heavy drop shadows, or generic marketing illustrations. Instead, the interface acts as a clean, highly legible index of real food from real places, presenting information cleanly so the user can search, compare, and order their craving immediately.

**Key Characteristics:**
- Structure is the interface: layout defined by high-contrast lines, borders, and clean typographic grids.
- Extreme speed and low latency, optimized for mobile-first utility.
- Restrained color application to highlight functional actions.

## 2. Colors

The palette is energetic yet restrained, utilizing a color from the yellow/orange/red area as the single primary accent color on a high-contrast, clean neutral canvas.

**The Restrained Utility Rule.** The primary color (not yet decided) is reserved for primary action targets (such as launching search or confirming an order), critical states, and conveying information hierarchies. It must never exceed 10% of any given screen's surface area.

### Primary
- **Undecided yellow/orange/red** `[to be resolved during implementation]`: Used for primary action buttons, main search highlight, and active interactive states.

### Neutral
- **White or Off-White Canvas** `[to be resolved during implementation]`: The main body background.
- **Deep Ink Text** `[to be resolved during implementation]`: The high-contrast color for body copy and headings.
- **Border Grey** `[to be resolved during implementation]`: The functional color for borders and high-contrast layout dividers.

## 3. Typography

**Display Direction:** Single Sans - Technical / Geometric (extremely clean, readable, high speed vibe)
**Body Direction:** Single Sans - Technical / Geometric

**Character:** Pure typographic utility. Clean, geometric, and high-readability sans-serif fonts optimized for scanning dish listings on mobile viewports.

### Hierarchy
- **Display** `[to be resolved during implementation]`: Hero search prompts and landing states.
- **Headline** `[to be resolved during implementation]`: Main dish titles and key section headers.
- **Title** `[to be resolved during implementation]`: Restaurant names and grouping labels.
- **Body** `[to be resolved during implementation]`: Menu descriptions and pricing details (max line length capped at 65ch).
- **Label** `[to be resolved during implementation]`: Small metrics, ratings, distance, and tags.

## 4. Elevation

This system uses a completely flat layout. Depth and hierarchy are established through crisp borders, solid background fills, and typographic scale, rather than drop shadows.

**The Flat-By-Default Rule.** All cards, search inputs, and sections are flat at rest. Depth cues and subtle elevations appear only as a response to interactive states (e.g., hover or active click) to maintain a fast, low-overhead visual experience.

## 5. Components

*Components are omitted in the seed system and will be documented here once implementation begins.*

## 6. Do's and Don'ts

### Do:
- **Do** design mobile-first, ensuring search and filters are fully usable on small screens while walking.
- **Do** establish visual hierarchy using clear solid borders (1px) and background fills instead of drop shadows.
- **Do** keep typography highly legible with contrast ratios exceeding 4.5:1 for all text.

### Don't:
- **Don't** use generic card grids with large food images that clutter the screen (avoid looking like DoorDash / UberEats).
- **Don't** use dry, unorganized yellow-pages directory lists without clear visual division and interactive cues (avoid looking like Yelp).
- **Don't** use small all-caps uppercase tracked eyebrows above sections, which feel like generic AI scaffolding.
