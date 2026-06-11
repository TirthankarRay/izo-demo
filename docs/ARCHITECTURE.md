# iZO IC & SFE Intelligence Platform — Architecture Reference

> **Audience:** Developers extending or maintaining the platform  
> **File:** `izo-ic-platform.html` (~315KB)  
> **Version:** June 2026

---

## 1. Design Constraints

The platform is intentionally a **single self-contained HTML file** with no build step, no Node.js, no bundler, and no backend. Everything runs in the browser.

**Rationale:**
- Zero-friction distribution (email the file, open in any browser)
- Trivial Vercel deployment — push the file, done
- No CORS, auth, or API infrastructure needed for a demo
- Babel-standalone compiles JSX in-browser on first load

**Trade-offs accepted:**
- Babel compile adds ~300–400 ms on first page load (masked by a boot splash)
- No tree-shaking; all library code is loaded even if unused
- File size cap: the babel block should stay below ~320KB to keep compile time acceptable
- No hot module replacement; edit → refresh is the dev loop

---

## 2. Tech Stack

| Layer | Library | Version | CDN |
|---|---|---|---|
| UI Framework | React | 18.2.0 | cdnjs |
| DOM Renderer | ReactDOM | 18.2.0 | cdnjs |
| JSX Compiler | babel-standalone | 7.23.9 | cdnjs |
| Excel Export | SheetJS (xlsx) | 0.18.5 | cdnjs |
| Fonts | Google Fonts (Inter, JetBrains Mono) | — | fonts.googleapis.com |

The HTML `<head>` loads all four CDN scripts before the babel block. SheetJS is passed into the babel scope via `window.XLSX`.

---

## 3. File Structure

The entire application is one file. Code is organized into 27 **sentinel-delimited sections**:

```
/* ▓▓ SECTION:NAME ▓▓ */
...code...
/* ▓▓ END:NAME ▓▓ */
```

Sentinels serve as navigational landmarks — jump to `SECTION:SCREEN-P4P` to find the P4P screen, `SECTION:EXPORT` for the workbook builder, etc.

### Section map

| Section | Contents |
|---|---|
| `TOKENS` | Design tokens (`C` object), phase colors/icons, fmt helpers |
| `RNG` | Seeded RNG: `hashStr`, `mulberry32`, `gauss`, `pick` |
| `PERSONAS` | 5 pharma company persona objects |
| `STATS` | Pure math: `rank`, `spearman`, `pearson`, `percentile`, `mean`, `normCdf`, `binHistogram`, `payoutCurve`, `costOfPlan`, `monteCarlo` |
| `DATAGEN` | `buildPersonaData(pid)` → 100-row territory dataset + aggregates |
| `AGENTS` | 11 agent definitions (persona, tools, 4-phase steps, HITL config) |
| `COPILOT-SCRIPTS` | 6 scripted copilot prompt responses (typewriter-animated) |
| `CHARTS` | SVG chart components: `BarChart`, `ScatterChart`, `LineChart`, `GaugeChart`, `SparkLine`, `ChartBox` |
| `UI` | Shared UI primitives: `Card`, `Badge`, `KpiCard`, `Tag`, `Pill`, `Row` |
| `SHELL` | Navigation (`NAV` constant), `Sidebar`, `PersonaSelector`, `TopBar`, `TraceModal`, `AnalysisActions` |
| `OBSERVE` | Persistence layer, feedback/challenge/action stores, `AnalysisActions` component |
| `SCREEN-COMMAND` | Command Center screen |
| `SCREEN-HEALTH` | IC Health Check screen |
| `SCREEN-P4P` | Pay-for-Performance Lab screen |
| `SCREEN-GOALS` | Goal Setting & Fairness screen |
| `SCREEN-STUDIO` | Plan Design Studio screen |
| `SCREEN-SFE` | Territory & SFE screen |
| `SCREEN-PULSE` | Field Pulse & Disputes screen |
| `SCREEN-COPILOT` | Ask iZO Copilot screen |
| `SCREEN-REGISTRY` | Agent Registry screen |
| `SCREEN-GOVERN` | Governance & Compliance screen |
| `SCREEN-TOKENS` | Token Usage screen |
| `SCREEN-CONNECTORS` | Data Connectors screen |
| `SCREEN-WORKLIST` | Action Worklist screen |
| `SCREEN-EXPLORER` | Data Explorer screen |
| `EXPORT` | `buildWorkbook(persona, data)` → SheetJS workbook |
| `APP` | Root `App` component + `ReactDOM.createRoot` mount |

---

## 4. Data Architecture

### 4.1 Seeded Deterministic RNG

All demo data is generated at render time from a seeded pseudo-random number generator. The seed is persona-specific:

```javascript
const rng = mulberry32(hashStr("izo-ic-" + pid));
```

The `mulberry32` function implements a 32-bit state machine. The `hashStr` function converts the persona ID string into a seed integer via the djb2-variant hash.

**Consequence:** Every page load, every persona switch, every browser, every analyst sees **identical numbers** for the same persona. Math.random() is never used for data — only for animation jitter.

**Draw order matters.** Every call to `rng()` advances the state. The 100 territory rows are generated in a fixed loop, and within each row the fields are drawn in a fixed order. Inserting a new `rng()` call anywhere in `buildPersonaData` will shift all subsequent numbers. When adding new data fields, always append to the end of the per-row draw sequence.

### 4.2 Persona Data Model

Each persona is a plain JavaScript object defined in `SECTION:PERSONAS`:

```javascript
{
  id: "vertanis",           // string, used as key everywhere
  name: "Vertanis Pharma",  // display name
  initials: "VP",           // 2-char avatar
  type: "Big Pharma — Primary Care",  // long type label
  typeShort: "Primary Care",
  reps: 812,                // headcount for cost calculations
  roleLabel: "Sales Reps",
  products: ["Cardiozen","Lipidra"],
  metric: "TRx",
  attainLabel: "TRx Attainment",
  color: "#1E82BD",         // accent color for charts/avatars
  launch: false,            // affects some narrative text
  plan: {
    archetype: "goalAttainment", // dispatches payoutCurve()
    freq: "Quarterly",
    threshold: 90,          // attainment% where payout begins
    thresholdPay: 50,       // payout% at threshold
    accelerator: 2.0,       // multiplier above 100%
    excellence: 110,        // attainment% for extra kicker
    cap: 200,               // max payout%
    ti: 18500,              // target incentive $ per rep per period
    // archetype-specific fields vary:
    // mboHybrid: mboWeight
    // rankBased: sigmaPct, tiers[]
    // accountMBO: base, milestones[]
    // gmCommission: floor, rate
  },
  sigma: 0.11,              // attainment std dev for MC simulation
  bias: "lowBaseline",      // "none" | "lowBaseline" | "opportunity"
  lumpy: false,             // if true, adds random large swings (Auralys)
  cycleStage: 4,            // index into CYCLE_STAGES array
  payNoise: 30,             // payout noise magnitude for P4P correlation
  story: "...",             // narrative shown on Command Center
  nudge: {                  // health score adjustments per dimension
    p4p, dist, curve, diff, fair, budget, cmplx, comp
  }
}
```

### 4.3 getData(pid) — the Derived Data Object

`getData(pid)` calls `buildPersonaData(pid)` and caches the result (keyed by pid, so persona switches don't re-run the generator if the same persona is re-selected). Returns:

```javascript
{
  rows: [...],        // 100 territory row objects
  cycle: {...},       // cycle metadata (period label, stage, days remaining)
  overall: 72,        // IC health score (0–100)
  health: {...},      // 8 dimension scores + findings
  rho: 0.87,          // Spearman ρ (pay-for-performance correlation)
  flagged: [...],     // subset of rows with P4P flags
  mc: {...},          // Monte Carlo results
  biasCorr: {...},    // Pearson correlations (quota vs baseline/size/tenure)
  sfe: {...},         // SFE aggregates
  disputes: [...],    // dispute list
  tokens: {...},      // token usage per agent
  connectors: [...],  // connector health status
  ...
}
```

### 4.4 Payout Curve Dispatch

`payoutCurve(plan)` is a factory — it takes the plan object and returns a function `(attainment%) → payout%`:

| Archetype | Logic |
|---|---|
| `goalAttainment` | Threshold → linear → accelerator → excellence kicker → cap |
| `rankBased` | Normal-CDF maps attainment to a percentile, then looks up a 10-tier payout table |
| `gmCommission` | Linear with floor and cap: `max(floor, min(cap, att * rate))` |
| `accountMBO` | Base pay + milestone increments accumulate as attainment crosses each milestone |
| `mboHybrid` | Weighted average of MBO component and goal-attainment component |

---

## 5. Persistence Layer (SECTION:OBSERVE)

```javascript
const PERSIST_KEY = "izo-ic-state-v1";

// Loaded once on module init (survives reload)
const _P = (() => {
  try { return JSON.parse(localStorage.getItem(PERSIST_KEY)) || {}; }
  catch(e) { return {}; }
})();

// Write helper — updates _P in memory and flushes to localStorage
const persist = (k, v) => {
  _P[k] = v;
  try { localStorage.setItem(PERSIST_KEY, JSON.stringify(_P)); }
  catch(e) {}  // quota exceeded — silently fail
};

// Reset — wipes localStorage entry and hard-reloads
const resetDemoState = () => {
  try { localStorage.removeItem(PERSIST_KEY); } catch(e) {}
  window.location.reload();
};
```

**Three stores** initialized from `_P` at startup:

```javascript
const FEEDBACK_STORE  = _P.feedback   || {};   // keyed by analysisId
const CHALLENGE_STORE = _P.challenges || {};   // keyed by analysisId
const ACTION_STORE    = _P.actions    || [];   // flat array, newest first
```

**Mutation pattern:** Stores are mutated in place, then `persist(key, store)` flushes. React re-renders are triggered by local component state — the stores themselves are not reactive. Components that read stores use `useState` with the store as initial value, then call their own setter when they mutate.

---

## 6. Component Architecture

### 6.1 App Root

```
App
├── Sidebar (persona, nav state)
├── TopBar (persona selector, export button, reset button)
└── <Screen key={personaId+view} persona={...} data={...} onNav={...}>
    └── (one of 14 screen components)
```

**Key design choice: `key={personaId+view}`**  
Every screen component is unmounted and remounted on persona switch OR navigation. This guarantees all local animation and UI state is cleared — no stale countdown timers, half-animated charts, or mid-type copilot sessions from the previous screen.  

**Trade-off:** Plan Design Studio sliders reset when you navigate away. This is the most user-visible consequence; adding scenario persistence (Wave 2 B3) would require lifting slider state to `App`.

### 6.2 AnalysisActions Component

The shared footer that appears on every analysis card across all screens:

```javascript
const AnalysisActions = ({
  persona,       // current persona object
  id,            // unique analysis ID (e.g., "p4p-rho")
  agent,         // agent name string
  title,         // analysis title for display
  method,        // short description of method
  datasets,      // array of data source names
  query,         // query description for trace modal
  checks,        // validation checks run
  computeNote,   // extra compute notes
  scope,         // scope description
  compact,       // if true, renders inline rather than block
  noTrace        // if true, hides "🔬 How computed" link
}) => { ... }
```

Renders four affordances:
1. **🔬 How this was computed** → opens `TraceModal`
2. **⚑ Challenge** → inline form → persists to `CHALLENGE_STORE`
3. **➕ Action** → inline form → calls `addAction()` → persists to `ACTION_STORE`
4. **👍 / 👎** → tag chip selector + comment input → persists to `FEEDBACK_STORE`

### 6.3 TraceModal

A full-screen overlay showing a 5-stage pipeline trace:

| Stage | What it shows |
|---|---|
| **INPUTS** | Data sources and fields used |
| **QUERY** | How the data was queried/joined |
| **COMPUTE** | The statistical method or calculation |
| **VALIDATE** | Guardrails and sanity checks applied |
| **NARRATE** | How the narrative was generated from findings |

### 6.4 Chart Components (SECTION:CHARTS)

All charts are **pure SVG**, stateless, no external charting library:

| Component | Usage |
|---|---|
| `BarChart` | Decile bars, histogram, token usage |
| `ScatterChart` | Attainment vs payout scatter (P4P) |
| `LineChart` | Trend lines, payout curves |
| `GaugeChart` | IC health score gauge |
| `SparkLine` | Inline trend in KPI cards |
| `ChartBox` | Wrapper with title, subtitle, tooltip container |

All charts use a fixed `viewBox` (no measured DOM dimensions) and accept data as plain arrays/objects. Tooltips are rendered in a portal div via the `ChartBox` wrapper.

---

## 7. Excel Export (SECTION:EXPORT)

`buildWorkbook(persona, data)` produces an SheetJS workbook with 11 named sheets:

| # | Sheet Name | Contents |
|---|---|---|
| 0 | Read Me | Metadata, date, persona, how to use the workbook |
| 1 | Raw Data - Territories | 100 rows × 23 columns (all territory fields) |
| 2 | 1 Health Check | 8 dimension scores, findings, recommendations |
| 3 | 2 P4P Analysis | ρ, flagged territory table, decile analysis, Club |
| 4 | 3 Goals & Fairness | Bias correlations, histogram, Monte Carlo |
| 5 | 4 Plan Design | Plan parameters, payout curve table |
| 6 | 5 Territory & SFE | KPIs, heatmap, targeting, whitespace, workload |
| 7 | 6 Disputes | All disputes with status and resolution |
| 8 | 7 Governance | Parity ratios, fairness cohorts, audit trail |
| 9 | 8 Token Usage | Per-agent token counts and cost |
| 10 | 9 Data Connectors | Connector health, last sync, record counts |

**Helper functions:**
- `xlsSheet(rows)` — converts an array of `{label, value}` objects to a SheetJS 2-column sheet
- `buildGovData(persona)` — shared between `SCREEN-GOVERN` and the export; ensures identical numbers in both

**Download trigger:** TopBar's "Export Excel" button calls `downloadExcel(persona, data)` which calls `buildWorkbook`, encodes to base64 blob, and triggers an `<a download>` click.

---

## 8. Agent Definitions (SECTION:AGENTS)

Each of the 11 agents is a plain object conforming to the same schema as the `izo-agents-demo.html` registry:

```javascript
{
  id: "health",
  name: "IC Health Check Agent",
  persona: "IC Strategy Consultant",
  icon: "🩺",
  color: "#1E82BD",
  status: "Active",
  tasks: 96,           // tasks run (for display)
  success: 99.1,       // success rate %
  desc: "...",
  tools: ["Snowflake","Varicent ICM","IQVIA Xponent","Power BI"],
  capabilities: [...],
  hitlConfig: {
    approvalGate: "ACT",   // which phase requires human approval
    escalationThreshold: "Medium",
    requiresHumanFor: [...],
    recentReviews: [...]
  },
  steps: [
    { phase: "PLAN", title: "...", desc: "...", actions: [...], color: "..." },
    { phase: "TOOL USE", ... },
    { phase: "REFLECT", ... },
    { phase: "ACT", ... }
  ]
}
```

**The 11 agents:**
1. `health` — IC Health Check Agent
2. `p4p` — P4P Analyst Agent
3. `goal` — Goal Setting Agent
4. `simulator` — Plan Simulator Agent
5. `auditor` — Payout Auditor Agent
6. `fairness` — Fairness & Compliance Agent
7. `inquiry` — Field Inquiry Agent
8. `sfe` — SFE Intelligence Agent
9. `copilot` — IC Copilot Agent
10. `alignment` — Territory Alignment Agent
11. `reporting` — Executive Reporting Agent

---

## 9. Adding a New Screen

1. **Create the component** in a new sentinel section:
   ```javascript
   /* ▓▓ SECTION:SCREEN-MYSCREEN ▓▓ */
   function MyScreen({ persona, data, onNav }) {
     return <div>...</div>;
   }
   /* ▓▓ END:SCREEN-MYSCREEN ▓▓ */
   ```

2. **Register it in the NAV constant** (`SECTION:SHELL`):
   ```javascript
   { id: "myscreen", icon: "🔧", label: "My Screen" }
   ```
   Add it under the appropriate group.

3. **Register it in the SCREENS map** (`SECTION:APP`):
   ```javascript
   const SCREENS = {
     ...
     myscreen: MyScreen,
   };
   ```

4. **Verify:** Run `node C:\Users\TirthankarRay\izo-verify\verify.js` — it checks sentinel pairing, script tag count, and babel transform.

---

## 10. Development Workflow

### Local dev server
```powershell
# Start local server (port 8642)
npx -y http-server C:\Users\TirthankarRay\izo-demo -p 8642
# Open: http://localhost:8642/izo-ic-platform.html
```

### Edit → verify → deploy
```powershell
# 1. Edit the file
# 2. Verify
node C:\Users\TirthankarRay\izo-verify\verify.js
# 3. Commit
git add izo-ic-platform.html
git commit -m "feat: ..."
git push
# 4. Deploy to production
vercel deploy --prod --yes
```

The verifier checks:
- Exactly 5 `</script>` closing tags (4 CDN + 1 babel block)
- All `SECTION:X` sentinels are paired with `END:X` in the same order
- The babel block transforms without errors
- No mojibake (double-encoded UTF-8 artifacts)

### Regenerate Excel sample files
```powershell
node C:\Users\TirthankarRay\izo-verify\gen-excel.js
# Output: C:\Users\TirthankarRay\OneDrive - Improzo\Desktop\iZO-IC-Excel-Exports\
```

---

## 11. Key Invariants

| Invariant | Why |
|---|---|
| Never call `Math.random()` in data generation | Breaks determinism; use `rng()` from the seeded generator |
| Always append new `rng()` calls to the end of per-row draw sequences | Earlier calls shift all subsequent draws |
| `key={personaId+view}` in App ensures screen remount | Screen components must not rely on local state surviving navigation |
| `buildGovData(persona)` must be called for both SCREEN-GOVERN and EXPORT | They must produce identical governance numbers |
| `TRAIL_AGENTS` is a module-level constant | Both Governance screen and live challenges reference it; local scoping breaks the audit trail |
| `addAction()` must call `persist("actions", ACTION_STORE)` | Mutations without persist are lost on reload |
| SheetJS is accessed as `window.XLSX` inside the babel block | The CDN script attaches to window; the babel scope doesn't have it as a local import |

---

## 12. File Size Budget

| Component | Approx. size |
|---|---|
| React + ReactDOM CDN | ~50KB (gzip) |
| babel-standalone CDN | ~400KB (gzip) |
| SheetJS CDN | ~400KB (gzip) |
| **izo-ic-platform.html** | **~315KB** |
| Babel block (JSX source) | ~304KB |
| Compiled output (in-browser) | ~900KB |

The babel block compiles in ~300–400 ms on a modern laptop. The boot splash masks this. Remaining headroom before noticeable compile-time degradation: ~50–80KB of JSX.

Items that would push past the limit:
- C3 multi-period (adds ~50KB of data model + chart code)
- A large charting library (Chart.js, D3) — avoid; hand-rolled SVG is sufficient

---

## 13. Deployment

The repo is linked to Vercel project `izo-demo` (account `tirthankarr-3947`).

```powershell
cd C:\Users\TirthankarRay\izo-demo
vercel deploy --prod --yes
```

- **Production URL:** https://izo-demo.vercel.app/izo-ic-platform.html
- **Preview URLs:** Protected by Vercel deployment protection (require team login)
- **No env vars, no build step, no framework config** — Vercel serves static HTML directly
- **Repo:** github.com/TirthankarRay/izo-demo (branch: `claude/loving-dijkstra-ddwvxe`)
