# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 8 |
| google/gemini-3.1-flash-lite | 9 |
| google/gemma-4-26b-a4b-it | 9 |
| google/gemma-4-31b-it | 9 |
| inclusionai/ling-2.6-flash | 2 |
| moonshotai/kimi-k2.5 | 8 |
| nvidia/nemotron-3-super-120b-a12b | 8 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 8 |
| qwen/qwen3.5-flash-02-23 | 8 |
| qwen/qwen3.6-35b-a3b | 8 |
| tencent/hy3-preview | 8 |
| xiaomi/mimo-v2.5 | 8 |
| z-ai/glm-4.7-flash | 8 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| deepseek/deepseek-v4-flash | - | beans, papas, rice |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| google/gemma-4-26b-a4b-it | - | beans, papas, rice |
| google/gemma-4-31b-it | - | beans, papas, rice |
| inclusionai/ling-2.6-flash | - | beans, papas, rice |
| moonshotai/kimi-k2.5 | - | beans, papas, rice |
| nvidia/nemotron-3-super-120b-a12b | - | beans, papas, rice |
| nvidia/nemotron-3-ultra-550b-a55b:free | - | beans, papas, rice |
| qwen/qwen3.5-flash-02-23 | - | beans, papas, rice |
| qwen/qwen3.6-35b-a3b | - | beans, papas, rice |
| tencent/hy3-preview | - | beans, papas, rice |
| xiaomi/mimo-v2.5 | - | beans, papas, rice |
| z-ai/glm-4.7-flash | - | beans, papas, rice |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burritos | Lunch $10 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | inclusionai/ling-2.6-flash |
| Chimichanga | Lunch $10 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | inclusionai/ling-2.6-flash |
| Enchiladas | Lunch $10 | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Enchiladas Suizas | Lunch $10 | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Enchiladas/Enchiladas Suizas | Lunch $10 | deepseek/deepseek-v4-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash |
| Fish Tacos | Lunch $10 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | inclusionai/ling-2.6-flash |
| Homemade Tamales | Lunch $10 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | inclusionai/ling-2.6-flash |
| Tostadas | Lunch $10 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | inclusionai/ling-2.6-flash |

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Burritos | Lunch $10 | burrito: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; entree: nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b |
| Chimichanga | Lunch $10 | chimichanga: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; entree: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b |
| Enchiladas | Lunch $10 | enchilada: google/gemini-3.1-flash-lite; entree: google/gemma-4-26b-a4b-it, google/gemma-4-31b-it |
| Enchiladas Suizas | Lunch $10 | enchilada: google/gemini-3.1-flash-lite; entree: google/gemma-4-26b-a4b-it, google/gemma-4-31b-it |
| Enchiladas/Enchiladas Suizas | Lunch $10 | enchilada: deepseek/deepseek-v4-flash, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; entree: moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b |
| Fish Tacos | Lunch $10 | entree: nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Homemade Tamales | Lunch $10 | entree: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b; tamale: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Street Tacos | Lunch $10 | entree: inclusionai/ling-2.6-flash, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Tostadas | Lunch $10 | entree: google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b; tostada: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Traditional Tacos | Lunch $10 | entree: inclusionai/ling-2.6-flash, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
