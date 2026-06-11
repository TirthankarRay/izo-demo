# iZO IC & SFE Intelligence Platform — Product Overview

> **Product:** iZO IC & SFE Intelligence  
> **By:** Improzo  
> **Demo:** https://izo-demo.vercel.app/izo-ic-platform.html  
> **Version:** June 2026

---

## What Is It?

iZO IC & SFE Intelligence is an AI-native platform for pharmaceutical Incentive Compensation (IC) and Sales Force Effectiveness (SFE) teams. It replaces the quarterly consulting engagement with a continuously running AI layer: 11 specialized agents work in parallel to monitor plan health, audit payout accuracy, detect fairness problems, and triage field disputes — delivering in minutes what used to take weeks.

The platform is not a dashboard that surfaces data. It is a **workbench** where IC analysts detect problems, investigate root causes, challenge AI conclusions, create remediation actions, and govern the full IC process — all in one place.

---

## The Problem It Solves

A typical enterprise pharmaceutical company runs IC on a quarterly cycle. The process involves:

| Pain point | Current state | iZO state |
|---|---|---|
| Health assessment | 6-week consulting engagement each quarter | Always-on, refreshed on every calc run |
| P4P validation | Manual Excel analysis post-payout | Continuous Spearman ρ monitoring with guardrails |
| Goal fairness | Spot-checked by a single analyst | Automated bias screen (baseline, size, tenure correlations) before goals ship |
| Dispute triage | IC ops team manually reviewing statements | AI recalculates, isolates root cause, drafts resolution; humans approve the dollars |
| Plan modeling | Consultant builds a PowerPoint scenario | Self-serve slider-based simulator with live cost, ρ, and Club impact |
| Audit trail | Excel logs, email chains | Structured, regulator-ready audit trail with full agent lineage |
| Analyst interventions | Email to IC Ops, wait for a ticket | Inline challenge, worklist action, or override — live on the finding |

---

## Platform Capabilities

### 15 Screens

| Screen | Group | Purpose |
|---|---|---|
| Command Center | OVERVIEW | Always-on IC dashboard: health score, cycle stage, top findings, KPI strip |
| Actions & Next Best | OVERVIEW | AI-ranked Next Best Actions for field leadership (endorse / edit / dismiss → downloadable Field Brief) + personal task board + contested findings |
| IC Health Check | DIAGNOSE | 8-dimension plan health scoring with findings and recommendations |
| Pay-for-Performance Lab | DIAGNOSE | Spearman ρ, quadrant analysis, decile curve, Club cutline diagnostics |
| Goal Setting & Fairness | DIAGNOSE | Bias correlations, attainment histogram, Monte Carlo attainability |
| Territory & SFE | DIAGNOSE | Call plan adherence, reach, frequency, targeting quality, whitespace |
| Data Explorer | DIAGNOSE | Sortable/filterable grid over all 100 territories; row detail drawer; filtered export |
| Plan Design Studio | DESIGN | Live payout curve simulator with cost, ρ, and cap impact tiles |
| Field Pulse & Disputes | EXECUTE | Dispute feed, HITL approval queue, auto-resolution theater |
| Ask iZO Copilot | ASK iZO | Conversational IC Q&A with animated agent reasoning traces |
| Model Hub | PLATFORM | Platform-wide foundation-model control plane: 13-model catalog, tier routing, temperature paths |
| Token Usage | PLATFORM | Per-agent LLM cost metering by model tier and flow type |
| Data Connectors | PLATFORM | Data source health, freshness, and manual upload zone |
| Agent Registry | GOVERN | Full directory of all 11 agents: steps, tools, HITL config, recent reviews |
| Governance & Compliance | GOVERN | Parity ratios, fairness cohorts, policy controls, full audit trail |

### 11 AI Agents

| Agent | Persona | Key Capability | HITL Gate |
|---|---|---|---|
| IC Health Check | IC Strategy Consultant | 8-dimension always-on health scoring | Exec report publication |
| P4P Analyst | Compensation Analytics Lead | Spearman ρ, quadrant outliers, windfall detection | Rep-level overpay tags |
| Goal Setting | Quota & Goal Strategist | Opportunity-weighted goals, bias detection, Monte Carlo | Field publication of goals |
| Plan Simulator | Plan Design Modeler | Curve modeling, cost forecast, what-if shocks | IC Council submission |
| Payout Auditor | Shadow-Calc Engineer | BPS-level shadow recalculation vs vendor | Payroll feed sign-off |
| Fairness & Compliance | IC Governance Officer | 80% rule, disparate-impact screens, audit custody | All fairness findings → Legal |
| Field Inquiry | IC Help-Desk Analyst | Dispute triage, statement recalc, auto-resolution | Adjustments > $1,000 |
| SFE Intelligence | Field Intelligence Analyst | Call quality scoring, whitespace, targeting efficiency | — |
| IC Copilot | IC Advisor | Conversational Q&A with data grounding | — |
| Territory Alignment | Territory Design Lead | Workload balancing, whitespace optimization | Alignment publication |
| Executive Reporting | Analytics Storyteller | Narrative synthesis, exec deck data package | Exec report publication |

### 5 Demo Company Personas

Each persona completely re-skins data, KPIs, plan design, and narrative to show a different IC archetype:

| Persona | Industry Segment | Field Size | Plan Archetype | IC Story |
|---|---|---|---|---|
| Vertanis Pharma | Big Pharma / Primary Care | 812 reps | Goal Attainment (quarterly) | Goal bias suppressing payout for low-baseline territories |
| Oncovia Therapeutics | Specialty / Oncology KAM | 124 KAMs | MBO Hybrid 60/40 (quarterly) | Healthy plan; MBO scoring inflation is the watch item |
| Neurelis Bio | Launch Biotech / CNS | 96 reps | Rank-Based (monthly) | Differentiation by design; 9 territories at zero NBRx activation |
| Auralys Rare | Rare Disease / Account | 38 Account Directors | Account MBO / Milestones (semi-annual) | Cliff-heavy payouts; 5 ADs missed milestone by <3 points |
| Genovex Labs | Generics / Portfolio GM | 210 reps | GM Commission (monthly) | Floor payments of $310K/yr to non-productive bottom decile |

---

## Analyst Intervention Model

The platform is built around a closed-loop intervention model. Every analysis finding supports four analyst actions without leaving the screen:

| Action | What it does |
|---|---|
| **🔬 How this was computed** | Opens a 5-stage pipeline trace (INPUTS → QUERY → COMPUTE → VALIDATE → NARRATE) showing the full AI reasoning chain |
| **⚑ Challenge** | Formal override request with mandatory rationale; logged to Governance Audit Trail as a HITL event; card shows "⚑ Challenged — under review" |
| **➕ Action** | Creates a worklist item with owner, due date, priority; lands on Actions & Next Best with orange indicator; survives page reload |
| **⚡ Endorse / dismiss NBA** | The platform proposes ranked Next Best Actions for field leadership; the analyst endorses (auto-creates a linked action), edits the talking points, or dismisses with a reason — only endorsed items reach the downloadable Field Leadership Brief |
| **👍 / 👎** | Sentiment feedback with tag chips (e.g., "wrong data", "good catch") and free-text comment; feeds model improvement logging |

This model means an analyst who disagrees with an AI conclusion has a structured path to contest it, not just a note in a spreadsheet.

---

## Persistence & State

Analyst interventions survive browser reloads and persona switches via localStorage (`izo-ic-state-v1`):

- Worklist actions and close-out outcomes (all companies)
- Next Best Action curation — endorsements, dismissal reasons, edited talking points (all companies)
- Challenges with rationale and IC Council verdicts (all companies)
- Feedback with tags and comments (all companies)
- Notification feed
- HITL dispute decisions
- Model Hub routing and temperature settings
- Governance policy toggles

The **↺ Reset demo** button in the header wipes all state (with a confirmation prompt) for a clean demo start.

---

## Excel Export

The **Export Excel** button in the header generates an 11-sheet workbook in the browser (no server round-trip) using SheetJS:

| Sheet | Contents |
|---|---|
| Read Me | Metadata, legend, how to use |
| Raw Data - Territories | 100 rows × 23 columns |
| 1 Health Check | 8-dimension scores, findings, recommendations |
| 2 P4P Analysis | ρ, outlier table, decile curve, Club analysis |
| 3 Goals & Fairness | Bias correlations, attainment histogram, Monte Carlo |
| 4 Plan Design | Plan parameters + payout curve lookup table |
| 5 Territory & SFE | KPI matrix, heatmap, targeting, whitespace, workload |
| 6 Disputes | All disputes with resolution status |
| 7 Governance | Parity ratios, fairness cohorts, audit trail |
| 8 Token Usage | Per-agent costs by tier and flow |
| 9 Data Connectors | Source health and freshness |

The Data Explorer also exports a filtered .xlsx containing only the rows matching active filters — useful for focused manager reviews or QBR prep.

**Field Leadership Brief:** Actions & Next Best has its own download — a 3-sheet workbook (Briefing Summary, Recommendations with talking points, Affected Territories) containing only the recommendations the analyst has endorsed. It is the artifact an analyst walks into a leadership meeting with; territory rows match Data Explorer exactly.

---

## Technical Stack (for IT / Procurement)

| Requirement | Answer |
|---|---|
| **Infrastructure** | None — single HTML file, served as static asset |
| **Backend / Database** | None — all computation is client-side |
| **Authentication** | None in demo; production deployment would add IdP |
| **Data** | All demo data is synthetic / seeded; no PHI, no real company data |
| **External calls** | Google Fonts CDN only (for Inter and JetBrains Mono fonts) |
| **Browser support** | Chrome 90+, Edge 90+, Firefox 90+, Safari 15+ |
| **Offline capable** | Partial — works offline after first load (fonts may not load) |
| **File size** | ~370KB single file |
| **Mobile** | Minimum viewport 1060px; optimized for laptop/desktop |

---

## Roadmap (Approved, Not Yet Built)

**Wave 2 — Wow Moments**
- **C2** Real Excel upload round-trip: SheetJS reads uploaded .xlsx → column-mapping preview → analyses recompute with new quotas
- **B1** Guardrail tuning panel: edit live thresholds (ρ guardrail, rank-gap band, bias trigger) and watch analyses re-flag in real time
- **B3** Scenario save & compare: name and persist Plan Design Studio scenarios, compare 2–3 side by side
- **A4** Write-back action theater: after HITL approval, staged "Push to Varicent / Queue re-run / Send comms" buttons
- **B2** Goal re-weighting preview: apply opportunity re-weighting and see bias correlations flip side by side

**Wave 3 — Polish**
- **D2** Shareable deep links via URL hash routing (#vertanis/p4p)
- **B4** Watchlist subscriptions (alert when ρ < threshold, budget > X%)
- **D1** Pinned notes / annotations on analyses
- **E2/E3** Feedback and worklist items in the Excel export
- **D4-lite** Executive summary print-PDF via print stylesheet

**Deliberately Out of Scope (demo)**
- C4 Ad-hoc SQL (use Snowflake/Hex deep links instead)
- D3 Team discussion threads (use Slack connector mock + "Send to #ic-ops" button)
- D5 Scheduled email digests (mock toggle; production is n8n/Power Automate)
- E4 Auth/roles (cosmetic role-switcher only if a prospect asks)
- C3 Multi-period trends (high data-model complexity; defer until prospect demands it)
