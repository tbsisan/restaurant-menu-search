# Workshop Log: Restaurant Menu Search

This file is append-only. Persona pass outputs go here before insights are promoted into canonical files.

---

## 2026-06-09T16:20:04Z — raw_concept_intake — script/intake_idea.py

### Goal
Create initial incubator files from a raw concept.

### Inputs considered
- Raw concept text provided at intake.

### Raw concept

```markdown
Users search for specific dishes across nearby restaurant menus, search results show all matching dishes at nearby restaurants, filterable by ingredient inclusion/exclusion, the user clicks to order one of the results, then an AI phone agent places pickup orders at normal in-store prices.
```

### Recommended next action
Run `run_idea_intake_pass` to extract a stronger structured interpretation, or `run_brainstorm_pass` if the concept is already clear enough to expand.


---

## 2026-06-09T15:35:40Z — idea_intake — intake_editor

### Goal
Populate initial incubator files from the raw concept.

### Key intake interpretation
- This is a dish-level local menu search product with an ordering layer: users search for a specific food across nearby restaurant menus, choose a result, and an AI phone agent places a pickup order at normal in-store prices.
- The spark is the craving-first flow: the user starts with "I want this dish" rather than "I want this restaurant."
- The non-obvious edge is combining menu search with AI phone ordering to reach restaurants and prices that may not be exposed through delivery-app marketplaces.

### Educated guesses made
- Likely: first users are people with specific cravings, food explorers, and price-sensitive pickup customers.
- Tentative: restaurants may benefit from incremental pickup demand without joining another marketplace, but this is not validated.
- Tentative: a neighborhood-scale pilot with human-in-the-loop ordering is the sharpest MVP because it tests data accuracy, demand, and ordering reliability without requiring full automation.
- Tentative: the strategic asset could become a dish-level local menu index plus ordering workflow, but defensibility is currently uncertain.

### Unknowns preserved
- Whether users search by dish frequently enough to support repeat use.
- How menu data will be sourced, normalized, and kept fresh.
- Whether restaurants will tolerate AI phone agents placing orders.
- How payments, order changes, unavailable dishes, and price mismatches will be handled.
- What business model works if the product promises normal in-store prices.

### Recommended next action
run_critique_pass. The idea is clear enough to stress-test, and the main risk is not lack of imagination but operational fragility: menu freshness, AI phone-call reliability, restaurant acceptance, payments, price accuracy, and distribution all need a hard critique before expanding the concept.
