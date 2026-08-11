# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 29 |
| google/gemini-3.1-flash-lite | 29 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 29 |
| qwen/qwen3.5-flash-02-23 | 29 |
| tencent/hy3-preview | 29 |
| xiaomi/mimo-v2.5 | 29 |
| z-ai/glm-4.7-flash | 36 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| deepseek/deepseek-v4-flash | beans, papas, rice | - |
| google/gemini-3.1-flash-lite | beans, papas, rice | - |
| nvidia/nemotron-3-ultra-550b-a55b:free | beans, papas, rice | - |
| qwen/qwen3.5-flash-02-23 | beans, papas, rice | - |
| tencent/hy3-preview | beans, papas, rice | - |
| xiaomi/mimo-v2.5 | beans, papas, rice | - |
| z-ai/glm-4.7-flash | beans, papas, rice | - |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burrito | DAILY SPECIALS | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Burritos | DAILY SPECIALS | google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, nvidia/nemotron-3-ultra-550b-a55b:free |
| Ground Beef Burrito | DAILY SPECIALS | nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash |
| Maria's Chili | SIGNATURE ITEMS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 | z-ai/glm-4.7-flash |
| Maria's Chili 🌶️ Bowl | SIGNATURE ITEMS | z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Maria's Chili 🌶️ Cup | SIGNATURE ITEMS | z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |

## Price Disagreements

| Dish | Original Category | Prices by model |
| --- | --- | --- |
| Beans | EXTRAS | $3.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5; $5.00: z-ai/glm-4.7-flash |
| Chips & Guacamole | EXTRAS | $15.00: z-ai/glm-4.7-flash; $8.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Chips & Maria's Queso | EXTRAS | $12.00: z-ai/glm-4.7-flash; $7.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Chips & Salsa | EXTRAS | $6.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5; $8.00: z-ai/glm-4.7-flash |
| Papas | EXTRAS | $3.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5; $5.00: z-ai/glm-4.7-flash |
| Rice | EXTRAS | $3.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5; $5.00: z-ai/glm-4.7-flash |

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chips & Guacamole | EXTRAS | addon: xiaomi/mimo-v2.5; appetizer: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free; side: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, z-ai/glm-4.7-flash |
| Chips & Maria's Queso | EXTRAS | addon: xiaomi/mimo-v2.5; appetizer: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free; side: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, z-ai/glm-4.7-flash |
| Chips & Salsa | EXTRAS | addon: xiaomi/mimo-v2.5; appetizer: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free; side: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, z-ai/glm-4.7-flash |
| Maria's Chili | SIGNATURE ITEMS | appetizer: google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, xiaomi/mimo-v2.5; entree: deepseek/deepseek-v4-flash, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview |
| Maria's Combo | SIGNATURE ITEMS | combo: deepseek/deepseek-v4-flash, z-ai/glm-4.7-flash; entree: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview, xiaomi/mimo-v2.5; family meal: qwen/qwen3.5-flash-02-23 |
| One Dozen Tamales | SIGNATURE ITEMS | entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview, xiaomi/mimo-v2.5, z-ai/glm-4.7-flash; family meal: qwen/qwen3.5-flash-02-23 |
| Chimichanga | SINGLE ITEMS | chimichanga: deepseek/deepseek-v4-flash, z-ai/glm-4.7-flash; entree: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Enchilada/Enchilada Suizas | SINGLE ITEMS | enchilada: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, z-ai/glm-4.7-flash; entree: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview, xiaomi/mimo-v2.5 |
| Homemade Tamale | SINGLE ITEMS | entree: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview, xiaomi/mimo-v2.5; tamale: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, z-ai/glm-4.7-flash |
| Tostada | SINGLE ITEMS | entree: tencent/hy3-preview, xiaomi/mimo-v2.5; taco: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23; tostada: deepseek/deepseek-v4-flash, z-ai/glm-4.7-flash |
