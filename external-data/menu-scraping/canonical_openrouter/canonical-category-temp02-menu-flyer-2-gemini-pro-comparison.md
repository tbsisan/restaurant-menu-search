# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 28 |
| google/gemini-3.1-flash-lite | 32 |
| google/gemma-4-26b-a4b-it | 32 |
| google/gemma-4-31b-it | 30 |
| inclusionai/ling-2.6-flash | 30 |
| moonshotai/kimi-k2.5 | 29 |
| nvidia/nemotron-3-ultra-550b-a55b:free | 27 |
| qwen/qwen3.5-flash-02-23 | 27 |
| qwen/qwen3.6-35b-a3b | 27 |
| tencent/hy3-preview | 28 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| deepseek/deepseek-v4-flash | - | beans, papas, rice |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| google/gemma-4-26b-a4b-it | - | beans, papas, rice |
| google/gemma-4-31b-it | beans, papas, rice | - |
| inclusionai/ling-2.6-flash | - | beans, papas, rice |
| moonshotai/kimi-k2.5 | beans, papas, rice | - |
| nvidia/nemotron-3-ultra-550b-a55b:free | - | beans, papas, rice |
| qwen/qwen3.5-flash-02-23 | - | beans, papas, rice |
| qwen/qwen3.6-35b-a3b | - | beans, papas, rice |
| tencent/hy3-preview | - | beans, papas, rice |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Birria Tacos | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash |
| Borracho Burrito | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash |
| Burritos | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash, nvidia/nemotron-3-ultra-550b-a55b:free |
| Chili Cheese Burritos | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash |
| Crispy Corn Ground Beef Tacos | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash |
| Ground Beef Burrito | DAILY SPECIALS | nvidia/nemotron-3-ultra-550b-a55b:free | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Street Tacos | DAILY SPECIALS | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash |
| Beans | EXTRAS | google/gemma-4-31b-it, moonshotai/kimi-k2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Beans, Rice, or Papas | EXTRAS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5 |
| Beans, Rice, OR Papas Large | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Beans, Rice, OR Papas Small | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Guacamole | EXTRAS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | google/gemma-4-26b-a4b-it |
| Chips & Guacamole Large | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Guacamole Small | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Maria's Queso | EXTRAS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | google/gemma-4-26b-a4b-it |
| Chips & Maria's Queso Large | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Maria's Queso Small | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Salsa | EXTRAS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | google/gemma-4-26b-a4b-it |
| Chips & Salsa Large | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Salsa Small | EXTRAS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Papas | EXTRAS | google/gemma-4-31b-it, moonshotai/kimi-k2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Rice | EXTRAS | google/gemma-4-31b-it, moonshotai/kimi-k2.5 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| FAMILY PACK ITEMS | Family Meal | inclusionai/ling-2.6-flash | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Family Pack | FAMILY PACK | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | deepseek/deepseek-v4-flash, inclusionai/ling-2.6-flash |
| Family Pack | FAMILY PACK $40.00 | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Birria Tacos | Friday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Street Tacos | Saturday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Maria's Chili | SIGNATURE ITEMS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview | google/gemma-4-26b-a4b-it, google/gemma-4-31b-it |
| Maria's Chili 🌶️ | SIGNATURE ITEMS | google/gemma-4-31b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Maria's Chili Bowl | SIGNATURE ITEMS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Maria's Chili Cup | SIGNATURE ITEMS | google/gemma-4-26b-a4b-it | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| One Dozen Tamales | SIGNATURE ITEMS | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b | tencent/hy3-preview |
| Tamales | SIGNATURE ITEMS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b |
| Enchilada Suizas | SINGLE ITEMS | deepseek/deepseek-v4-flash, google/gemma-4-31b-it, tencent/hy3-preview | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b |
| Chili Cheese Burritos | Sunday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Borracho Burrito | Thursday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Crispy Corn Ground Beef Tacos | Tuesday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Burritos | Wednesday | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |

## Price Disagreements

| Dish | Original Category | Prices by model |
| --- | --- | --- |
| Beans, Rice, or Papas | EXTRAS | $3.00: deepseek/deepseek-v4-flash, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; $5.00: google/gemini-3.1-flash-lite |
| Chips & Guacamole | EXTRAS | $15.00: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash; $8.00: deepseek/deepseek-v4-flash, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Maria's Queso | EXTRAS | $12.00: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash; $7.00: deepseek/deepseek-v4-flash, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Salsa | EXTRAS | $6.00: deepseek/deepseek-v4-flash, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; $8.00: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |
| Maria's Chili | SIGNATURE ITEMS | $6.00: deepseek/deepseek-v4-flash, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; $8.00: google/gemini-3.1-flash-lite, inclusionai/ling-2.6-flash |

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Birria Tacos | DAILY SPECIALS | other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; taco: tencent/hy3-preview |
| Borracho Burrito | DAILY SPECIALS | burrito: google/gemma-4-26b-a4b-it, tencent/hy3-preview; other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b |
| Burritos | DAILY SPECIALS | burrito: tencent/hy3-preview; other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b |
| Chili Cheese Burritos | DAILY SPECIALS | burrito: tencent/hy3-preview; other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b |
| Crispy Corn Ground Beef Tacos | DAILY SPECIALS | other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; taco: tencent/hy3-preview |
| Street Tacos | DAILY SPECIALS | other: inclusionai/ling-2.6-flash; special: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b; taco: tencent/hy3-preview |
| Chips & Guacamole | EXTRAS | appetizer: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash; side: nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Maria's Queso | EXTRAS | appetizer: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash; side: nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Chips & Salsa | EXTRAS | appetizer: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash; side: nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Half & Half | EXTRAS | other: inclusionai/ling-2.6-flash; side: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Maria's Chili | SIGNATURE ITEMS | appetizer: qwen/qwen3.6-35b-a3b; other: inclusionai/ling-2.6-flash; soup: google/gemini-3.1-flash-lite, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, tencent/hy3-preview; special: deepseek/deepseek-v4-flash |
| Maria's Combo | SIGNATURE ITEMS | combo: deepseek/deepseek-v4-flash, google/gemma-4-26b-a4b-it, inclusionai/ling-2.6-flash, moonshotai/kimi-k2.5, qwen/qwen3.6-35b-a3b; entree: google/gemini-3.1-flash-lite, nvidia/nemotron-3-ultra-550b-a55b:free, tencent/hy3-preview; family meal: google/gemma-4-31b-it, qwen/qwen3.5-flash-02-23 |
| One Dozen Tamales | SIGNATURE ITEMS | entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5; family meal: qwen/qwen3.5-flash-02-23; other: inclusionai/ling-2.6-flash; tamale: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b |
| Burrito | SINGLE ITEMS | burrito: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; other: inclusionai/ling-2.6-flash |
| Chimichanga | SINGLE ITEMS | chimichanga: google/gemma-4-26b-a4b-it, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23; other: inclusionai/ling-2.6-flash |
| Enchilada | SINGLE ITEMS | enchilada: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview; entree: google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash |
| Enchilada Suizas | SINGLE ITEMS | enchilada: deepseek/deepseek-v4-flash, tencent/hy3-preview; entree: google/gemma-4-31b-it |
| Fish Taco | SINGLE ITEMS | other: inclusionai/ling-2.6-flash; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Homemade Tamale | SINGLE ITEMS | entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash; tamale: google/gemma-4-26b-a4b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Street Taco | SINGLE ITEMS | other: inclusionai/ling-2.6-flash; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Tostada | SINGLE ITEMS | entree: deepseek/deepseek-v4-flash, google/gemma-4-31b-it, moonshotai/kimi-k2.5; other: inclusionai/ling-2.6-flash; taco: qwen/qwen3.5-flash-02-23; tostada: google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
| Traditional Taco | SINGLE ITEMS | other: inclusionai/ling-2.6-flash; taco: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, google/gemma-4-26b-a4b-it, google/gemma-4-31b-it, moonshotai/kimi-k2.5, nvidia/nemotron-3-ultra-550b-a55b:free, qwen/qwen3.5-flash-02-23, qwen/qwen3.6-35b-a3b, tencent/hy3-preview |
