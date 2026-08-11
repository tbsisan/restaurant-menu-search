# Canonical Category Menu Output Comparison

Source OCR: `menu-flyer-2-google__gemini-3.1-pro-preview.md`

## Summary

| Model | Parsed rows |
| --- | --- |
| deepseek/deepseek-v4-flash | 27 |
| google/gemini-3.1-flash-lite | 32 |
| qwen/qwen3.5-flash-02-23 | 27 |
| tencent/hy3-preview | 30 |

## Beans/Rice/Papas Split Check

| Model | Split rows present | Missing split rows |
| --- | --- | --- |
| deepseek/deepseek-v4-flash | - | beans, papas, rice |
| google/gemini-3.1-flash-lite | - | beans, papas, rice |
| qwen/qwen3.5-flash-02-23 | - | beans, papas, rice |
| tencent/hy3-preview | beans, papas, rice | - |

## Missing Or Extra Rows

| Dish | Original Category | Present in | Missing from |
| --- | --- | --- | --- |
| Burrito | Daily Specials | deepseek/deepseek-v4-flash | google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Burritos | DAILY SPECIALS | google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 | deepseek/deepseek-v4-flash, tencent/hy3-preview |
| Ground Beef Burrito | DAILY SPECIALS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Beans | EXTRAS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Beans, Rice, OR Papas | Extras | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 | tencent/hy3-preview |
| Papas | EXTRAS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Rice | EXTRAS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |
| Maria's Chili | Signature Items | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, tencent/hy3-preview | qwen/qwen3.5-flash-02-23 |
| Maria's Chili 🌶️ | SIGNATURE ITEMS | qwen/qwen3.5-flash-02-23 | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, tencent/hy3-preview |
| Enchilada Suizas | SINGLE ITEMS | tencent/hy3-preview | deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23 |

## Price Disagreements

| Dish | Original Category | Prices by model |
| --- | --- | --- |
| Beans, Rice, OR Papas | Extras | $3.00: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23; $5.00: google/gemini-3.1-flash-lite |
| Chips & Guacamole | Extras | $15.00: google/gemini-3.1-flash-lite; $8.00: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Chips & Maria's Queso | Extras | $12.00: google/gemini-3.1-flash-lite; $7.00: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Chips & Salsa | Extras | $6.00: deepseek/deepseek-v4-flash, qwen/qwen3.5-flash-02-23, tencent/hy3-preview; $8.00: google/gemini-3.1-flash-lite |
| Maria's Chili | Signature Items | $6.00: deepseek/deepseek-v4-flash, tencent/hy3-preview; $8.00: google/gemini-3.1-flash-lite |

## Canonical Category Disagreements

| Dish | Original Category | Canonical categories by model |
| --- | --- | --- |
| Chips & Guacamole | Extras | addon: deepseek/deepseek-v4-flash, tencent/hy3-preview; appetizer: google/gemini-3.1-flash-lite; side: qwen/qwen3.5-flash-02-23 |
| Chips & Maria's Queso | Extras | addon: deepseek/deepseek-v4-flash, tencent/hy3-preview; appetizer: google/gemini-3.1-flash-lite; side: qwen/qwen3.5-flash-02-23 |
| Chips & Salsa | Extras | addon: deepseek/deepseek-v4-flash, tencent/hy3-preview; appetizer: google/gemini-3.1-flash-lite; side: qwen/qwen3.5-flash-02-23 |
| Maria's Combo | Signature Items | combo: qwen/qwen3.5-flash-02-23; entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite, tencent/hy3-preview |
| One Dozen Tamales | Signature Items | entree: deepseek/deepseek-v4-flash, google/gemini-3.1-flash-lite; tamale: qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Chimichanga | Single Items | alacarte: deepseek/deepseek-v4-flash; chimichanga: qwen/qwen3.5-flash-02-23, tencent/hy3-preview; entree: google/gemini-3.1-flash-lite |
| Enchilada/Enchilada Suizas | Single Items | alacarte: deepseek/deepseek-v4-flash; enchilada: google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Homemade Tamale | Single Items | alacarte: deepseek/deepseek-v4-flash; entree: google/gemini-3.1-flash-lite; tamale: qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
| Tostada | Single Items | alacarte: deepseek/deepseek-v4-flash; tostada: google/gemini-3.1-flash-lite, qwen/qwen3.5-flash-02-23, tencent/hy3-preview |
