# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| google/gemini-3.1-flash-lite | 9 |
| google/gemma-4-31b-it | 9 |
| xiaomi/mimo-v2.5 | 8 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| google/gemma-4-31b-it | - | beans, papas, rice |
| xiaomi/mimo-v2.5 | - | beans, papas, rice |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burritos | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Chimichanga | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Enchiladas | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Enchiladas Suizas | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Fish Tacos | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Homemade Tamales | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Street Tacos | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Tostadas | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Traditional Tacos | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it | xiaomi/mimo-v2.5 |
| Burritos | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Chimichanga | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Enchiladas/Enchiladas Suizas | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Fish Tacos | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Homemade Tamales | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Street Tacos | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Tostadas | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |
| Traditional Tacos | Lunch $10 | xiaomi/mimo-v2.5 | google/gemini-3.1-flash-lite, google/gemma-4-31b-it |

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chimichanga | Lunch | chimichanga: google/gemini-3.1-flash-lite; entree: google/gemma-4-31b-it |
| Enchiladas | Lunch | enchilada: google/gemini-3.1-flash-lite; entree: google/gemma-4-31b-it |
| Enchiladas Suizas | Lunch | enchilada: google/gemini-3.1-flash-lite; entree: google/gemma-4-31b-it |
| Homemade Tamales | Lunch | entree: google/gemma-4-31b-it; tamale: google/gemini-3.1-flash-lite |
| Tostadas | Lunch | entree: google/gemma-4-31b-it; tostada: google/gemini-3.1-flash-lite |
