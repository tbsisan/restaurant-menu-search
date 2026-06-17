# Residential proxy and scraping-as-a-service provider research

_Date researched: 2026-06-16. Prices are vendor-list prices captured from public pricing/product pages via Jina Reader mirrors; verify before purchase because proxy/scraping vendors change promos frequently._

## Executive takeaways for restaurant/menu scraping

- **Cheapest raw residential bandwidth found:** Infatica advertises residential from **$0.30/GB** in its nav, but the detailed residential table captured shows PAYG **$4/GB** and volume down to **$2.60/GB** at 1 TB. Treat the $0.30/GB claim as a high-volume/marketing floor until confirmed in-dashboard.
- **Low-commit raw residential options:** PacketStream is simplest at **$1.00/GB PAYG**; Proxy-Cheap rotating residential advertises **$0.78/GB**; Webshare rotating residential advertises **starting at $1.40/GB**; IPRoyal starts **$1.75/GB**.
- **Midmarket/enterprise proxy networks:** Bright Data, Oxylabs, Decodo, SOAX, NetNut, Rayobyte. These are more expensive at small volume but include better tooling, targeting, compliance posture, and support.
- **Scraping-as-a-service/API may be cheaper operationally** than managing proxies + browser automation if targets are restaurant sites with JS, anti-bot, or rate limits. Good candidates to test first: **Zyte API, ScraperAPI, ScrapingBee, ZenRows, Bright Data Unlocker/API, Decodo Web Scraping API, Oxylabs Web Scraper API**.
|- **Recommendation:** run a small benchmark with 100–500 known target URLs: raw residential via PacketStream/Webshare/IPRoyal vs managed scraping API via Zyte/ScraperAPI/ScrapingBee/ZenRows. Track success rate, HTML completeness, rendered menu capture, block/CAPTCHA rate, and effective cost per successful menu.

## Pricing models explained

Not all providers charge the same way. There are three main models, and many providers mix them across their products.

| Model | What you pay for | Typical for | Predictability |
|---|---|---|---|
| **Per GB (bandwidth)** | Bytes transferred through the proxy (request + response headers + body) | Raw proxy access (you manage the scraper) | Low — depends on page sizes and retries |
| **Per 1K requests** | Per successful HTTP/rendered request to the API | Managed scraping APIs (proxy + JS + retries included) | Medium — depends on request volume |
| **Monthly subscription + included credits** | Fixed monthly fee covers a bucket of GB or requests; overage at discounted rate | Most SaaS scraping APIs and some proxy vendors | High — cost is known up front |

**Key distinctions:**

- **Proxy providers** (PacketStream, IPRoyal, Webshare, Proxy-Cheap, Infatica, SOAX, NetNut, Rayobyte) predominantly charge **per GB** for residential proxies. Some also offer monthly plans with an included GB bucket (e.g. SOAX, NetNut, Rayobyte show monthly commitment tiers). You bring your own scraping stack (requests, Playwright, etc.).
- **Scraping APIs** (Zyte, ScraperAPI, ScrapingBee, ZenRows, Crawlbase, Scrapingdog) predominantly charge **per request or per 1K requests**, and almost always wrap this in a **monthly subscription** that includes a credit bucket. Failed requests are typically not charged. The API handles proxies, JS rendering, CAPTCHAs, and retries for you.
- **Hybrid providers** (Bright Data, Oxylabs, Decodo, NetNut, IPRoyal, Infatica) offer **both**: raw proxies charged per GB, and managed scraping APIs charged per request or per 1K records. This is useful if you want to benchmark both approaches.

**For our restaurant-menu use case:**
- If target sites are simple and static, per-GB residential proxies + our own scraper may be cheapest.
- If target sites need JS rendering, have anti-bot protection, or block datacenter IPs, a managed scraping API (per request) may be cheaper overall because it avoids engineering time and retry logic.
- Monthly subscription plans with included credits are usually the best value if we expect steady volume (e.g. scrape 50K menus/month).

## Raw residential / proxy-network providers

| Provider | Residential pricing captured | Minimum / plan shape | Scraping-related services | Notes |
|---|---:|---|---|---|
| **PacketStream** | **$1.00/GB** metered residential | PAYG; no long-term commitment stated | Reseller API | Very simple cheap baseline. Captured pricing page says residential access at $1.00/GB and reseller rates starting $1.00/GB. |
| **Proxy-Cheap** | Rotating residential **$0.78/GB** promo; page says min top-up 1 GB and max 50 GB/mo | Also static residential from ~$2.12/mo; rotating mobile $5.99/GB | Proxy only | Very low-cost; quality/compliance should be tested carefully before relying on it. |
| **Webshare** | Rotating residential **starting at $1.40/GB**; static residential from **$0.23/IP**; private static residential **$0.53/IP**, dedicated static **$1.47/IP** | Free proxy list up to 1GB/mo; many static proxy tiers | Proxy only | Good cheap self-serve proxy vendor; pricing page also shows datacenter proxy tiers from free / $0.0299 per proxy/mo. |
| **IPRoyal** | Residential **from $1.75/GB**; ISP **from $1.80/proxy**; datacenter **from $1.39/proxy**; mobile **from $117/mo** | PAYG-ish / product-specific | Web Unblocker **from $1.00/1,000 requests**; Video Scraper API | Affordable self-serve option with unblocking API. |
| **Infatica** | Detailed residential table: PAYG **$4/GB**, 25GB **$3.84/GB**, 100GB **$3.60/GB**, 241GB **$2.90/GB**, 500GB **$2.70/GB**, 1TB **$2.60/GB**. Nav advertises residential IPs **from $0.30/GB**. | $4 7-day trial captured | Web Scraper, SERP Web Scraper, custom scraping-as-a-service, YouTube Data API, AI Search Data API | Source has a discrepancy between headline/nav and detailed plan table; verify in account/sales. |
| **Decodo / Smartproxy** | Residential headline **from $2/GB**. Visible monthly tiers: 3GB **$3.75/GB**, 10GB **$3.50/GB**, 25GB **$3.25/GB**, 50GB **$3.00/GB**. Static residential **from $0.27/IP**, mobile **from $2.25/GB**, datacenter **from $0.02/IP**. | Monthly plans; free trial CTAs | Site Unblocker **from $0.95/1K requests**; Web Scraping API **from $0.09/1K requests** | Strong balance of price + tooling; likely worth testing. |
| **Bright Data** | Residential promo **$2.50/GB** (marked 50% off from $5); datacenter **from $0.90/IP**; ISP **from $1.30/IP** | Enterprise-oriented, free trials/free tiers on APIs | Unlocker API **from $1/1K req**, Crawl API **from $1/1K req**, SERP API **from $1/1K req**, Browser API **from $5/GB**, Scraper APIs **from $0.75/1K records**, managed acquisition **from $1,500/mo** | Broadest product suite and likely best compliance/support; not usually cheapest. |
| **Oxylabs** | Residential **from $2.50/GB**; mobile **from $3.50/GB**; ISP **from $1.20/IP**; dedicated ISP **from $2.50/IP** | Enterprise/midmarket | Web Scraper API **from $0.25/1K results**; Headless Browser **from $4.70/GB**; Web Unblocker promo **$3/GB** (shown as $5 → $3/GB, 40% off) | Strong enterprise provider; good candidate if reliability matters more than unit cost. |
| **SOAX** | Unified credits across residential/mobile/ISP/datacenter + Web Data API: Starter 25GB **$3.60/GB** ($90/mo), Advanced 50GB **$3.40/GB** ($170/mo), Professional 300GB **$2.46/GB** ($740/mo), Business 800GB **$2.00/GB** ($1,600/mo), Enterprise from **$0.32/GB** | Monthly subscription; $1.99 3-day 400MB trial noted | Web Data API included in credit model | Useful unified plan if experimenting across proxy types. |
| **NetNut** | Residential monthly tiers captured: Starter **$99/mo at $3.53/GB**, Advanced **$249/mo at $3.45/GB**, Production **$499/mo at $3.32/GB**, Semi-Pro **$999/mo at $2.85/GB**, Professional **$1,999/mo at $2.49/GB**, Master **$3,750/mo at $1.87/GB**. Annual discounted to as low as **$1.59/GB**. | Monthly/annual; request-based and bandwidth models appear on page | Website Unblocker **$1.50 → $0.83/1K results** by monthly tier; SERP Scraper **$0.75 → $0.41/1K requests** monthly, lower annual | More enterprise-ish minimums than cheap PAYG providers. |
| **Rayobyte** | Rotating residential visible tiers include **$3.50/GB**, **$2/GB**, **$1.50/GB**, **$0.70/GB**, “as low as **$0.50/GB**”. Static residential/IP and mobile/datacenter tiers also present. | Plans by GB/month; exact tier names hard to parse from page capture | Web Scraping API displayed **$0.0018/scrape**, as low as **$0.00004/scrape** depending on website | Established proxy vendor; page capture is noisy, verify exact tiers. |

## Scraping-as-a-service / managed scraping API providers

| Provider | Pricing captured | Included model / notes | Best fit |
|---|---:|---|---|
| **Zyte API** | PAYG HTTP response **$0.13–$1.27 per 1K requests**; browser-rendered **$1.01–$16.08 per 1K**. With monthly commitments: $100/mo lowers HTTP to **$0.10–$0.95/1K**, $200/mo to **$0.08–$0.76/1K**, $500/mo to **$0.06–$0.61/1K**; rendered at $500/mo **$0.48–$7.68/1K**. $5 free credit. | Automated API includes datacenter, residential, rendering as needed; charges by website difficulty tier and only successful responses. | Strong candidate for menu scraping because it optimizes proxy/rendering automatically and avoids hand-tuning. |
| **ScraperAPI** | Trial: 5,000 API credits. Hobby **$49/mo for 100K credits**, Startup **$149/mo for 1M**, Business **$299/mo for 3M**, Scaling **$475/mo for 5M**, Professional **$975/mo for 10.5M**, Advanced **$1,975/mo for 21.5M**, Enterprise custom. | Includes JS rendering, premium proxies, JSON auto parsing, rotating pools, CAPTCHA/anti-bot detection, retries, unlimited bandwidth. Credits consumed vary by domain/features. | Easy all-in-one scraper API; useful benchmark. |
| **ScrapingBee** | 1,000 free credits. Freelance **$49/mo for 250K credits**, Startup **$99/mo for 1M**, Business **$249/mo for 3M**, Business+ **$599/mo for 8M**, custom. | Handles headless browsers and rotates proxies; plan rows include concurrency (50/100/200/400) and support options. | Developer-friendly API with browser rendering; good for small/medium experiments. |
| **ZenRows** | Free 14-day trial: 1,000 basic results, 40 protected results, 100MB browser. Developer **$69/mo** includes 250K basic / 10K protected results and 12.73GB scraping-browser/residential-proxy resource; higher plans visible at **$129**, **$299**, **$499**, **$999**, **$1,999**, **$2,999/mo**. | Universal Scraper API, Scraping Browser, residential proxies, AI Web Unblocker, auto retries. | Good if targets need anti-bot handling and rendered pages. |
| **Crawlbase** | Crawling API tiered per 1K requests: normal starts **$3.00/1K** for first 1K, falls to **$0.02/1K** after 1B; JS tiers start **$4.50/1K**; another tier starts **$6.00/1K**. Also Crawler subscriptions: **$29/mo for 10K requests**, **$249/mo for 1M**, enterprise/custom. First 1,000 requests free; Smart Proxy page offers 5,000 free credits. | Mixed datacenter/residential proxy in some plans; JS requests use more credits. | Useful for large crawling pipelines; compare pricing carefully by product. |
| **Apify** | Platform plans: Free $5/mo included usage, Starter **$29/mo**, Scale **$199/mo**, Business **$999/mo**. Residential proxies **$8/GB** on Free/Starter, **$7.50/GB** Scale, **$7/GB** Business. Datacenter proxies included then **$1/IP**, **$0.80/IP**, **$0.60/IP** by plan. Compute **$0.20/CU** down to **$0.13/CU**. | Marketplace of Actors, browser automation platform, storage/proxy charges. | Best when you want hosted crawlers/actors, not just proxy traffic. Residential bandwidth is pricier. |
| **Bright Data Scraper APIs / Unlocker / Browser** | Scraper APIs **from $0.75/1K records**, Unlocker/Crawl/SERP **from $1/1K requests**, Browser API **from $5/GB**, managed data acquisition **from $1,500/mo**. | Pre-built scrapers, scraping browser, unlocker, managed service. | Enterprise-grade managed data acquisition; likely expensive but reliable. |
| **Oxylabs Web Scraper API / Web Unblocker** | Web Scraper API **from $0.25/1K results**; Web Unblocker promo **$3/GB**; Headless Browser **$4.70/GB**. | Anti-blocking/unblocking and scraping APIs. | Enterprise alternative to Bright Data. |
| **Decodo Web Scraping API / Site Unblocker** | Web Scraping API **from $0.09/1K requests**; Site Unblocker **from $0.95/1K requests**. | Configure features per request and pay in credits based on complexity. | Potentially very cost-effective API option to benchmark. |
| **NetNut Website Unblocker / SERP Scraper** | Website Unblocker monthly: **$99/mo at $1.50/1K results** to **$3,750/mo at $0.83/1K**; annual as low as **$0.70/1K**. SERP Scraper monthly: **$99/mo at $0.75/1K requests** to **$3,750/mo at $0.41/1K**; annual as low as **$0.35/1K**. | Only successful requests charged on SERP page. | Worth considering if SERP/AI-data use cases appear; higher monthly commitments. |
| **Rayobyte Web Scraping API** | **$0.0018/scrape** displayed; as low as **$0.00004/scrape** depending on website. | Hybrid scraping/unblocker product. | Needs direct quote/benchmark because price depends heavily on site. |
| **IPRoyal Web Unblocker** | **from $1.00/1,000 requests** | AI-driven unblocking manages locations, rotation, fingerprints. | Cheap-ish unblocking API to test. |
| **Infatica custom scraping / Web Scraper / SERP Web Scraper** | Pricing page captured product availability and “free trial period,” but not detailed scraper API prices in the captured lines. | Custom scraping-as-a-service and domain-specific APIs (Amazon/eBay/LinkedIn/etc.). | Contact or account quote needed. |
| **Scrapingdog** | Free 200 credits; Lite **$40/mo for 200K credits**, Standard **$90/mo for 1M**, Pro **$200/mo for 3M**, then many tiers to **$30K/mo for 1.1B credits**. Rotating proxy costs 1 credit/request; JS 5 credits/request; premium/geo 10 credits/request; JS+premium 25 credits/request. | Every plan unlocks every API; failed requests never charged. | Low entry price; good to test if API quality is adequate. |
| **Nimble** | Pricing page captured per-1K-ish line items: Web Search Agents **$3**, Search **$1.50**, Answer **$4**, Extract drivers: Standard **$0.90**, Render JS **$1.30**, Render JS + Stealth **$1.45**; managed agents add 10%. | Enterprise/data-agent positioning; volume discounts and custom high-scale terms. | Better for search/extract/agent workflows than raw restaurant-site crawling; confirm units with sales/docs. |

## Shortlist to benchmark first

1. **Zyte API** — likely best “less engineering” option for arbitrary restaurant sites because it auto-selects unblocking/rendering and charges successful responses.
2. **ScraperAPI or ScrapingBee** — simple APIs with generous credits at $49–$99 entry tiers.
3. **Decodo Web Scraping API** — compelling advertised floor ($0.09/1K req) if quality is good.
4. **PacketStream + our own Playwright/browser stack** — cheapest raw residential baseline ($1/GB) but more engineering/maintenance.
5. **Webshare/IPRoyal/Proxy-Cheap raw residential** — cheap self-serve alternatives; benchmark quality before scaling.
6. **Bright Data/Oxylabs** — keep as “pay more for reliability/support/compliance” options if smaller providers fail.

## Benchmark design for our project

Use a fixed corpus of URLs from the menu-search target set:

- 100 static/simple restaurant pages
- 100 JS-rendered menu/provider pages
- 50 sites known to block datacenter IPs or return bot challenges
- 50 pages where the desired output is a PDF/image/menu embed

For each provider/product, record:

- request count and actual provider billable units
- success rate: HTTP 200 + complete menu content present
- need for JS rendering
- CAPTCHA/block/403/429 rate
- median/95p latency
- extracted menu text quality
- cost per successful complete menu
- operational complexity: simple HTTP API vs needing Playwright/proxy rotation/retry logic

## Source files saved

Raw page captures are saved under:

`/home/tbsisan/Projects/restaurant-menu-search/external-data/raw-untracked/proxy-pricing-sources/`

Key captured source URLs:

- Bright Data pricing: https://brightdata.com/pricing
- Oxylabs pricing: https://oxylabs.io/pricing
- Decodo pricing: https://decodo.com/pricing
- NetNut residential/unblocker/SERP pages: https://netnut.io/residential-proxies/ , https://netnut.io/unblocker/ , https://netnut.io/serp-scraper-api/
- IPRoyal pricing: https://iproyal.com/pricing/
- SOAX pricing: https://soax.com/pricing
- Webshare pricing: https://www.webshare.io/pricing
- Rayobyte pricing: https://rayobyte.com/proxy/pricing/
- PacketStream pricing: https://packetstream.io/pricing/
- Infatica pricing: https://infatica.io/pricing/
- Proxy-Cheap pricing: https://proxy-cheap.com/pricing/
- Nimble pricing: https://www.nimbleway.com/pricing
- ScrapingBee pricing: https://www.scrapingbee.com/pricing/
- ScraperAPI pricing: https://www.scraperapi.com/pricing/
- Zyte pricing: https://www.zyte.com/pricing/
- Apify pricing: https://apify.com/pricing
- ZenRows pricing: https://www.zenrows.com/pricing
- Crawlbase pricing: https://crawlbase.com/pricing
- Scrapingdog pricing: https://www.scrapingdog.com/pricing

## Caveats

- Many vendors display promotional “starts at” floors that may require high volume, annual commitment, or sales negotiation.
- Raw proxy bandwidth is not comparable to scraping API requests; effective cost should be measured as **cost per successful useful extraction**.
- Residential proxy sourcing/compliance varies materially. For production use, review each provider’s acceptable-use policy, KYC requirements, and sourcing claims.
- Some captured pages were noisy or partially duplicated due to dynamic pricing widgets; for shortlisted providers, confirm the plan in their dashboard or with sales before committing.
