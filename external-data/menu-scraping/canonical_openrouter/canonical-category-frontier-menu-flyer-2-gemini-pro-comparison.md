# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| ~anthropic/claude-opus-latest | 30 |
| ~google/gemini-pro-latest | 30 |
| ~openai/gpt-latest | 30 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| ~anthropic/claude-opus-latest | beans, papas, rice | - |
| ~google/gemini-pro-latest | beans, papas, rice | - |
| ~openai/gpt-latest | beans, papas, rice | - |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burritos | Daily Specials | ~anthropic/claude-opus-latest, ~google/gemini-pro-latest | ~openai/gpt-latest |
| Ground Beef Burritos | DAILY SPECIALS | ~openai/gpt-latest | ~anthropic/claude-opus-latest, ~google/gemini-pro-latest |
| Family Pack | Family Pack | ~anthropic/claude-opus-latest | ~google/gemini-pro-latest, ~openai/gpt-latest |
| Family Pack | FAMILY PACK $40.00 | ~google/gemini-pro-latest, ~openai/gpt-latest | ~anthropic/claude-opus-latest |

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chips & Guacamole | Extras | appetizer: ~anthropic/claude-opus-latest, ~openai/gpt-latest; side: ~google/gemini-pro-latest |
| Chips & Maria's Queso | Extras | appetizer: ~anthropic/claude-opus-latest, ~openai/gpt-latest; side: ~google/gemini-pro-latest |
| Chips & Salsa | Extras | appetizer: ~anthropic/claude-opus-latest, ~openai/gpt-latest; side: ~google/gemini-pro-latest |
| Maria's Combo | Signature Items | combo: ~anthropic/claude-opus-latest; entree: ~google/gemini-pro-latest, ~openai/gpt-latest |
| Rice Bowl | Signature Items | bowl: ~anthropic/claude-opus-latest, ~openai/gpt-latest; entree: ~google/gemini-pro-latest |
