# The Shelf Is Lying - Project Plan

## 1. Project in one sentence

Build an inventory decision tool for a fictional omnichannel retailer that identifies products shown as available but unlikely to be findable or sellable, explains whether returns or store-specific clearance activity may be responsible, and recommends the most valuable action for store teams to take.

The project should answer a practical question:

> When the system says an item is in stock but the shelf is empty, where is it likely to be, and is it worth spending time to recover it?

## 2. The four ideas that define the project

These are not optional features. Every part of the analysis should support them.

### 2.1 Recorded inventory is not the same as available inventory

The project starts from the gap between:

- **Book inventory:** the quantity recorded in the inventory system.
- **Sellable inventory:** units that are not damaged, quarantined, or otherwise unavailable.
- **Findable inventory:** units that a team member can physically locate.
- **Shelf inventory:** units placed where a guest expects to find them.
- **Available-to-promise inventory:** units that can safely be offered for pickup or delivery.

An item can have positive book inventory while having zero practical availability.

### 2.2 Returns can create hidden availability problems

A return does not instantly become shelf-ready inventory. It may spend time:

- awaiting inspection;
- in a returns or reshop area;
- waiting for repricing;
- moved to clearance;
- classified as damaged;
- recorded under the wrong location.

The project will measure **return-to-shelf lag** and test whether recent returns help explain online cancellations and no-sale inventory.

### 2.3 Clearance is a shadow inventory location

Clearance is central to the project. It is not simply a section about markdowns.

Each store can develop a different clearance assortment because of local demand, returns, seasonal sell-through, store layout, markdown timing, and execution. An item may still exist in the store but no longer be in its expected location. This can make it difficult for both guests and fulfillment teams to find.

The project will create a **clearance fingerprint** for each store and investigate why similar stores end up with different clearance inventory.

### 2.4 The result must be an action, not an anomaly score

Store labor is limited. The final output must recommend what to do and rank actions by expected value. Possible actions are:

- verify the shelf and perform a cycle count;
- search returns, reshop, and clearance locations;
- return recovered units to the regular selling location;
- correct the recorded quantity;
- temporarily suppress online availability until the count is verified;
- transfer inventory to a store with stronger remaining demand;
- take or deepen a markdown;
- take no action when recovery is unlikely to justify the labor.

## 3. Business setting

Use a fictional general-merchandise retailer. Do not imply that the data or operating procedures come from Target.

The first case study will follow a **back-to-campus home and dorm collection** because it naturally combines:

- a short selling season;
- different demand in college-town and suburban stores;
- online pickup demand;
- frequent returns;
- items moving from regular shelves to clearance;
- rapid loss of value after the season;
- meaningful differences between stores.

### Proposed scope

- 24 stores
- 6 market or store archetypes
- 120 products
- 16 weeks of daily activity
- Regular-price, first-markdown, deeper-markdown, and post-season periods
- In-store purchases and online pickup orders

This is large enough to show patterns while remaining understandable.

## 4. Intended audience

The main audience is an inventory analyst or inventory planning leader deciding how stores should use limited labor to protect availability and margin.

Secondary users are:

- district or store operations leaders;
- merchandising and clearance planners;
- digital fulfillment teams;
- vendor managers investigating repeated product problems.

The project should be understandable without a data science background.

## 5. Questions the analysis must answer

1. Which store-product combinations have positive recorded inventory but a high risk of not being findable?
2. Which signals provide credible evidence of false availability?
3. How often do recent returns precede pickup cancellations, long no-sale periods, or inventory corrections?
4. How different are clearance assortments across otherwise similar stores?
5. Which stores appear to have ordinary local-demand clearance, and which appear to have operationally stranded inventory?
6. Which products should be checked first under a fixed labor budget?
7. Should a suspicious item be recovered to the shelf, left in clearance, transferred, marked down, suppressed online, or written off?
8. How much cancellation risk, sales, and gross margin could a targeted intervention recover compared with simpler policies?

## 6. Data design

The main dataset will be synthetic because public retail datasets do not contain the physical-location, return-disposition, pickup-cancellation, and audit outcomes needed for this problem. The synthetic data must be clearly labeled and generated from readable business rules.

Random numbers should create variation, not replace reasoning. Every important pattern must have a documented cause.

### 6.1 Store data

Fields include:

- store ID;
- market type;
- selling-area size;
- college proximity;
- typical online pickup share;
- estimated daily inventory-labor capacity;
- clearance-area capacity;
- execution profile used only to generate realistic variation.

Example store archetypes include college-town, urban small-format, suburban family, warm-weather, high-digital-demand, and lower-volume stores.

### 6.2 Product data

Fields include:

- product ID and description;
- category and subcategory;
- regular price and unit cost;
- launch date and seasonal end date;
- size or handling class;
- return tendency;
- expected markdown schedule;
- base demand and store-archetype affinity.

Products should be recognizable dorm and home items rather than meaningless SKU numbers alone.

### 6.3 Daily inventory snapshots

For each store and product:

- beginning and ending book inventory;
- estimated true physical quantity;
- units assigned to the shelf, backroom, returns area, clearance, pickup hold, damaged, and missing states;
- inventory adjustments;
- latest verified count date.

The true physical state is retained as evaluation data. It is not exposed to the risk model as an input.

### 6.4 Sales and demand

Include:

- in-store units sold;
- regular-price and markdown sales;
- lost-demand estimate when shelf inventory is unavailable;
- local seasonal demand pattern;
- promotion indicators.

Demand should reflect store and product differences instead of using the same curve everywhere.

### 6.5 Returns and disposition

Each return should include:

- date and store;
- product and quantity;
- original channel;
- disposition: shelf-ready, reshop, clearance, damaged, or pending inspection;
- time until the item reaches its next location;
- whether the inventory system becomes available before the physical process is complete.

This table is necessary for calculating return-to-shelf lag.

### 6.6 Online pickup orders

Include:

- order date;
- requested quantity;
- fulfilled, partially fulfilled, or cancelled status;
- cancellation reason when known;
- recorded quantity at order time;
- physical location outcome when an audit later occurs.

### 6.7 Markdown and clearance events

Include:

- markdown date and depth;
- reason: planned seasonal markdown, slow sell-through, return disposition, damaged packaging, or local action;
- regular and clearance location assignments;
- days spent in clearance;
- clearance sales and remaining units.

### 6.8 Location checks and cycle-count outcomes

These records provide the observable labels for analysis:

- expected location;
- location searched;
- quantity found;
- actual location found;
- corrected quantity;
- minutes spent;
- action taken afterward.

## 7. Important measures

### Inventory truth measures

- **Availability gap:** positive book inventory with no findable sellable units.
- **Book-to-findable ratio:** findable units divided by recorded units.
- **Pickup failure rate:** cancelled or shorted pickup orders divided by pickup orders.
- **No-sale inventory age:** days since the last sale while book inventory remains positive.
- **Count-adjustment rate:** frequency and size of verified inventory corrections.

### Returns measures

- **Return-to-shelf lag:** time from return receipt to a sellable location.
- **Return-stranding rate:** share of sellable returns not placed in a selling location within an agreed period.
- **Post-return availability failure:** pickup failure or no-sale behavior following a return.

### Clearance measures

- clearance sell-through;
- median days in clearance;
- average markdown depth;
- clearance units originating from returns;
- clearance assortment overlap between peer stores;
- share of a store's clearance assortment unique to that store;
- clearance items with repeated online fulfillment failures;
- units that should be consolidated, transferred, or removed from online availability.

### Decision measures

- expected recovered sales;
- expected recovered gross margin;
- avoided pickup cancellations;
- labor minutes required;
- expected recovered margin per labor hour;
- action confidence;
- seasonal urgency.

## 8. Analytical approach

The project should favor clear reasoning over sophisticated-looking code.

### 8.1 Start with an auditable rule-based baseline

Flag a store-product combination when several understandable conditions occur together, such as:

- positive book inventory;
- no recent sales;
- repeated pickup failures;
- recent returns;
- a recent markdown or clearance move;
- a stale verified count;
- normal sales for the same item at peer stores.

This baseline creates a useful comparison and shows business understanding.

### 8.2 Build one interpretable risk model

Use a logistic regression or a shallow decision tree to estimate the probability that positive book inventory is not findable.

Candidate inputs:

- days since last sale;
- book units;
- seven-day pickup cancellation rate;
- recent return units;
- return-to-shelf lag;
- markdown status;
- days in clearance;
- days since last verified count;
- recent inventory adjustments;
- difference between expected and observed sales;
- peer-store sell-through.

Do not build a model tournament. Compare the chosen model with the rule-based baseline and explain where each works or fails.

### 8.3 Estimate the likely hidden location

Use transparent conditional probabilities or simple classification to estimate whether the item is most likely in:

- clearance;
- returns or reshop;
- the backroom;
- a pickup hold;
- a damaged state;
- a truly missing state.

The explanation should name the strongest evidence, such as "three recent returns and a markdown event with no subsequent sale."

### 8.4 Build the store clearance fingerprint

For each store, summarize:

- what enters clearance;
- how quickly it sells;
- how much comes from returns;
- how its assortment differs from peer stores;
- how much clearance inventory remains digitally available;
- whether its unusual mix is supported by local demand or suggests stranded inventory.

Use direct comparisons and simple distances or overlaps. Avoid clustering merely to make the work appear advanced.

### 8.5 Convert risk into a recommended action

Estimate the value of an intervention using:

- probability the item is not findable;
- probability it can be recovered;
- units likely recoverable;
- expected remaining seasonal demand;
- current unit margin;
- expected markdown loss if action is delayed;
- investigation time and labor cost;
- cost of another failed pickup attempt.

Rank actions by expected value per labor hour, subject to each store's weekly labor capacity.

## 9. Recommendation logic

The recommendation engine should remain readable. It should produce one primary action and a short reason.

Examples:

- **Search returns and clearance:** recent returns, recent markdown, no sales, and pickup failures.
- **Verify shelf and cycle count:** high book quantity, stale count, and unexplained no-sale period.
- **Suppress online until verified:** repeated pickup failures and low availability confidence.
- **Recover to regular shelf:** product still has strong demand and enough season remaining.
- **Keep in clearance:** low full-price demand but healthy clearance sell-through.
- **Transfer:** weak local demand, strong peer-store demand, sufficient margin, and enough season remaining.
- **Deepen markdown:** low local and peer demand close to the seasonal end date.
- **No action:** expected recovery is lower than the labor and handling cost.

## 10. Evaluation plan

### 10.1 Detection quality

Evaluate whether the highest-risk recommendations contain more true availability problems than:

- random inspections;
- checking the largest book quantities first;
- checking products with the most cancellations first.

Use precision among the top items that fit within the labor budget, recall, and calibration. Overall accuracy is not sufficient because most inventory records will be normal.

### 10.2 Business-policy quality

Simulate a fixed weekly labor budget and compare:

- no targeted intervention;
- a simple cancellation-first policy;
- the proposed value-per-labor-hour policy.

Measure recovered sales, recovered margin, avoided cancellations, corrected inventory records, and clearance units resolved.

### 10.3 Clearance analysis quality

Confirm that the project can distinguish:

- ordinary local clearance caused by genuine demand differences;
- return-heavy clearance;
- seasonal leftovers;
- likely operationally stranded inventory.

Store comparisons should use comparable peers rather than treating every difference as a problem.

### 10.4 Explanation quality

Every high-priority recommendation must show:

- what happened;
- why it is suspicious;
- where the item may be;
- what action is recommended;
- the estimated benefit;
- the uncertainty or limitation.

## 11. Final user experience

Build a small Streamlit application with four focused views.

### 11.1 Executive overview

Answer:

- How large is the availability gap?
- What is driving it?
- How much value is concentrated in the top recommended actions?
- How does the seasonal deadline change the recommendation?

### 11.2 Item investigation

Allow the user to select one store and product and view its history:

- book inventory;
- estimated physical states;
- sales;
- returns;
- cancellations;
- markdowns;
- location checks;
- recommended action and explanation.

### 11.3 Clearance by store

Show the store's clearance fingerprint and compare it with similar stores. Emphasize unique assortment, return-originated items, aging inventory, and items that remain digitally available but difficult to fulfill.

### 11.4 Weekly action plan

Show the ranked action queue under a chosen labor budget. The user should be able to see which actions are funded, the reason for each, and the expected impact.

## 12. Project structure

All code and project artifacts will live under `the-shelf-is-lying/`. The root-level `plan.md` remains outside it.

```text
Inventory Analysis Project/
|-- plan.md
`-- the-shelf-is-lying/
    |-- README.md
    |-- requirements.txt
    |-- app.py
    |-- data/
    |   |-- raw/
    |   `-- processed/
    |-- notebooks/
    |   |-- 01_inventory_truth.ipynb
    |   `-- 02_clearance_and_actions.ipynb
    |-- src/
    |   |-- generate_data.py
    |   |-- prepare_data.py
    |   |-- metrics.py
    |   |-- availability.py
    |   |-- clearance.py
    |   `-- recommendations.py
    |-- tests/
    |   `-- test_business_rules.py
    `-- reports/
        |-- figures/
        `-- leadership_summary.md
```

The structure may be simplified if a file does not earn its place. Do not create empty architectural layers.

## 13. Coding approach

Use:

- Python;
- pandas and NumPy;
- scikit-learn for the one interpretable model;
- Plotly or Altair for charts;
- Streamlit for the final interface;
- Jupyter only for exploratory analysis and explaining findings.

Code principles:

- prefer named business functions over generic frameworks;
- keep calculations visible and explainable;
- use comments for business reasoning, not line-by-line narration;
- avoid unnecessary classes;
- keep configuration in a small group of constants;
- give tables and columns meaningful retail names;
- use a fixed random seed so results are reproducible;
- use assertions and a few focused tests for inventory conservation and recommendation rules;
- keep notebooks short and move reused calculations into `src/`;
- do not include generated claims that cannot be traced to the data.

Do not add:

- an LLM or chatbot;
- cloud infrastructure;
- authentication;
- a production API;
- Docker or Kubernetes;
- a complex database;
- automated orchestration;
- model registries or experiment tracking platforms;
- multiple competing machine-learning models;
- decorative dashboard pages that do not answer a business question.

## 14. Build phases

### Phase 1: Create the business definitions and project skeleton

**Objective:** Make every inventory state, measure, and action unambiguous before generating data.

**Work:**

- create the folder structure;
- write the project README;
- define inventory states and event timing;
- define the seasonal calendar;
- define store archetypes and product categories;
- write formulas for the primary measures.

**Checks:**

- book, physical, sellable, findable, shelf, and available-to-promise inventory are clearly distinguished;
- returns and clearance transitions have explicit timing;
- every recommended action has a business meaning.

### Phase 2: Generate a traceable retail dataset

**Objective:** Create realistic daily activity with known hidden inventory states.

**Work:**

- generate stores and products;
- generate demand and sales;
- process returns through physical states;
- create markdown and clearance movements;
- generate online pickup attempts and cancellations;
- generate audits and count corrections;
- validate inventory conservation.

**Checks:**

- units do not appear or disappear without an event;
- the same item behaves differently across relevant store types;
- recent returns and clearance moves sometimes, but not always, produce availability problems;
- the data contains normal cases as well as problems.

### Phase 3: Establish the business baseline

**Objective:** Describe the problem before modeling it.

**Work:**

- calculate the inventory truth, returns, and clearance measures;
- quantify the availability gap;
- identify when returns precede failures;
- compare clearance assortments across peer stores;
- create a simple rule-based risk score.

**Checks:**

- findings can be explained without model terminology;
- store differences are not automatically labeled as failures;
- the analysis includes concrete item journeys.

### Phase 4: Estimate availability risk and hidden location

**Objective:** Rank items that are most likely to be recorded but not findable.

**Work:**

- create time-safe features;
- train one interpretable model using audit outcomes;
- compare it with the rule-based baseline;
- estimate the most likely hidden location;
- generate plain-language reason codes.

**Checks:**

- no future information enters the model;
- the ranked list outperforms simple inspection policies;
- explanations agree with the underlying signals;
- uncertainty is visible.

### Phase 5: Build clearance fingerprints

**Objective:** Explain why clearance differs by store and identify stranded inventory.

**Work:**

- summarize clearance mix, age, markdown depth, origin, and sell-through;
- compare each store with relevant peers;
- measure assortment overlap and unique clearance items;
- separate local-demand outcomes from operational warning signs;
- connect clearance patterns to online availability failures.

**Checks:**

- the analysis does not assume that different clearance is inherently bad;
- each unusual store has supporting evidence;
- return-originated and seasonal clearance can be separated.

### Phase 6: Build and evaluate the action policy

**Objective:** Convert risk into a weekly plan under limited labor.

**Work:**

- estimate recoverable units and remaining demand;
- calculate expected benefit and labor cost;
- assign primary actions and reason codes;
- rank actions under store-level labor limits;
- compare the policy with simple alternatives.

**Checks:**

- actions follow documented rules;
- expected value calculations reconcile to price, cost, units, and time;
- low-value problems can correctly receive no action;
- the proposed policy improves simulated business outcomes.

### Phase 7: Create the application and leadership story

**Objective:** Make the work usable and presentable without burying the decision in charts.

**Work:**

- build the four Streamlit views;
- select two or three detailed item journeys;
- write the leadership summary;
- produce final figures and screenshots;
- document data limitations and proposed pilot design.

**Checks:**

- a reviewer can understand the problem and recommendation in five minutes;
- every chart supports a decision;
- the application works from a clean environment;
- the README clearly states that the operational data is synthetic.

## 15. Completion criteria

The project is complete when:

- the difference between recorded and practical availability is central and measurable;
- returns are traced through disposition and return-to-shelf lag;
- clearance is analyzed as a store-specific inventory location, not a generic markdown page;
- the model ranks likely availability problems using only information available at decision time;
- the system recommends understandable actions under a labor budget;
- the recommendation policy beats simple baselines in the simulation;
- at least two item journeys show how the conclusion was reached;
- limitations and synthetic-data assumptions are explicit;
- the dashboard, notebook analysis, and written recommendation tell the same story;
- the code remains short enough for a reviewer to follow.

## 16. Leadership presentation outline

Keep the final presentation to six slides.

1. **The observation:** the website says an item is available, but the shelf is empty.
2. **Why it happens:** book inventory can be trapped between returns, reshop, clearance, damage, and incorrect counts.
3. **What the data shows:** availability-gap size, return-to-shelf lag, and store-specific clearance patterns.
4. **The decision method:** availability confidence, likely location, and expected value per labor hour.
5. **Seasonal pilot result:** actions selected for the back-to-campus collection and comparison with baseline policies.
6. **Recommendation:** a limited store pilot, measures to track, risks, and the decision required from leadership.

## 17. Honesty and limitations

The project must not claim that its simulated processes describe Target's internal systems. It should state that the starting observation came from ordinary shopping experience and that the analysis tests a plausible retail mechanism.

Important limitations to acknowledge:

- synthetic outcomes depend on the business rules used to generate them;
- a cancelled order does not prove inventory is missing;
- clearance differences can be intentional and healthy;
- locating inventory does not guarantee a sale;
- labor-time and guest-friction estimates are assumptions;
- a real pilot would require audit results and operational feedback before rollout.

These limitations strengthen the project because they show judgment rather than false certainty.
