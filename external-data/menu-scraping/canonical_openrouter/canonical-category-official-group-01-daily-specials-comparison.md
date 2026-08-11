# Canonical Category Menu Output Comparison

Source: `official_site/text/section-groups/01-daily-specials.txt`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 6 |
| google/gemini-3.1-flash-lite | 6 |
| google/gemma-4-26b-a4b-it | 6 |
| google/gemma-4-31b-it | 6 |
| inclusionai/ling-2.6-flash | 6 |
| moonshotai/kimi-k2.5 | 6 |
| nvidia/nemotron-3-super-120b-a12b | 6 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 6 |
| qwen/qwen3.5-flash-02-23 | 6 |
| qwen/qwen3.6-35b-a3b | 6 |
| tencent/hy3-preview | 6 |
| xiaomi/mimo-v2.5 | 6 |
| z-ai/glm-4.7-flash | 6 |

## Missing Or Extra Rows

No coverage differences.

## Price Disagreements

No price disagreements.

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Birria Tacos | Friday | special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; taco: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview |
| Street Tacos | Saturday | special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; taco: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview |
| Chili Cheese Burritos | Sunday | burrito: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview; special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Borracho Burrito | Thursday | burrito: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview; special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Crispy Corn Ground Beef Tacos | Tuesday | special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; taco: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview |
| Two Dollar Burritos | Wednesday | burrito: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, tencent/hy3-preview; special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |

## Sides Number Disagreements

| Dish | Original Category | Sides numbers by model |
| --- | --- | --- |
| Birria Tacos | Friday | 0: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, qwen/qwen3.6-35b-a3b, z-ai/glm-4.7-flash; 1: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-super-120b-a12b, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Borracho Burrito | Thursday | 0: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, z-ai/glm-4.7-flash; 1: nvidia/nemotron-3-ultra-550b-a55b:free, xiaomi/mimo-v2.5 |

## Side Choices Disagreements

| Dish | Original Category | Side choices by model |
| --- | --- | --- |
| Birria Tacos | Friday | [blank]: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.6-35b-a3b, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; consomm: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Borracho Burrito | Thursday | [blank]: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-super-120b-a12b, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; sour cream: nvidia/nemotron-3-ultra-550b-a55b:free |
