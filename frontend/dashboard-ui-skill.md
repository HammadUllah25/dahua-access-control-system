Instructions
Step 1: Define the Audience and Purpose
Answer these questions before designing anything:

Who uses this dashboard? Executive, team manager, analyst, engineer, customer?
What decision does it inform? ("Should we increase marketing spend in the West region?")
How often will they look at it? Real-time (ops), daily, weekly, monthly?
What action can they take? If no action → reconsider whether a dashboard is the right format.
Dashboard archetypes:

Type	Audience	Refresh	KPI Count	Example
Strategic	C-suite, VPs	Weekly/Monthly	3–5	Company health scorecard
Operational	Team leads, managers	Daily	8–15	Sales pipeline dashboard
Analytical	Data analysts	On-demand	Unlimited	Cohort analysis explorer
Real-time monitoring	Engineers, support	Live	10–20	System uptime & error rates
Step 2: Select the Right KPIs
A KPI must be:

Actionable: the viewer can change it based on what they see
Timely: available at the frequency the dashboard refreshes
Comparable: has a target, benchmark, or prior period to compare against
Unambiguous: has one clear definition shared by all stakeholders
KPI selection process:

List 20 metrics the audience cares about
Filter to metrics the audience can act on (eliminate vanity metrics)
Group remaining into 3–5 themes (e.g., Revenue, Customers, Operations, Quality)
Pick 1–3 primary metrics per theme
Define calculation, data source, and owner for each
KPI tiers:

Level 1 (headline): 3–5 KPIs shown large at the top (Total Revenue, MAU, NPS)
Level 2 (supporting): 6–10 charts providing context (by region, by product, trend)
Level 3 (detail): Tables or drill-downs for investigation
Step 3: Information Architecture (Layout Patterns)
F-pattern layout (most common): Users scan top-left → top-right → down the left.

┌─────────────────────────────────────────────────────┐
│  KPI 1        KPI 2        KPI 3        KPI 4       │  ← Headline KPIs
├───────────────────────┬─────────────────────────────┤
│                       │                             │
│  Primary chart        │  Secondary chart            │  ← Primary context
│  (e.g. revenue trend) │  (e.g. by region)           │
│                       │                             │
├───────────────────────┴─────────────────────────────┤
│  Detail chart 1    │  Detail chart 2  │  Table      │  ← Supporting detail
└────────────────────┴──────────────────┴─────────────┘
Z-pattern layout (executive dashboards): Fewer elements, high-level narrative flow.

Grid layout (operational dashboards): Equal-sized tiles arranged in rows.

Step 4: Visual Hierarchy Principles
Size: Larger = more important. Make the most critical KPI card the biggest element.
Position: Top-left corner gets most attention. Put the hero metric there.
Color: Use strong color (blue, orange) for primary data; grey for all context.
Typography: Metric values large (24–32pt), labels small (10–12pt), titles medium (14–16pt).
White space: Empty space is not wasted—it guides the eye and reduces fatigue.
Step 5: Color Coding System
Establish a consistent color language:

🟢 Green: good, on track, above target
🔴 Red: bad, alert, below target
🟡 Yellow/Orange: caution, approaching threshold
🔵 Blue: primary data, neutral information
⬜ Grey: secondary data, prior period, context
Colorblind-safe alternative palette:

Use: #0077BB (blue), #EE7733 (orange), #009988 (teal), #CC3311 (red)
Avoid: pure red + pure green together without texture or label differentiation
Step 6: BI Tool Selection Guide
Tool	Best For	Strengths	Limitations
Tableau	Enterprise BI, complex visualizations	Powerful viz, strong community, drag-and-drop	Expensive, steep learning curve
Power BI	Microsoft-centric orgs, self-service BI	Deep Excel/Azure integration, affordable	Less flexible layout, DAX complexity
Looker	Data-team-driven, engineering-heavy orgs	LookML modeling, governed metrics, Git integration	Requires data engineers, expensive
Grafana	Real-time monitoring, engineering metrics	Live data, alerting, open source	Not for business users, limited chart types
Metabase	Small teams, SQL-first analytics	Open source, easy SQL → dashboard	Limited advanced features
Google Data Studio (Looker Studio)	Google Workspace users, quick sharing	Free, easy to share, Google Sheets integration	Limited transformations, basic visuals
Retool	Operational dashboards with actions	CRUD operations, internal tools	Requires developer to set up
Quick selector:

Startup with small team → Metabase or Looker Studio
Enterprise with existing Microsoft stack → Power BI
Data team building governed metrics layer → Looker
Engineering monitoring → Grafana
Best-in-class viz + large budget → Tableau
Step 7: Dashboard Quality Checklist
Before publishing, verify:

 Every chart has a title stating the insight (not just the metric name)
 Every KPI has a comparison value (vs. target, vs. last period)
 Color coding is consistent throughout
 Date range is clearly labeled and user-controlled
 Filters are at the top and default to the most common view
 All numbers are formatted with appropriate precision (revenue: $1.2M not $1,234,567.89)
 Data source and refresh date are visible in a footer
 Mobile layout tested (if relevant)
Examples
Example 1: Design a Sales Performance Dashboard
Input: "I need a dashboard for our VP of Sales to review weekly. We care about revenue, pipeline health, and team performance."

Audience analysis: VP of Sales — executive level — weekly review — strategic decisions about team resourcing and focus.

KPI selection (Level 1 — headline):

Bookings (ARR) — new closed revenue this week vs target
Pipeline Coverage — pipeline value / quota (target: 3× coverage)
Win Rate — % of deals closed-won (target: 25%)
Deals at Risk — open deals past expected close date
Layout design:

┌────────────────────────────────────────────────────────────────┐
│ FILTER: [Week ▼]  [Region ▼]  [Rep ▼]          Data as of Mon │
├──────────────┬──────────────┬──────────────┬──────────────────┤
│ Bookings     │ Pipeline     │ Win Rate     │ Deals at Risk    │
│ $1.2M        │ 3.4× quota   │ 28%          │ 12 deals         │
│ ▲ 15% vs LW  │ ✅ on track  │ ▲ 3pt vs LW  │ 🔴 $340K at risk │
├──────────────┴──────────────┴──────────────┴──────────────────┤
│ Bookings Trend (12 weeks) ← primary chart, 60% width          │
│                                                                │
├─────────────────────────────┬──────────────────────────────────┤
│ Revenue by Rep (bar chart)  │ Pipeline Stage Funnel            │
├─────────────────────────────┴──────────────────────────────────┤
│ Deal Table: Name | Stage | Value | Expected Close | Days Late  │
└────────────────────────────────────────────────────────────────┘
Color logic:

Green: metric above target
Red: metric below target or "at risk" items
Blue: trend line (primary data)
Grey: prior period comparison line
Tool recommendation: Salesforce Einstein Analytics (if using Salesforce CRM) or Tableau with Salesforce connector. For smaller teams, HubSpot built-in reporting or Metabase connected to CRM database.

Example 2: Design an Engineering Metrics Dashboard
Input: "Engineering team wants a dashboard to track system health, deployment frequency, and incident response."

Audience: Engineering team leads, on-call engineers — daily + real-time use.

KPI selection (DORA Metrics framework):

Deployment Frequency — deploys/week (target: daily)
Lead Time for Changes — PR merge → production (target: < 1 day)
Change Failure Rate — % of deploys causing incidents (target: < 5%)
MTTR (Mean Time to Recovery) — avg incident duration (target: < 1 hour)
Supporting charts:

Error rate by service (last 24h line chart)
P95 API latency by endpoint (heatmap)
Open incidents table with severity and SLA status
Recent deployments log
Tool recommendation: Grafana (connects directly to Prometheus, DataDog, or CloudWatch; native alerting; real-time refresh).

Color coding: Red = SLA breach, Yellow = degraded, Green = healthy, Grey = no data.

Best Practices
Design for the question, not the data—start with "what decision does this enable?" not "what data do I have?"
One dashboard, one audience—don't try to serve executives and analysts with the same view
KPIs need targets: a number without a benchmark is meaningless
"Alert" color (red) loses impact if overused; reserve it for genuine problems
Show the trend, not just the snapshot—a current value without history lacks context
Label data directly on charts when possible rather than relying on legend lookups
Build the mobile version after the desktop version, not as an afterthought
Common Mistakes
Too many KPIs: 20+ metrics creates analysis paralysis, not insight
Vanity metrics: page views, social followers, total registered users (not actionable)
Missing comparison context: showing $1.2M revenue without target or prior period
Inconsistent date filters: one chart shows "last 30 days" while another shows "this month"
Using pie charts for more than 5 segments—switch to a ranked bar chart
Auto-refreshing a dashboard that users need to study calmly—adds cognitive load
Forgetting mobile: 40%+ of dashboard views happen on tablets or phones
Tips & Tricks
Run a "5-second test": show the dashboard to someone for 5 seconds, then ask "what's the most important thing?"—if they can't answer, the hierarchy isn't clear
Use grey as your default color for all secondary data; use color only to highlight what matters
Always include a "last updated" timestamp so users know if data is stale
Dashboard titles should answer the question the dashboard addresses: "Sales Performance — Week of Jan 15" not "Sales Dashboard"
For executive dashboards, start with a written "dashboard narrative" document before building—executives often want a briefing, not a tool to explore