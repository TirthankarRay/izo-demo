# iZO IC & SFE Intelligence Platform — User Manual

> **Audience:** IC Analysts, Sales Operations, Compensation Managers, and IC Governance teams  
> **Platform URL:** https://izo-demo.vercel.app/izo-ic-platform.html  
> **Version:** June 2026

---

## 1. Getting Started

### 1.1 Launching the Platform

Open the platform URL in any modern browser (Chrome, Edge, or Firefox). A brief boot splash appears while the in-browser engine compiles — this takes about 300–400 ms and only happens once per page load.

The platform requires no login. All demo data is seeded deterministically, meaning every analyst sees identical numbers for the same company.

### 1.2 Choosing a Company (Persona)

The platform ships with five fictional pharma company scenarios. Each re-skins all KPIs, territories, plans, and narratives to match a specific archetype:

| Company | Archetype | Field Size | Plan Type | Key Story |
|---|---|---|---|---|
| **Vertanis Pharma** | Big Pharma / Primary Care | 812 reps | Goal Attainment | Goal-setting bias against low-baseline territories |
| **Oncovia Therapeutics** | Specialty / Oncology KAM | 124 KAMs | MBO Hybrid (60/40) | Healthy plan; MBO scoring inflation is the watch item |
| **Neurelis Bio** | Launch Biotech / CNS | 96 reps | Rank-Based | Rank plan driving differentiation; 9 territories at zero NBRx |
| **Auralys Rare** | Rare Disease / Account | 38 ADs | Account MBO (milestones) | Lumpy payout; 5 ADs missed milestone by <3 points |
| **Genovex Labs** | Generics / Portfolio GM | 210 reps | GM Commission | Floor payments of $310K/yr to bottom decile |

**To switch companies:** Click the company badge in the top-right of the header, then select a company from the dropdown. All screens, charts, and data instantly re-render for the selected company.

### 1.3 Navigation

The left sidebar organizes all screens into six groups:

| Group | Screens |
|---|---|
| **OVERVIEW** | Command Center, Action Worklist |
| **DIAGNOSE** | IC Health Check, Pay-for-Performance Lab, Goal Setting & Fairness, Territory & SFE, Data Explorer |
| **DESIGN** | Plan Design Studio |
| **EXECUTE** | Field Pulse & Disputes |
| **ASK iZO** | Ask iZO Copilot |
| **PLATFORM** | Token Usage, Data Connectors |
| **GOVERN** | Agent Registry, Governance & Compliance |

**Activity indicators:**
- Orange dot on **Action Worklist** = there are open actions for this company
- Orange dot on **Field Pulse & Disputes** = there are pending HITL approval items

---

## 2. Screen Reference

### 2.1 Command Center

**What it is:** Your always-on IC dashboard. One page tells you whether this cycle is healthy.

**Key elements:**
- **Cycle stage tracker** — shows where you are in the IC cycle (Data Lock → Payroll Feed). The current stage pulses blue.
- **IC Health gauge** — an overall health score from 0–100 with a color-coded band (green ≥ 80, yellow 60–79, red < 60).
- **KPI strip** — territory count, average attainment, total payout, active disputes, and P4P correlation (ρ).
- **Finding cards** — AI-generated narrative findings with severity tags. Each card has:
  - **➕ Action** button → sends a finding to your Action Worklist with one click
  - **"View details →"** link → jumps directly to the relevant diagnostic screen

**Typical use:** Start here at the beginning of every calc cycle. If the health score has dropped or a finding is flagged, navigate directly to the screen indicated in the finding card.

---

### 2.2 Actions & Next Best

**What it is:** Two things in one screen — the platform's ranked recommendations for field leadership (Next Best Actions), and a personal task board tracking every intervention you've created from any screen.

**Next Best Actions (hero panel):**
- The agent stack synthesizes live P4P, goal-fairness, SFE, and dispute signals into ~5–6 ranked recommendations per company, each with a named field-leadership owner (e.g., "Regional Director — West"), urgency, expected impact, AI confidence, talking points, and the exact affected territories (same rows Data Explorer shows)
- **✓ Endorse** — puts the recommendation in the downloadable brief and creates a linked, tracked worklist action automatically. **↩ undo** reverses both (the linked action is removed if untouched)
- **✎ edit points** — rewrite the talking points in your own words; your edits ship in the brief, not the AI's draft
- **✕ dismiss** — remove with an optional reason; logged to the Governance audit trail; restorable
- **🔺 how this was triangulated** — opens a modal showing the 2–3 independent signals (agent, finding, computed value, source datasets) that converged into the recommendation, the convergence rationale, the impact-derivation formula, and the full data lineage. Each signal deep-links to its source analysis. The same signal detail ships in the Field Brief
- **🔎 evidence link** — every recommendation deep-links to the screen it was derived from
- **📥 Field Brief (.xlsx)** — downloads endorsed recommendations as a 3-sheet leadership-ready workbook (Briefing Summary, Recommendations with talking points, Affected Territories). Disabled until you endorse at least one — *nothing reaches leadership without analyst review*

**Action worklist:**
- **KPI strip** — count of Open / In Progress / Done actions for the current company
- **Action table** — sortable list with title, source screen, owner, due date, priority, and status
- **Status chips** — click any status chip to advance it: Open → In Progress → Done → Open
- **Remove** — click the × to delete an action
- **Contested Findings** — a separate table showing all analyses you've formally challenged via the ⚑ Challenge flow, with reviewer and status

**Seeded actions:** Each company starts with 3 pre-seeded actions relevant to its IC story, so the worklist is never empty in a demo.

**Creating actions from other screens:** Every analysis footer across the platform has a **➕ Action** button. You can also create actions from:
- Command Center finding cards (inline ➕ button)
- Data Explorer territory detail drawer

---

### 2.3 IC Health Check

**What it is:** An 8-dimension automated health assessment, equivalent to what a consulting team would deliver as a 6-week quarterly engagement.

**The 8 dimensions:**

| # | Dimension | What it scores |
|---|---|---|
| 1 | Pay-for-Performance | Spearman rank correlation between attainment and payout |
| 2 | Payout Distribution | How spread out payouts are; flags compression or over-dispersion |
| 3 | Payout Curve Design | Whether the curve shape incentivizes the right behaviors |
| 4 | Differentiation | Whether top performers are meaningfully separated from average |
| 5 | Goal Fairness | Whether quotas are systematically biased against any cohort |
| 6 | Budget Compliance | Whether total payout is within plan budget |
| 7 | Plan Complexity | Whether reps can understand and predict their own pay |
| 8 | Competitive Pay | Whether the plan is competitive against market benchmarks |

Each dimension shows a score (0–100), a trend arrow, a finding, and a recommendation. Scores below 60 are flagged red.

**Analysis footer:** Every dimension card has the standard analysis toolbar:
- **🔬 How this was computed** — opens a 5-stage pipeline trace (what data, what query, what compute, what validation, what narrative was generated)
- **⚑ Challenge** — lets you formally contest a score with a rationale; the challenge flows into the Governance audit trail
- **➕ Action** — adds an item to the Worklist
- **👍 / 👎** — feedback with optional tags and comment

---

### 2.4 Pay-for-Performance Lab

**What it is:** Deep-dive diagnostics on whether compensation is actually rewarding performance.

**Key analyses:**

**P4P Correlation**
- Spearman ρ between attainment rank and payout rank across all territories
- Guardrail: ρ ≥ 0.80 (below this, pay is not tracking performance)
- Displays a scatter chart (attainment vs payout), the ρ value, and a narrative

**Quadrant Analysis**
- Territories are classified into 4 quadrants: Aligned / Overpaid / Underpaid / Review
- Flagged territories table shows the rep, attainment, payout%, quadrant, and likely root cause
- Root causes are classified: Legacy guarantee / Windfall account / Quota error

**Decile Curve**
- Bar chart comparing avg attainment by decile vs avg payout% by decile
- Kinks in the curve (where payout doesn't scale with attainment) are auto-flagged

**President's Club Cutline**
- Shows the payout% threshold for top-performer recognition
- Flags territories near the cutline (within ±5 payout points) that could cross with minor adjustments

---

### 2.5 Goal Setting & Fairness

**What it is:** Audit of whether quotas are fair before they cause payout problems.

**Key analyses:**

**Bias Correlations**
- Correlation between quota and: territory baseline volume, territory size (market opportunity), rep tenure
- A correlation above |r| = 0.30 is flagged as a meaningful bias signal
- Displayed as a correlation bar chart with color-coded severity

**Attainment Histogram**
- Distribution of attainment across all territories
- Reference lines: Threshold (payout kicks in), 100% (target), Excellence (accelerator kicks in)
- A left-skewed distribution suggests quotas may be set too high

**Monte Carlo Attainability**
- Simulates 500 attainment draws per territory using the current plan's volatility
- Outputs: probability of hitting threshold, target, and excellence for a "typical" territory
- If P(threshold) < 50%, the plan may be demoralizing even for average performers

**Goal Fairness Score**
- Summary score combining all bias signals
- Cohort breakdown (if applicable) showing attainment disparity by region or other groupings

---

### 2.6 Territory & SFE

**What it is:** Sales Force Effectiveness diagnostics — field activity, targeting quality, and whitespace.

**Key metrics per territory:**
- Call plan adherence (% of call targets met)
- Reach (% of target prescribers called on)
- Frequency (average calls per prescriber per period)
- Tier-A share (% of calls on highest-potential prescribers)
- Workload index (normalized field activity intensity)

**Views:**
- **SFE Heatmap** — territory matrix color-coded by a composite SFE score
- **Targeting Quality** — scatter of SFE score vs attainment, identifying territories with good activity but low results (market problem) vs poor activity with good results (windfall or legacy)
- **Whitespace** — territories with high opportunity but low reach; prime candidates for focus investment

---

### 2.7 Data Explorer

**What it is:** The raw data browser. All 100 territory rows visible, filterable, sortable, and exportable without leaving the platform.

**Filter controls (top bar):**
- **Search** — text search across Rep name, territory, district, region
- **Region** — filter to one of the 5 US regions
- **Quadrant** — show All / Aligned / Overpaid / Underpaid / Review
- **Flagged only** — toggle to show only territories with at least one active flag

**Column views:**
- **IC view** — attainment%, payout%, target incentive, flags
- **SFE view** — calls, call plan adherence, reach, frequency, tier-A share
- **Goals view** — quota, actual, baseline volume, market opportunity, tenure

**Sorting:** Click any column header to sort ascending; click again to sort descending.

**Live summary strip:** As you filter, a strip below the filter bar updates in real time showing rows matching, average attainment, total payout, and flagged count.

**Territory detail drawer:** Click any row to open a full detail panel showing all 12 fields, the territory's quadrant classification, and quick-action buttons:
- **View in P4P Lab** — navigates to the P4P screen filtered to that territory's context
- **➕ Create action** — adds a worklist item pre-filled with the territory name

**Export:** The **📥 Export N rows** button downloads a formatted .xlsx with exactly the rows currently visible (respects all active filters). Useful for sending a focused slice of data to a manager or putting into a QBR deck.

---

### 2.8 Plan Design Studio

**What it is:** A live what-if simulator for plan parameter changes, backed by the Plan Simulator Agent.

**Sliders:**
- **Threshold %** — attainment level where payout begins (e.g., 80% = no pay below 80% attainment)
- **Threshold Pay %** — payout% at the threshold (e.g., 50% of target incentive)
- **Accelerator** — multiplier above 100% attainment (e.g., 2.0× = every 1 point above target pays 2)
- **Excellence %** — attainment level where the extra accelerator kicks in
- **Payout Cap %** — maximum payout as a % of target incentive

**Impact tiles:** Changing any slider instantly updates:
- Cost of plan (annualized payout across the field)
- Budget variance vs current plan
- Expected P4P ρ under the new curve
- % of field expected to hit cap
- Projected Club qualifier count

**Payout curve chart:** A live SVG showing the curve shape. The current plan curve is shown in blue; any slider changes update the preview curve in orange.

**Monte Carlo cost panel:** A histogram of simulated annual cost distribution, showing the P10/P50/P90 cost range and probability of exceeding budget.

**Note:** Slider state is local to your browser session. Navigating away and returning resets sliders to the current plan defaults. (Scenario save/compare is on the Wave 2 roadmap.)

---

### 2.9 Field Pulse & Disputes

**What it is:** Dispute management and HITL (Human-in-the-Loop) approval queue for field inquiries.

**Dispute feed:** Live list of territory-level disputes with:
- Rep name, territory, dispute amount ($)
- Dispute type (calculation error, quota protest, credit dispute, missing SPIFFs)
- Status (Open / Under Review / Resolved / Auto-resolved)
- Sentiment icon (positive / neutral / negative)

**HITL approval queue:** High-value disputes surface in the HITL queue. You review the AI's proposed resolution and either:
- **Approve** — accepts the AI recommendation and marks the dispute resolved
- **Deny** — returns to agent with your override rationale

**Auto-resolution:** Low-value disputes (below the auto-approve threshold) are handled autonomously by the Field Inquiry Agent with a resolution note. You can review the auto-resolution trace.

**Cycle policy controls:** Toggle per-period policies (e.g., dispute window duration, auto-approve threshold) that persist across reloads.

---

### 2.10 Ask iZO Copilot

**What it is:** A conversational interface for IC questions, powered by the IC Copilot Agent.

**Pre-set prompts (click to run):**
1. Why is our P4P correlation below target?
2. Which territories are at risk of missing Club?
3. What's the cost impact of raising the accelerator to 2.5×?
4. Are our goals biased toward high-baseline territories?
5. Show me the top 5 dispute drivers this cycle
6. What would happen to payout if we removed the cap?

Each prompt runs a scripted 4-phase agent trace (PLAN → TOOL USE → REFLECT → ACT) with a typewriter animation, then reveals a structured response with data callouts.

**Interpretation:** The Copilot cites the specific data, analysis, and agent steps behind every answer — click **🔬 How this was computed** to see the full pipeline trace.

---

### 2.11 Agent Registry

**What it is:** Directory of all 11 AI agents that power the platform, their capabilities, HITL configuration, and recent activity.

**For each agent you can see:**
- Agent persona, tools used (Snowflake, IQVIA, Varicent, etc.)
- 4-phase reasoning trace (PLAN / TOOL USE / REFLECT / ACT) — click to expand
- Capabilities list
- HITL configuration: what the agent escalates to humans vs resolves autonomously
- Recent HITL review history (last 3 decisions with reviewer and outcome)

**Why it matters for demos:** This screen answers the "what are these agents actually doing?" question. Every approval gate, data source, and decision boundary is visible here.

---

### 2.12 Token Usage

**What it is:** Per-agent cost metering showing how many LLM tokens each agent consumes, by model tier and flow type.

**Metrics:**
- Input / Output / Total tokens per agent
- Cost estimate (at standard API pricing)
- Model tier: Light (Haiku), Core (Sonnet), Reasoner (Opus)
- Flow breakdown: Autonomous vs HITL (HITL runs incur a ~1.55× multiplier for the human-review reasoning step)

**Summary panel:** Totals across all agents for the current cycle, plus a projection to full-year cost.

---

### 2.13 Data Connectors

**What it is:** Status panel for all data sources feeding the platform — external systems, internal databases, and manual uploads.

**Connector cards:**
- **Snowflake** — IC and sales transaction data warehouse
- **IQVIA Xponent** — prescriber-level demand and market data
- **Varicent ICM** — payout calculation engine and statements
- **Veeva CRM** — sales activity (calls, samples, reach)
- **Veeva Align** — territory alignment and roster management
- **Workday** — HR demographics (used for fairness screening)
- **SAP / Finance** — budget actuals and payroll feed
- And more

Each connector shows health (green / degraded / error), last-sync timestamp, record count, and latency. Degraded connectors show a warning with a **Sync now** button.

**Manual upload zone:** For data not in a connected system, drag-and-drop an Excel file. The platform parses the upload, previews the mapped columns, and queues it for use in analyses.

---

### 2.14 Governance & Compliance

**What it is:** The regulator- and legal-ready layer: parity tracking, fairness cohorts, policy controls, and a full audit trail.

**Tabs:**

**Parity & Fairness**
- Payout parity ratios by gender cohort (80% rule)
- Cohort attainment comparison (senior vs junior, by tenure band)
- Running disparity index with alert threshold

**Fairness Cohorts**
- Table of cohort pairs with payout ratio, 80% rule pass/fail, and recommended action
- Filters by cohort type (gender, tenure, region)

**Governance Policies**
- Toggleable policy controls: dispute auto-approve threshold, shadow-calc parity band, equity review triggers
- Each toggle persists across reloads

**Audit Trail**
- Timestamped log of every significant event: HITL approvals, policy changes, analyst challenges, agent actions
- Live challenges you submit via ⚑ appear here automatically
- Filterable by agent, action type, and date

---

## 3. Key Analyst Workflows

### 3.1 Cycle Start — Health Check Triage
1. Open **Command Center** → read the overall health score and top 3 findings
2. If any finding is red/amber, click **"View details →"** to jump to the relevant screen
3. On the diagnostic screen, review the analysis and HITL queue
4. Create worklist actions for items that need follow-up

### 3.2 Flagging a P4P Outlier
1. Go to **Pay-for-Performance Lab** → Quadrant Analysis
2. Find the flagged territory in the table
3. Click the territory row → opens detail in **Data Explorer** (or use the Explorer directly)
4. Review the territory's full data profile
5. If the flag looks legitimate: **➕ Create action** with owner and due date
6. If you disagree with the AI conclusion: **⚑ Challenge** → enter rationale → the challenge is logged in Governance Audit Trail

### 3.3 Challenging an Analysis
1. Find the analysis you disagree with (any screen)
2. Click **⚑ Challenge** in the analysis footer
3. Enter your rationale in the text box and click **Submit Challenge**
4. The analysis card shows **⚑ Challenged — under review**
5. The challenge appears in **Action Worklist → Contested Findings** and **Governance → Audit Trail**

### 3.4 Simulating a Plan Change
1. Go to **Plan Design Studio**
2. Move sliders to your proposed scenario
3. Watch the impact tiles update — cost, ρ, cap%, Club count
4. If the scenario is worth pursuing: note the parameters, go to **Action Worklist**, create an action to present to IC Council
5. The Plan Simulator Agent trace (**🔬 How this was computed**) documents the methodology for the submission

### 3.5 Exporting a Filtered Dataset
1. Go to **Data Explorer**
2. Apply filters (e.g., Region = Southeast, Quadrant = Overpaid)
3. Click **📥 Export N rows**
4. An .xlsx downloads with just the visible rows

### 3.6 Downloading the Full Analysis Workbook
1. Click **Export Excel** in the top-right header bar
2. An 11-sheet workbook downloads instantly with:
   - Raw territory data (100 rows × 23 columns)
   - All analyses (Health Check, P4P, Goals & Fairness, Plan Design, Territory & SFE, Disputes, Governance)
   - Token usage and Data Connectors summaries
   - A **Read Me** tab explaining the workbook structure

---

## 4. Persistence — What Survives a Reload

The platform stores your session state in the browser's localStorage under the key `izo-ic-state-v1`. The following persist across page reloads **and** company switches:

| Item | Persists? |
|---|---|
| Worklist actions (all companies) | ✅ Yes |
| Challenges (all companies) | ✅ Yes |
| 👍 / 👎 feedback with tags and comments | ✅ Yes |
| Field Pulse HITL decisions | ✅ Yes |
| Governance policy toggles | ✅ Yes |
| Plan Design Studio slider positions | ❌ No (resets on navigation) |
| Copilot conversation history | ❌ No (resets per session) |

**To reset all demo state:** Click the **↺ Reset demo** button in the top-right header. You will be asked to confirm before any data is cleared.

---

## 5. Tips for Demos

- **Switch personas mid-demo** to show that the platform adapts instantly — Vertanis's fairness story is very different from Genovex's commission floor problem
- **Submit a challenge** on a finding, then immediately navigate to **Governance → Audit Trail** to show it appearing live — demonstrates real-time interconnection
- **Create an action** from a Command Center finding, then navigate to the **Worklist** to show it sitting there with the orange indicator — the "platform as workbench, not just dashboard" story
- **Export the workbook** and open it; the 11 sheets show the breadth of analysis behind the UI
- **Open the Agent Registry** and expand any agent's 4-phase trace — shows "AI with glass walls" vs a black box
- **Use the Copilot** with "Why is our P4P correlation below target?" — the animated trace before the answer shows the reasoning process
