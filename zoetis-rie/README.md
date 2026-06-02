# Zoetis Retail Intelligence Engine (RIE)

A market-intelligence platform that estimates **market share for animal-health
brands** across veterinary, retail and e-commerce channels by **triangulating
multiple data sources**, ships every number with a **95% confidence band**, runs
an **automated QC workflow** before any data is "delivered," generates
**plain-language insight narratives**, and includes a **data-procurement decision
tool** that scores e-commerce vendors and models cost.

This is a **Phase-1 MVP demo**. It is complete enough to walk a client through
today, but built with a clean separation between the synthetic-data layer and
the analytics/UI layers, so the data layer can later be swapped for real vendor
feeds (CIQ, Stackline, Nielsen) **without rewriting the engine**.

> **Everything is synthetic.** No real Zoetis, CIQ, Stackline or Nielsen data.
> No external calls, no auth, no secrets — it runs fully offline.

---

## The four capabilities

| # | Capability | Where it lives |
|---|------------|----------------|
| 1 | **Market Share + Triangulation + Channel View** — coverage-weighted estimates, 95% bands, brand leaderboard, channel split & trend | `core/engine.py`, `core/analytics.py`, pages *Market Share* + *Channels* |
| 2 | **QC Scorecard + Data Validation** — 5-stage validation, flagged-record drill-down, quality score, delivery gating | `core/qc_engine.py`, page *QC Scorecard* |
| 3 | **Procurement Decision Tool + Cost Model** — live-reweightable vendor scoring, pass-through cost model | `core/scoring.py`, page *Procurement* |
| 4 | **Insight Narratives + Confidence Intervals** — deterministic, confidence-aware prose | `core/narratives.py`, page *Insights* |

---

## Run it

### Option A — Docker (one command)

```bash
docker compose up --build
```

Then open **http://localhost:5173**. The API is at **http://localhost:8000**
(interactive docs at **http://localhost:8000/docs**).

### Option B — Local (Make)

```bash
make install     # install backend + frontend deps
make test        # run the backend test suite (34 tests)
make backend     # terminal 1: FastAPI on :8000
make frontend    # terminal 2: Vite dev server on :5173 (proxies /api -> :8000)
```

### Option C — Local (manual)

```bash
# Backend
cd backend
pip install -r requirements.txt
python -m app.data.generator --seed 42 --issues 30   # (optional; auto-runs if missing)
uvicorn app.main:app --reload --port 8000

# Frontend (separate terminal)
cd frontend
npm install
npm run dev        # http://localhost:5173
```

---

## Architecture

```
zoetis-rie/
  backend/                         # FastAPI + Python (stdlib-only analytics)
    app/
      main.py                      # app, CORS, router mount, health, catalog
      api/                         # one route module per capability
        market_share.py  triangulation.py  channel.py
        qc.py            procurement.py     insights.py
      core/
        engine.py                  # PURE triangulation + CI math (no I/O)
        analytics.py               # orchestration: provider + engine -> tables
        qc_engine.py               # 5-stage validation (pure stage functions)
        scoring.py                 # vendor scoring + cost model (pure)
        narratives.py              # template-based insight generation (pure)
      data/
        provider.py                # ★ DATA ABSTRACTION LAYER — the seam
        generator.py               # synthetic data generator (writes seeds)
        seeds/                     # committed --seed 42 dataset (CSV + JSON)
      models/schemas.py            # pydantic request/response contracts
    tests/                         # pytest: engine math, QC rules, scoring, API
  frontend/                        # React (Vite) + TypeScript + Recharts
    src/
      pages/                       # one page per capability + dashboard
      components/                  # cards, charts, confidence-band visual, filters
      lib/{api.ts,types.ts}        # typed client + mirrored contracts
  docker-compose.yml               # one-command spin-up
```

### The critical design rule

> **All data access goes through `data/provider.py`.** The analytics engine and
> API never read seed files directly — they call the provider.

```
   API routes ──▶ analytics ──▶ engine.py        (pure math; no I/O)
                      │
                      └────────▶ provider.py ──▶ seeds/ (today)
                                     ▲
                                     └────────── real vendor connectors (tomorrow)
```

The provider owns the messy, vendor-shaped concerns (SKU normalization, mapping
raw rows to canonical brands, geography derivation, exposing source coverage).
The engine only ever sees clean numbers, so it is identical whether the inputs
are synthetic or real.

---

## How the numbers are built

**Triangulation** (`engine.py`). Each source observes
`observed = true_sales × coverage × bias × (1 + noise)` for the one channel it
covers. We recover an estimate by grossing each source up by its coverage and
blending the covering sources, weighted by coverage:

```
point = Σ(observed_s) / Σ(coverage_s)        # coverage-weighted mean of observed/coverage
```

- **E-commerce** blends **CIQ + Stackline**.
- **Retail** comes from the **Nielsen** scanner.
- **Veterinary** comes from the **Zoetis internal** feed.

**95% confidence band.** Built from two ingredients: **cross-source dispersion**
(how much the grossed-up sources disagree) and the **coverage gap** (how much of
the channel the combined sources miss), combined in quadrature with a
single-source penalty. Narrow band when sources agree and coverage is high; wide
band otherwise. This is validated in tests: triangulated estimates land within
**7%** of ground truth at national grain, and the band covers the truth ≥80% of
the time.

**QC engine** (`qc_engine.py`) — five pure, testable stages:

1. **File Validation** — schema, completeness (grid gaps = missing rows), row counts vs prior period.
2. **Statistical Anomaly Detection** — IQR + z-score outliers, period-over-period limits.
3. **Hierarchy Checks** — SKU→brand mapping (unmapped SKUs), channel + geography rollups.
4. **KPI Validation** — shares sum to 100%, sales reconcile to control totals, CI bounds sane.
5. **Automated Reporting** — assemble the delivery package + pass/fail summary.

Delivery is **blocked** until every stage is PASS or flags are explicitly
resolved (the *Resolve flags & approve delivery* button simulates this).

**Procurement** (`scoring.py`) — six criteria (SKU granularity, retailer
coverage, refresh frequency, historical depth, cost efficiency, integration
ease) scored 0–100 per vendor; the **weights are user-adjustable** and the winner
re-ranks live. The **cost model** makes the *pass-through, zero-markup* principle
explicit: vendor data is billed at cost; Improzo services are priced separately
by tier (figures are clearly-labelled placeholders).

**Narratives** (`narratives.py`) — deterministic string templates filled from the
computed numbers (no LLM). Conclusion first, evidence second, every narrative
cites the confidence band and flags low-confidence estimates.

---

## Synthetic data generator

Deterministic and reproducible:

```bash
cd backend
python -m app.data.generator --seed 42 --issues 30   # default committed set
python -m app.data.generator --random                # use system entropy for variety
python -m app.data.generator --seed 7 --issues 50    # different seed / more outliers
```

It builds a hidden **ground-truth** table, then derives four feeds with
deliberately different coverage, noise and channel bias:

| Feed | Channel | Coverage | History | Character |
|------|---------|----------|---------|-----------|
| `ciq_ecommerce` | E-commerce | ~82% | 24 mo | history-rich |
| `stackline_ecommerce` | E-commerce | ~88% | 18 mo | SKU-granular, recent |
| `nielsen_scanner` | Retail | ~91% | 24 mo | mass/grocery/drug/club |
| `zoetis_vet_internal` | Veterinary | ~96% | 24 mo | internal |

It also injects **messy-on-purpose** defects so QC has real work to do
(configurable count): statistical outliers, unmapped SKUs (same product under
different vendor SKU strings), hierarchy mismatches, missing rows, and off
control totals — all recorded in `seeds/injected_issues.json` so tests can score
detection.

**Domain model:** 5 companion-animal categories (Parasiticides, Vaccines,
Dermatology, Pain/Osteoarthritis, Petcare Diagnostics) × 5 brands each (one
clearly-marked **Zoetis** brand, three synthetic competitors, one private label)
× 3 channels × National + 4 regions + 5 key metros × 24 months (8 quarters).

---

## Testing

```bash
cd backend && python -m pytest -q          # 34 tests
```

- **`test_engine.py`** — pure math + triangulated estimates vs ground truth (within tolerance), band calibration, e-commerce band tighter than single-source channels.
- **`test_qc.py`** — each of the 5 stages in isolation + the full engine detecting every injected defect class.
- **`test_scoring.py`** — weight normalization, winner re-ranking, pass-through cost model, deterministic narratives.
- **`test_api.py`** — end-to-end smoke of every endpoint via FastAPI's TestClient.

---

## ★ Path to real MVP — what changes when real feeds replace synthetic data

**Only the data layer changes. The engine, QC, scoring, narratives, API and the
entire frontend are untouched.**

| To productionize | File(s) you touch | What stays the same |
|------------------|-------------------|---------------------|
| Replace synthetic CIQ/Stackline/Nielsen with real feeds | **`data/provider.py`** internals + new connector configs | The provider's public method signatures (`observed`, `coverage_for`, `catalog`, `list_*`, …) |
| Ingest real vendor SKU strings | `dim_sku_variants` mapping (now a config/table) loaded by the provider | `engine.py` triangulation + CI — **zero changes** |
| Real coverage figures | source metadata the provider serves | `qc_engine.py`, `scoring.py`, `narratives.py` — **zero changes** |
| Real geography/calendar | provider catalog | every API route + every React page — **zero changes** |

Concretely, the migration is:

1. Implement real connectors (CIQ/Stackline/Nielsen API or file drops) behind the
   **same** `DataProvider` interface — return normalized observations + coverage.
2. Retire `generator.py` and the `seeds/` directory (or keep them for tests/CI).
3. Point `provider.py` at the connectors instead of the CSVs.

Because the engine is **pure** and validated against ground truth, swapping the
data source cannot silently break the math — the test suite still guards it.

---

## Out of scope (by design)

No authentication/SSO, multi-tenancy, real vendor API integrations, payment, CRM
hooks, email, or generic admin panels. The platform does exactly the four things
above and nothing else.
