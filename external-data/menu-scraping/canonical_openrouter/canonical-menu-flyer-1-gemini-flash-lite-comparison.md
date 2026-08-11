# Canonical Menu Output Comparison

Source OCR: `menu-flyer-1-google__gemini-3.1-flash-lite.md`

## Summary

| Model | Parsed rows | Unsupported side rows | Invalid/missing prices |
| --- | --- | --- | --- |
| deepseek/deepseek-v4-flash | 24 | - | - |
| google/gemini-3.1-flash-lite | 24 | - | - |
| nvidia/nemotron-3-ultra-550b-a55b:free | 29 | Refried Beans, Papas, Spanish Rice, Cilantro Lime Rice, Charro Beans | Refried Beans, Papas, Spanish Rice, Cilantro Lime Rice, Charro Beans |
| qwen/qwen3.5-flash-02-23 | 24 | - | - |
| z-ai/glm-4.7-flash | 29 | Refried Beans, Papas, Spanish Rice, Cilantro Lime Rice, Charro Beans | Fajitas, Refried Beans, Papas, Spanish Rice, Cilantro Lime Rice, Charro Beans |

## Missing Or Extra Rows

| Dish | Category | Present in | Missing from |
| --- | --- | --- | --- |
| Charro Beans | Sides | nvidia/nemotron-3-ultra-550b-a55b:free, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Cilantro Lime Rice | Sides | nvidia/nemotron-3-ultra-550b-a55b:free, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Papas | Sides | nvidia/nemotron-3-ultra-550b-a55b:free, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Refried Beans | Sides | nvidia/nemotron-3-ultra-550b-a55b:free, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Spanish Rice | Sides | nvidia/nemotron-3-ultra-550b-a55b:free, z-ai/glm-4.7-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |

## Price Disagreements

| Dish | Category | Prices by model |
| --- | --- | --- |
| Fajitas | Dinner | : z-ai/glm-4.7-flash; $13.00: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23 |
| Charro Beans | Sides | : z-ai/glm-4.7-flash; $0.00: nvidia/nemotron-3-ultra-550b-a55b:free |
| Cilantro Lime Rice | Sides | : z-ai/glm-4.7-flash; $0.00: nvidia/nemotron-3-ultra-550b-a55b:free |
| Papas | Sides | : z-ai/glm-4.7-flash; $0.00: nvidia/nemotron-3-ultra-550b-a55b:free |
| Refried Beans | Sides | : z-ai/glm-4.7-flash; $0.00: nvidia/nemotron-3-ultra-550b-a55b:free |
| Spanish Rice | Sides | : z-ai/glm-4.7-flash; $0.00: nvidia/nemotron-3-ultra-550b-a55b:free |

## Naming Differences

| Category | Names by model |
| --- | --- |
| Dinner | Enchiladas: deepseek/deepseek-v4-flash; Enchiladas/Enchiladas Suizas: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, z-ai/glm-4.7-flash |
| Lunch | Enchiladas: deepseek/deepseek-v4-flash; Enchiladas/Enchiladas Suizas: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, z-ai/glm-4.7-flash |
