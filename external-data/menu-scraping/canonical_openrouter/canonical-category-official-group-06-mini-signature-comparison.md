# Canonical Category Menu Output Comparison

Source: `official_site/text/section-groups/06-mini-signature.txt`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 12 |
| google/gemini-3.1-flash-lite | 11 |
| google/gemma-4-26b-a4b-it | 11 |
| google/gemma-4-31b-it | 11 |
| inclusionai/ling-2.6-flash | 8 |
| moonshotai/kimi-k2.5 | 11 |
| nvidia/nemotron-3-super-120b-a12b | 11 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 11 |
| qwen/qwen3.5-flash-02-23 | 11 |
| qwen/qwen3.6-35b-a3b | 11 |
| tencent/hy3-preview | 11 |
| xiaomi/mimo-v2.5 | 11 |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burrito | Burrito | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Enchilada | Enchilada | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Burrito | Mini Marias | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Enchilada | Mini Marias | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Mini Marias | Mini Marias | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias Burrito | Mini Marias | google/gemini-3.1-flash-lite | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias Enchilada | Mini Marias | google/gemini-3.1-flash-lite | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias Quesadilla | Mini Marias | google/gemini-3.1-flash-lite | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias Taco | Mini Marias | google/gemini-3.1-flash-lite | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias Tostada | Mini Marias | google/gemini-3.1-flash-lite | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Quesadilla | Mini Marias | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Taco | Mini Marias | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Tostada | Mini Marias | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Quesadilla | Quesadilla | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Botana | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash |
| Maria's Chili | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash |
| Maria's Combo | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash |
| Nachos | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash |
| One Dozen Tamales | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash, tencent/hy3-preview |
| Rice Bowl | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | inclusionai/ling-2.6-flash |
| Tamales | Signature Items | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Maria's Chili | Special | inclusionai/ling-2.6-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Mini Marias | Special | inclusionai/ling-2.6-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Taco | Taco | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Tostada | Tostada | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |

## Price Disagreements

| Dish | Original Category | Prices by model |
| --- | --- | --- |
| Burrito | Burrito | $3.00: inclusionai/ling-2.6-flash; $6.00: deepseek/deepseek-v4-flash |
| Enchilada | Enchilada | $3.00: inclusionai/ling-2.6-flash; $6.00: deepseek/deepseek-v4-flash |
| Quesadilla | Quesadilla | $3.00: inclusionai/ling-2.6-flash; $6.00: deepseek/deepseek-v4-flash |
| Taco | Taco | $3.00: inclusionai/ling-2.6-flash; $6.00: deepseek/deepseek-v4-flash |
| Tostada | Tostada | $3.00: inclusionai/ling-2.6-flash; $6.00: deepseek/deepseek-v4-flash |

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Burrito | Burrito | alacarte: inclusionai/ling-2.6-flash; burrito: deepseek/deepseek-v4-flash |
| Enchilada | Enchilada | alacarte: inclusionai/ling-2.6-flash; enchilada: deepseek/deepseek-v4-flash |
| Burrito | Mini Marias | burrito: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it |
| Enchilada | Mini Marias | enchilada: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it, moonshotai/kimi-k2.5, tencent/hy3-preview |
| Quesadilla | Mini Marias | entree: google/gemma-4-31b-it, moonshotai/kimi-k2.5, tencent/hy3-preview; quesadilla: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Taco | Mini Marias | entree: google/gemma-4-31b-it; taco: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Tostada | Mini Marias | entree: google/gemma-4-31b-it, moonshotai/kimi-k2.5, tencent/hy3-preview; tostada: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Quesadilla | Quesadilla | alacarte: inclusionai/ling-2.6-flash; quesadilla: deepseek/deepseek-v4-flash |
| Maria's Combo | Signature Items | combo: google/gemma-4-26b-a4b-it, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5; entree: google/gemini-3.1-flash-lite, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23; family meal: deepseek/deepseek-v4-flash, google/gemma-4-31b-it; special: tencent/hy3-preview |
| Nachos | Signature Items | appetizer: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; nachos: nvidia/nemotron-3-ultra-550b-a55b:free, xiaomi/mimo-v2.5 |
| One Dozen Tamales | Signature Items | entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23; tamale: qwen/qwen3.6-35b-a3b; tamales: google/gemma-4-26b-a4b-it, xiaomi/mimo-v2.5 |
| Taco | Taco | alacarte: inclusionai/ling-2.6-flash; taco: deepseek/deepseek-v4-flash |
| Tostada | Tostada | alacarte: inclusionai/ling-2.6-flash; tostada: deepseek/deepseek-v4-flash |

## Sides Number Disagreements

| Dish | Original Category | Sides numbers by model |
| --- | --- | --- |
| Maria's Combo | Signature Items | 0: deepseek/deepseek-v4-flash, google/gemma-4-31b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; 1: moonshotai/kimi-k2.5; 2: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| One Dozen Tamales | Signature Items | 0: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; 1: xiaomi/mimo-v2.5 |

## Side Choices Disagreements

| Dish | Original Category | Side choices by model |
| --- | --- | --- |
| Burrito | Mini Marias | [blank]: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it |
| Enchilada | Mini Marias | [blank]: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it |
| Quesadilla | Mini Marias | [blank]: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it |
| Taco | Mini Marias | [blank]: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it |
| Tostada | Mini Marias | [blank]: google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it |
| Botana | Signature Items | [blank]: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; none: google/gemini-3.1-flash-lite; not specified: google/gemma-4-31b-it |
| Maria's Chili | Signature Items | [blank]: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; none: google/gemini-3.1-flash-lite; not specified: google/gemma-4-31b-it |
| Maria's Combo | Signature Items | [blank]: deepseek/deepseek-v4-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5; not specified: google/gemma-4-31b-it; rice beans: google/gemini-3.1-flash-lite; rice, beans: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, tencent/hy3-preview |
| Nachos | Signature Items | [blank]: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; none: google/gemini-3.1-flash-lite; not specified: google/gemma-4-31b-it |
| One Dozen Tamales | Signature Items | [blank]: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; none: google/gemini-3.1-flash-lite; not specified: google/gemma-4-31b-it; salsa of your choice: xiaomi/mimo-v2.5 |
| Rice Bowl | Signature Items | [blank]: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5; none: google/gemini-3.1-flash-lite; not specified: google/gemma-4-31b-it |
