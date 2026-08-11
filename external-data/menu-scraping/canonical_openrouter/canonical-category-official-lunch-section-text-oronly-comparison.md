# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| google/gemini-3.1-flash-lite | 8 |
| google/gemma-4-31b-it | 8 |
| xiaomi/mimo-v2.5 | 8 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| google/gemma-4-31b-it | - | beans, papas, rice |
| xiaomi/mimo-v2.5 | - | beans, papas, rice |

## Missing Or Extra Rows

No coverage differences.

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chimichanga | Lunch | chimichanga: google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it |
| Enchiladas/Enchiladas Suizas | Lunch | enchilada: google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it |
| Homemade Tamales | Lunch | entree: google/gemma-4-31b-it; tamale: google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5 |
| Tostadas | Lunch | entree: google/gemma-4-31b-it; tostada: google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5 |
