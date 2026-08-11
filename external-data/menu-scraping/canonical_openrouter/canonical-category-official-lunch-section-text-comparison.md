# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 8 |
| google/gemini-3.1-flash-lite | 9 |
| google/gemma-4-26b-a4b-it | 8 |
| google/gemma-4-31b-it | 9 |
| moonshotai/kimi-k2.5 | 8 |
| nvidia/nemotron-3-super-120b-a12b | 8 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 8 |
| qwen/qwen3.5-flash-02-23 | 8 |
| qwen/qwen3.6-35b-a3b | 8 |
| tencent/hy3-preview | 8 |
| xiaomi/mimo-v2.5 | 9 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| deepseek/deepseek-v4-flash | - | beans, papas, rice |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| google/gemma-4-26b-a4b-it | - | beans, papas, rice |
| google/gemma-4-31b-it | - | beans, papas, rice |
| moonshotai/kimi-k2.5 | - | beans, papas, rice |
| nvidia/nemotron-3-super-120b-a12b | - | beans, papas, rice |
| nvidia/nemotron-3-ultra-550b-a55b:free | - | beans, papas, rice |
| qwen/qwen3.5-flash-02-23 | - | beans, papas, rice |
| qwen/qwen3.6-35b-a3b | - | beans, papas, rice |
| tencent/hy3-preview | - | beans, papas, rice |
| xiaomi/mimo-v2.5 | - | beans, papas, rice |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burritos | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Chimichanga | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Enchiladas | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 | google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Enchiladas Suizas | Lunch | google/gemini-3.1-flash-lite, google/gemma-4-31b-it, xiaomi/mimo-v2.5 | deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Enchiladas/Enchiladas Suizas | Lunch | google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Fish Tacos | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Homemade Tamales | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Street Tacos | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Tostadas | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Traditional Tacos | Lunch | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free |
| Burritos | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Chimichanga | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Enchiladas/Enchiladas Suizas | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Fish Tacos | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Homemade Tamales | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Street Tacos | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Tostadas | Lunch $10 | moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Traditional Tacos | Lunch $10 | moonshotai/kimi-k2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| TraditionalTacos | Lunch $10 | nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5 |

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chimichanga | Lunch | chimichanga: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it, tencent/hy3-preview |
| Enchiladas | Lunch | enchilada: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it |
| Enchiladas Suizas | Lunch | enchilada: google/gemini-3.1-flash-lite, xiaomi/mimo-v2.5; entree: google/gemma-4-31b-it |
| Enchiladas/Enchiladas Suizas | Lunch | enchilada: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23; entree: tencent/hy3-preview |
| Homemade Tamales | Lunch | entree: google/gemma-4-31b-it, tencent/hy3-preview; tamale: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Tostadas | Lunch | entree: google/gemma-4-31b-it, tencent/hy3-preview; tostada: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5 |
| Chimichanga | Lunch $10 | chimichanga: nvidia/nemotron-3-ultra-550b-a55b:free; entree: moonshotai/kimi-k2.5 |
| Enchiladas/Enchiladas Suizas | Lunch $10 | enchilada: nvidia/nemotron-3-ultra-550b-a55b:free; entree: moonshotai/kimi-k2.5 |
| Homemade Tamales | Lunch $10 | entree: moonshotai/kimi-k2.5; tamale: nvidia/nemotron-3-ultra-550b-a55b:free |
| Tostadas | Lunch $10 | entree: moonshotai/kimi-k2.5; tostada: nvidia/nemotron-3-ultra-550b-a55b:free |
