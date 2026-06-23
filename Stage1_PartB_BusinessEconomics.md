# SliceMatic — Business Unit Economics

**Project:** SliceMatic Digital Ordering System
**Stage:** 1 (Part B of 2) — Business Unit Economics
**Prepared for:** SliceMatic (New Ashok Nagar, Delhi) — Founder: Mr. Rajan Sharma
**Document status:** Draft v1.0 for client review
**Date:** 23 June 2026

---

## 0. Approach

This is a financial model for a single-outlet pizza delivery business in East Delhi. We take the
client's reference baseline (FY 2024–25 model) as the starting point, reproduce its core unit
economics, and then **stress-test it** against the six scenarios the business actually cares
about (rent shocks, aggregator commissions, ingredient inflation, etc.). Where we refine a
baseline number, the justification is noted inline. All figures are in INR; the P&L is computed
**ex-GST** (GST is a pass-through — see Section 8).

**Headline numbers (baseline, 60% capacity):**

| Metric | Value |
|---|---|
| Average Order Value (AOV) | ₹847 |
| Monthly revenue (ex-GST) | ~₹9.96 L |
| Contribution margin / order | ₹644 (76%) |
| Total monthly fixed costs | ₹2,02,910 |
| Break-even | ~315 orders/mo ≈ **11/day** |
| Operating profit (EBITDA) | ~₹7.0 L/mo |
| Payback period | ~18 months |

---

## 1. Monthly Fixed Costs

Costs incurred regardless of order volume — the minimum monthly cash outflow before any profit.

| Cost item | Detail | Monthly (₹) |
|---|---|---:|
| Kitchen rent | 1,200 sq ft commercial lease, New Ashok Nagar | 55,000 |
| Equipment EMI | 2-deck oven, mixer, refrigeration — 36-mo loan on ₹4.5L | 14,500 |
| Electricity | Commercial rate, ~1,800 units/mo | 12,600 |
| Gas / LPG | 3 commercial cylinders @ ₹1,850 | 5,550 |
| Head chef | 1 experienced pizza chef | 28,000 |
| Kitchen helper | 1 prep staff (min wage + ESI/PF) | 16,500 |
| Counter + billing | 1 person | 18,000 |
| Delivery riders | 2 riders, fixed component + fuel allowance | 32,000 |
| Internet + POS + SaaS | Broadband + POS + gateway annual fee amortised | 2,800 |
| Marketing (fixed) | Meta Ads retainer, pamphlets, GBP boost | 8,000 |
| Packaging (fixed component) | Branded boxes/bags minimum order | 4,200 |
| Misc / contingency (3%) | Maintenance, repairs, consumables | 5,760 |
| **Total fixed costs** | | **2,02,910** |

> *Note:* Rider figure is the **fixed** salary component only. The per-delivery incentive
> (₹15/order) is a **variable** cost (Section 5).

---

## 2. COGS per Pizza — by Pizza Type

COGS per pizza = raw ingredients + packaging + per-order delivery variable. (Wholesale rates,
INA Market / Azadpur Mandi.)

| Component | Margherita (Thin) | Farm House (Thick) | Cheese Burst (premium) | Avg across menu |
|---|---:|---:|---:|---:|
| Pizza base ingredients | 38 | 45 | 72 | 52 |
| Sauce + seasoning | 12 | 14 | 14 | 13 |
| Cheese (mozzarella) | 28 | 32 | 65 | 38 |
| Pizza-specific toppings | 8 | 22 | 18 | 17 |
| Add-on topping (avg 1) | 10 | 10 | 10 | 10 |
| Packaging (box + bag) | 18 | 18 | 18 | 18 |
| Delivery variable | 22 | 22 | 22 | 22 |
| **Total COGS / pizza** | **136** | **163** | **219** | **170** |

---

## 3. Gross Margin — per Pizza and by Category

| Pizza | Selling price* | COGS | Gross margin | GM % |
|---|---:|---:|---:|---:|
| Margherita (Thin) | 397 | 136 | 261 | 65.7% |
| Farm House (Thick) | 417 | 163 | 254 | 60.9% |
| Cheese Burst (premium) | 447 | 219 | 228 | 51.0% |
| **Average** | **420** | **170** | **250** | **59.5%** |

\* Selling price = cheapest base + pizza + 1 average topping. Actual order value varies; AOV of
₹847 reflects multi-pizza orders and premium selections.

**Margin by category split (illustrative, per average order line):**

| Category | Avg menu price | Approx. food cost | Approx. GM % |
|---|---:|---:|---:|
| Base | ~₹177 (avg of 5) | ₹38–72 | high (~65–75%) |
| Pizza | ~₹342 (avg of 8) | ₹20–55 | high (~80%+) |
| Topping | ~₹50 (avg of 10) | ~₹10 | very high (~80%) |

**Insight (challenge to baseline):** Margin is **inversely driven by cheese intensity**.
Cheese Burst's gross margin (51%) is ~15 pts below Margherita's (65.7%) purely because cheese
cost jumps ₹28 → ₹65. The menu's profit lever is therefore **mix**, not price: nudging customers
toward thin/thick bases and high-margin toppings lifts blended margin more than a price rise
would. This is a direct input to the Stage 3 recommendation engine.

---

## 4. Revenue Model — Monthly Projections (60% capacity)

| Metric | Weekday | Weekend/Holiday | Monthly total |
|---|---:|---:|---:|
| Days in period | 22 | 8 | 30 |
| Orders/day (60% cap) | 38 | 68 | ~47 avg |
| AOV | ₹792 | ₹940 | ₹847 |
| Daily revenue | ₹30,096 | ₹63,920 | ~₹40,500 avg |
| Monthly gross revenue | ₹6,62,112 | ₹5,11,360 | **₹11,73,472** |
| GST collected (18%, → Govt) | | | ₹1,77,564 |
| **Net revenue (ex-GST)** | | | **₹9,95,908** |

> Max capacity = 80 orders/day (1 pizza every 6 min, 2-oven setup). 60% utilisation is a
> deliberately conservative launch assumption. At 100% capacity revenue ≈ ₹19.6 L/mo.

---

## 5. Contribution Margin & Break-Even

Contribution margin per order = revenue (ex-GST) − **all** variable costs per order. It measures
how much each order contributes toward fixed costs and then profit.

| P&L line | Per order (₹) | Monthly @ 60% (₹) |
|---|---:|---:|
| Revenue (ex-GST) | 847 | 11,88,996 |
| − Ingredient COGS | (148) | (2,07,768) |
| − Packaging (variable) | (18) | (25,272) |
| − Delivery variable (rider incentive) | (22) | (30,888) |
| − Payment gateway fee (1.8% of GMV) | (15) | (21,402) |
| **Contribution margin** | **644 (76%)** | **9,03,666** |
| − Total fixed costs | | (2,02,910) |
| **Operating profit (EBITDA)** | | **7,00,756** |
| Operating margin | | **58.9%** |

**Break-even:**

| Fixed costs/mo | CM/order | Break-even/mo | Break-even/day |
|---:|---:|---:|---:|
| ₹2,02,910 | ₹644 | **315 orders** | **~11/day** |

At 60% capacity (47/day) the outlet runs at **4.3× break-even** — a wide safety margin. It only
turns unprofitable below ~11 orders/day (a 76% collapse from plan).

**Refinement / caveat (critical note):** the baseline counts ingredient COGS at ₹148/order while
the per-pizza table shows ~₹130 food/pizza, and AOV ₹847 implies **>1 pizza per order**. So the
"per order" variable line is conservative for a single pizza but **understates** food cost for
genuinely multi-pizza orders (food scales with pizzas; delivery and gateway scale with *orders*).
For order-level accuracy we recommend the model scale ingredient + packaging by pizza count and
keep delivery as a per-order cost. We retain the baseline figures here for comparability and flag
this for refinement.

---

## 6. Delivery Radius Economics

| Radius | Households served | Avg delivery time | Trips/day/rider | Viable? |
|---|---|---|---|---|
| 0–2 km | ~18,000 | 8–12 min | 55–60 | Yes — premium SLA |
| 2–4 km | ~55,000 | 15–22 min | 30–35 | **Yes — sweet spot** |
| 4–6 km | ~1,10,000 | 25–40 min | 18–22 | Marginal — needs 3rd rider |
| > 6 km | diminishing | 40+ min | 12–15 | Not viable at launch |

**Recommendation:** Launch at **4 km** — large addressable market without breaching the 30-min
SLA. With 2 riders at 30–35 trips each, delivery capacity ≈ 60–70 orders/day, comfortably above
the 47/day plan. Expand to 5 km once a 3rd rider is added (~₹16,000/mo fixed; see Q3).

---

## 7. GST Treatment — How 18% Flows Through the P&L

Home delivery of restaurant food attracts **18% GST** (no composition scheme). SliceMatic is
GST-registered.

- **Who absorbs it? The customer.** GST is added on top of the bill; SliceMatic collects it on
  the government's behalf. It is **never the shop's money**.
- **It does not flow through profit.** GST collected is a *liability*, not revenue. The P&L is
  always computed on the **ex-GST** amount.
- **Input Tax Credit (ITC):** SliceMatic reclaims GST paid on ingredients, packaging and
  equipment (~₹18,000–22,000/mo), netted against GST collected.
- **Effective GST liability:** Output GST (~₹1,77,564/mo) − ITC (~₹20,000/mo) ≈ **₹1,57,564/mo**
  net remittance.
- **Pricing implication for the app:** menu prices are GST-**exclusive**; GST is added once, at
  the billing stage, on the **post-discount** total (not per item).

**Sample bill (Stage 2 reference):**

| Line | ₹ |
|---|---:|
| Base: Cheese Burst | 229.00 |
| Pizza: BBQ Chicken | 379.00 |
| Topping: Extra Cheese | 69.00 |
| Unit subtotal | 677.00 |
| × Qty 5 → Subtotal | 3,385.00 |
| Discount 10% (qty ≥ 5) | (338.50) |
| Post-discount subtotal | 3,046.50 |
| GST @ 18% | 548.37 |
| **Total payable** | **3,594.87** |

---

## 8. Stress Tests — "Challenge These Numbers"

The six scenarios the model must answer. Each shows the method so the result can be reproduced.

### Q1 — Rent rises to ₹70,000/mo. New break-even? At what rent is the model unviable?

- New fixed costs = 2,02,910 − 55,000 + 70,000 = **₹2,17,910**.
- New break-even = 2,17,910 / 644 = **338 orders/mo ≈ 11.3/day → ~12/day**.
- **Break-even barely moves (11 → ~12/day).** A ₹15k rent hike costs only ~1 extra order/day.

*At what rent does it become unviable?* Define "unviable" as break-even reaching the **planned
operating volume** (47/day ≈ 1,404 orders/mo). That requires fixed costs to absorb the full
contribution at plan: 1,404 × 644 ≈ ₹9.04 L. Non-rent fixed costs are ₹1,47,910, so rent would
have to reach **~₹7.6 L/month** — about **13× current rent** — before the business stops clearing
its costs at planned volume.

**Conclusion:** thanks to the 76% contribution margin, the model is **extremely robust to rent**.
Rent is *not* the binding risk — **demand volume is**.

### Q2 — 40% of orders via aggregator at 25% commission. New CM/order and break-even?

*Assumptions:* aggregator takes 25% of the ex-GST order value and handles **delivery and payment**
(so on those orders SliceMatic saves the ₹22 rider incentive and ₹15 gateway fee). Direct orders
unchanged.

- **Aggregator order CM** = 847 − 148 (ingredients) − 18 (packaging) − 211.75 (25% commission)
  = **₹469.25** (a ~27% hit vs direct).
- **Direct order CM** = ₹644 (unchanged).
- **Blended CM** = 0.4 × 469.25 + 0.6 × 644 = **₹574.10/order**.
- **New break-even** = 2,02,910 / 574.10 = **354 orders/mo ≈ 11.8/day → ~12/day**.

**Conclusion:** the 25% commission slashes margin **on aggregator orders specifically** (₹644 →
₹469), but because direct orders dominate, blended CM only falls ~11% and break-even rises just
~1/day. Aggregators are a viable **demand channel** — but every order pushed to direct (own app)
is worth ~₹175 more in contribution, which is the core economic argument for building this system.

### Q3 — At what daily volume is a 3rd rider justified?

- **Financial test:** a 3rd rider adds ~₹16,000/mo fixed. At ₹644 CM/order it pays for itself with
  16,000 / 644 ≈ **25 extra orders/month (<1/day)** — financially trivial.
- **Physical test (the real constraint):** 2 riders at 30–35 trips/day ≈ **60–70 deliveries/day**
  capacity. The 30-min SLA starts to break as volume approaches that ceiling.

**Conclusion:** hire the 3rd rider when daily orders reach **~55–60/day** — *before* the 2-rider
fleet saturates — to protect the SLA, not because of cost. The trigger is **capacity/SLA, not
economics.** (This also unlocks the 5 km radius.)

### Q4 — Impact of the qty ≥ 5 / 10% discount on a 5-pizza order. Value-driver or leak?

Using the sample 5× Cheese Burst order (worst-case margin):

| | No discount | With 10% discount |
|---|---:|---:|
| Revenue (ex-GST) | 3,385.00 | 3,046.50 |
| Variable costs (food 5×179 + pkg 5×18 + 1 delivery + gateway) | ~1,079 | ~1,072 |
| **Contribution margin** | **~2,306** | **~1,975** |

- The discount removes **~₹331 of contribution** from this order (≈ the ₹338.50 discount, less a
  tiny gateway saving). CM% drops from ~68% to ~65%.
- **But** compare a 4-pizza order (no discount, CM ≈ ₹1,840) to a discounted 5-pizza order (CM ≈
  ₹1,975): if the discount **converts a 4-pizza intent into 5**, total contribution still **rises
  by ~₹134**.

**Conclusion: it's both — depending on behaviour.** It is a **value-driver** when it lifts a
customer across the threshold (4→5), and a **margin leak** (~₹331/order) on customers who would
have bought 5+ anyway. **Recommendation:** keep the discount **configurable**, watch the order-size
distribution — heavy clustering exactly at 5 suggests it's driving behaviour (keep it); if 5+
orders occur regardless, trial a smaller % or a free high-margin topping instead (cheaper to give,
same perceived value).

### Q5 — COGS +12% (ingredient inflation). Extra daily orders to hold EBITDA flat?

- Ingredient COGS 148 → 148 × 1.12 = 165.76, i.e. **+₹17.76/order**.
- New CM/order = 644 − 17.76 = **₹626.24**.
- To hold EBITDA at ₹7,00,756: orders × 626.24 − 2,02,910 = 700,756 → orders = 9,03,666 / 626.24 =
  **1,443/mo ≈ 48.1/day** (vs 1,403/mo ≈ 47/day baseline).
- **Additional needed = ~40 orders/month ≈ 1.3 extra orders/day.**

**Conclusion:** a 12% ingredient shock is absorbed by **barely more than one extra order per day** —
again a function of the high contribution margin. (Applying 12% to *all* COGS components gives
~1.5/day — same order of magnitude.) Ingredient inflation is a **low-severity** risk for this model.

### Q6 — Three BI metrics from the order log that directly improve profitability

1. **Basket / AOV analysis (combo + topping attach rate).** Which base+pizza+topping combinations
   and upsells drive higher AOV. Because fixed costs are flat, every rupee of incremental AOV drops
   almost straight to profit → guides upsell prompts and menu engineering.
2. **Demand by hour × day-of-week (peak heatmap).** Reveals true peaks so staff and rider
   scheduling match demand — cuts idle labour cost and prevents SLA-breaching overload. (Feeds the
   Stage 3 demand-forecasting feature directly.)
3. **Item-level contribution-margin ranking.** Top *sellers* vs most *profitable* items — promote
   high-margin lines, reprice/retire low-margin ones (e.g. the Cheese Burst margin drag),
   improving blended margin without touching volume.

*Bonus metric:* **discount-effectiveness** (order-size distribution around the qty≥5 threshold) to
tune the discount per Q4; and **repeat-customer rate** for retention targeting.

---

## 9. Summary of Refinements / Challenges to the Baseline

| # | Baseline | Our refinement | Rationale |
|---|---|---|---|
| 1 | Ingredient COGS flat at ₹148/order | Scale ingredients + packaging by pizza count; keep delivery & gateway per-order | AOV ₹847 implies >1 pizza/order; flat food cost understates multi-pizza orders |
| 2 | Gateway fee 1.8% on all orders | Apply only to Card/UPI share (Cash pays no gateway) | Cash orders incur no gateway fee → effective rate < 1.8% |
| 3 | Rent framed as a key risk | Rent is low-risk (robust to ~13× increase); **demand volume** is the real risk | Driven by the 76% contribution margin |
| 4 | Flat 10% qty≥5 discount | Make threshold/percentage configurable + monitored | It is margin-accretive only when it shifts order size (Q4) |

---

*Prepared as Stage 1, Part B. To be merged with Part A (PRD) into a single submission PDF after
review.*
