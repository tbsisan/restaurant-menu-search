# Idea: Restaurant Menu Search

## Core

### Mission
Likely: Make it easier for people to find and buy the exact dish they are craving from nearby restaurants without being forced through fragmented restaurant websites, delivery-app markups, or generic cuisine search.

### One-liner
A dish-level local menu search engine where users search for specific foods nearby, choose a matching restaurant result, and have an AI phone agent place a pickup order at normal in-store prices.

### What value does this create?
Likely: The product removes the friction of hunting across many restaurant menus when the user wants a specific dish, not just a cuisine or restaurant.

Likely: It could help users avoid delivery-app price inflation by placing pickup orders through normal restaurant ordering channels.

Likely: we can literally have every restaurant that has a menu (more than doordash!), and there could be ways to even get ones that don't. (Offer a bonus for one of our users to photograph a menu.)

Tentative: We can be better about restaurant specials if we scrape frequently enough.

Tentative: Reduces "pickup surprises" (out of an item) because it can be handled over the phone.

Tentative: It creates value for restaurants by not taking a percentage cut (restaurants might love us!).

### Target user
Likely first users:
- People who know the specific dish they want and are flexible about which nearby restaurant makes it
- Price-sensitive users who want pickup rather than delivery-app markups
- Picky eaters looking for a particular item, ingredient, or preparation across nearby menus
- Early on: Local users supporting a local entrepreneur (local subreddits and facebook groups.
- Techy People that like a more powerful search interface
- People with phone phobia, hearing or speaking difficulties
- People that think it's unfair that the other apps take such a huge cut from the restaurant
- Early adopter types

### Proposed solution
A local search interface indexes nearby restaurant menus at the dish level. The user enters a dish query, sees matching menu items from nearby restaurants, selects one, and triggers an AI phone agent that calls the restaurant to place a pickup order at the restaurant's normal in-store price.

### Business model hypothesis
Tentative: 
- Freemium model: 3 free orders a month, then require subscription
- Restaurants can pay to promote their dishes to the top, or users can (boost your fave restaurant!)
- Small upcharge (doesn't make sense unless we're doing ~1000 orders a month). Note: removes our "same price as the restaurant" marketing angle
- Users can tip us
- Delivery upcharge
- App costs $5 (one time)

Likely near-term reality: The business model should probably stay secondary to proving the core loop first: users actually want dish-level search, menu data can stay accurate enough, and the ordering flow is reliable enough to trust.

Open issue: If the main user value is avoiding delivery-app markup, the revenue model must avoid recreating the same economic downside that makes users want to bypass those apps in the first place.

### Potential moat / defensibility
Likely early moat: We're tiny and under the radar

Tentative: 
- Incumbent inertia: The main players don't want to radically change their purchase flow and interface. 
- Stay smallish enough to ignore. Even getting 1% of the market is still a lot.
- The big players like their cash cow -- switching to this system turns off most of it (we will admittedly be less profitable overall).

Potential stronger moat over time: 
- proprietary feedback loops about menu accuracy and fulfillment reliability 
- Strong "Pro mom and pop" brand and user habit

### Marketing ideas
- **Status:** Open
- downriver facebook and reddit communities
- Audience/channel ideas: Southgate/Metro Detroit pickup customers, food explorers, price-sensitive diners, local restaurant groups, and social posts around specific dish cravings.
- Messaging angles: find the exact dish nearby, avoid delivery-app markups, order from more restaurants than delivery apps cover, and discover local menu items hidden inside PDFs/images.
- Launch/distribution experiments: small local dish-search demos, "where can I get X nearby?" posts, and comparison examples showing restaurant-menu prices versus delivery-app prices.
- Local "guy" takes on DoorDash
- when people search "doordash fees" or "reduce doordash fees", we could put up an add
- go on gig economy forums or social sites
- market to niche communities like spice-heads, give them a special "spice search" or spice explorer. For beer lovers give them beer histograms. Wild mushrooms/truffle. Also gluten-free, keto, halal. Calculate estimated macro nutrients. Happy hours & good values, eating challenges. Most kid options. Refreshers. See niche-food-communities.md and niche-food-community-marketing.md
- When doing passes over all the restaurants ask if anything may be instagrammable (see instagrammable-food-moments.md and
- Menu audits or health check (check for consistency / anomalies), also dish suggestions
- Restaurant intelligence / find the differentiator. Describe where the restaurant sits in niche
- Cost per inch or sq. in.
- try to get doordash related ratings off restaurant pages
- i want to get menu intelligence for suggesting menu improvements

---

## Shape

### MVP
A small-city or neighborhood pilot that:
1. Indexes menus for a limited set of nearby restaurants.
2. Supports search for exact or fuzzy dish names.
3. Shows dish, restaurant, price if available, store and dish-level ratings, distance, and source confidence.
4. Lets the user request a pickup order.
5. Uses a human-in-the-loop or constrained AI phone agent to place the order and confirm pickup details.

The MVP should test whether users actually search by dish often enough, whether menu data can stay accurate, and whether phone ordering through an agent works reliably.

### Weird angle
The weird edge is not just "restaurant search"; it is search-first ordering at the dish level plus an AI phone agent that bypasses marketplace ordering rails and tries to preserve normal in-store prices. The user does not start with a restaurant brand. They start with a craving: "who nearby has this dish?"

### Variants, offshoots, and complementary products
- Dish finder only: search nearby menus for specific dishes, then hand off to the restaurant's existing ordering method.
- Pickup concierge: search plus AI/human phone ordering for restaurants without online ordering.
- Price-aware anti-markup tool: compare delivery-app-style ordering against direct pickup prices, if price data can be obtained accurately.
- Include owner profile to make the transaction more personal
- Try to get restaurants to do dynamic pricing based on their foot traffic
- Gluten free finder
- Handicap access site
- Soup daddy, soup of the day listings
- Daily specials
- Instagrammability / thumb stoppers / feed worthy
- menu audits

---

## Tensions

### Risks
- Menu data may be stale, incomplete, or inconsistent
- AI phone ordering may fail in noisy, ambiguous, high-variation restaurant calls, especially around modifications, availability, timing, and payment.
- Restaurants or users may object to automated phone agents, especially if calls are poor quality or create operational burden.
- "Normal in-store prices" may be hard to guarantee without live confirmation and could vary by channel, time, or menu source.
- Users interested in the "cheapest prices" might not be willing to pay extra for an app.
- Ordering multiple items is weird. For dish results ther should be a button to order, and a button to add to cart. When an item is in the cart we maybe switch to "restaurant mode". Or to be creative there could be some sort of "search on route" where dishes along the drive route are shown.
- Some states have laws against 3rd-party delivery apps doing orders without the restaurants consent, and some of these laws apply to pickup orders as well. So we will have to figure out how to contact restaurant owners or get there attention. maybe with a ditch doordash campaign, or perhaps getting on google "order online" button, but that will be hard without any way to do orders.

### Open questions
- What happens if the dish is unavailable, the menu price differs, or the restaurant refuses AI-agent orders?
- Which initial cuisine type, or user segment is most promising for a pilot?
- Is the strongest wedge search/discovery, price savings, pickup convenience, or restaurant access where online ordering is poor?

---

## Raw concept

Users search for specific dishes across nearby restaurant menus, search results show all matching dishes at nearby restaurants, the user clicks to order one of the results, then an AI phone agent places pickup orders at normal in-store prices.

---

## Current thesis
This may be worth pursuing because it starts from a concrete user behavior: craving a specific dish and wanting to compare nearby offerings. The interesting twist is combining dish-level search with an AI phone ordering agent to access normal restaurant pickup prices instead of defaulting to delivery-app marketplaces. The biggest uncertainties are practical rather than conceptual: menu freshness, phone-order reliability, restaurant tolerance, business model, and whether enough users have this dish-first search habit to support a product.
