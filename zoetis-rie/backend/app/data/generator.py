"""Synthetic data generator for the Zoetis Retail Intelligence Engine (RIE).

This module is the *only* place that invents numbers. It builds a hidden
``ground_truth`` table for the animal-health market, then derives several
synthetic vendor feeds from it -- each with deliberately different coverage,
noise and channel bias so that triangulating them is meaningful. It also
injects messy-on-purpose defects (outliers, unmapped SKUs, hierarchy
mismatches, missing rows, off control totals) so the QC engine has real work
to do, and writes a manifest of exactly what it injected so tests can score
detection.

Everything is deterministic given ``--seed`` so demos reproduce exactly.

Run standalone::

    python -m app.data.generator --seed 42 --issues 30

The generated CSV/JSON seeds land in ``app/data/seeds/`` and are the *only*
contract between the synthetic-data layer and the rest of the platform. The
analytics engine and API never read these files directly -- they go through
``app/data/provider.py``. When real vendor feeds replace synthetic data, only
the provider (and these file formats) change; the engine is untouched.
"""
from __future__ import annotations

import argparse
import csv
import json
import math
import random
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"

# --------------------------------------------------------------------------
# Domain catalog -- animal health, companion-animal categories.
# This is the single source of truth for the demo's universe. The generator
# writes it out as dimension files; nothing else imports these constants.
# --------------------------------------------------------------------------

CHANNELS = ["Veterinary", "Retail", "E-commerce"]

# Categories with their national all-channel annual market size (USD) and an
# annual organic growth rate.
CATEGORIES = {
    "Parasiticides":        {"annual": 1_250_000_000, "growth": 0.06},
    "Vaccines":             {"annual":   720_000_000, "growth": 0.03},
    "Dermatology":          {"annual":   980_000_000, "growth": 0.09},
    "Pain/Osteoarthritis":  {"annual":   540_000_000, "growth": 0.12},
    "Petcare Diagnostics":  {"annual":   610_000_000, "growth": 0.07},
}

# Per category: brands with role (zoetis | competitor | private_label), the
# brand's base share of its category (must sum to ~1.0 per category) and a
# nominal unit price used to derive units from sales.
BRANDS = {
    "Parasiticides": [
        ("Simparica Trio",          "zoetis",        0.31, 28.0),
        ("VectraGuard",             "competitor",    0.22, 26.0),
        ("TickShield Plus",         "competitor",    0.17, 24.0),
        ("FleaStop Pro",            "competitor",    0.13, 21.0),
        ("VetSelect Flea & Tick",   "private_label", 0.17, 17.0),
    ],
    "Vaccines": [
        ("Vanguard",                "zoetis",        0.28, 22.0),
        ("ImmunoCore Canine",       "competitor",    0.24, 21.0),
        ("BioShield Vax",           "competitor",    0.19, 20.0),
        ("VetGuard Immunize",       "competitor",    0.16, 19.0),
        ("VetSelect Core Vax",      "private_label", 0.13, 14.0),
    ],
    "Dermatology": [
        ("Apoquel",                 "zoetis",        0.35, 65.0),
        ("DermaCalm",               "competitor",    0.21, 58.0),
        ("AllerVet RX",             "competitor",    0.18, 54.0),
        ("SkinRelief Pro",          "competitor",    0.14, 49.0),
        ("VetSelect Derma",         "private_label", 0.12, 38.0),
    ],
    "Pain/Osteoarthritis": [
        ("Librela",                 "zoetis",        0.26, 48.0),
        ("FlexiCare Joint",         "competitor",    0.23, 44.0),
        ("OsteoEase Vet",           "competitor",    0.20, 41.0),
        ("PainAway Canine",         "competitor",    0.16, 37.0),
        ("VetSelect Joint",         "private_label", 0.15, 29.0),
    ],
    "Petcare Diagnostics": [
        ("Vetscan",                 "zoetis",        0.30, 18.0),
        ("DiagnosTech Vet",         "competitor",    0.25, 17.0),
        ("RapidVet Dx",             "competitor",    0.22, 16.0),
        ("PetLab Analyzer",         "competitor",    0.13, 15.0),
        ("VetSelect Dx",            "private_label", 0.10, 12.0),
    ],
}

# Channel mix per category at the START of the window (vet, retail, ecomm).
# A global trend then pushes e-commerce up and veterinary down over time.
CHANNEL_MIX_START = {
    "Parasiticides":        {"Veterinary": 0.42, "Retail": 0.38, "E-commerce": 0.20},
    "Vaccines":             {"Veterinary": 0.82, "Retail": 0.08, "E-commerce": 0.10},
    "Dermatology":          {"Veterinary": 0.68, "Retail": 0.14, "E-commerce": 0.18},
    "Pain/Osteoarthritis":  {"Veterinary": 0.74, "Retail": 0.10, "E-commerce": 0.16},
    "Petcare Diagnostics":  {"Veterinary": 0.80, "Retail": 0.06, "E-commerce": 0.14},
}
# Total mix shift applied linearly across the window (the "e-comm rising /
# vet eroding" story). Retail drifts slightly down.
TREND_ECOMM_UP = 0.10
TREND_VET_DOWN = 0.08
TREND_RETAIL_DOWN = 0.02

# Geography hierarchy.
REGION_WEIGHTS = {"Northeast": 0.22, "South": 0.34, "Midwest": 0.21, "West": 0.23}
# Key metro areas (DMAs) as a modeled subset of their parent region.
METROS = {
    "New York":           {"parent": "Northeast", "share_of_region": 0.46},
    "Chicago":            {"parent": "Midwest",   "share_of_region": 0.43},
    "Los Angeles":        {"parent": "West",      "share_of_region": 0.50},
    "Dallas-Fort Worth":  {"parent": "South",     "share_of_region": 0.28},
    "Atlanta":            {"parent": "South",      "share_of_region": 0.22},
}

# Synthetic vendor / internal feeds. ``channel`` is the only channel the source
# observes; ``coverage`` is the fraction of true sales it captures; ``bias`` is
# a small persistent multiplicative skew; ``history`` is how many of the most
# recent months the source carries (Stackline is recent-only).
SOURCES = {
    "ciq_ecommerce": {
        "channel": "E-commerce", "coverage": 0.82, "bias": 0.985,
        "noise_sd": 0.038, "history": 24, "sku_granular": False,
        "label": "CIQ (e-commerce panel)",
        "note": "E-commerce only, history-rich, ~82% coverage.",
    },
    "stackline_ecommerce": {
        "channel": "E-commerce", "coverage": 0.88, "bias": 1.012,
        "noise_sd": 0.030, "history": 18, "sku_granular": True,
        "label": "Stackline (e-commerce)",
        "note": "E-commerce only, SKU-granular, recent (18 mo), ~88% coverage.",
    },
    "nielsen_scanner": {
        "channel": "Retail", "coverage": 0.91, "bias": 1.0,
        "noise_sd": 0.028, "history": 24, "sku_granular": False,
        "label": "Nielsen (retail scanner)",
        "note": "Retail scanner (mass/grocery/drug/club), ~91% coverage.",
    },
    "zoetis_vet_internal": {
        "channel": "Veterinary", "coverage": 0.96, "bias": 1.0,
        "noise_sd": 0.020, "history": 24, "sku_granular": True,
        "label": "Zoetis internal (vet)",
        "note": "Veterinary internal feed, ~96% coverage.",
    },
}

# Number of trailing months (8 quarters), anchored to quarter boundaries.
N_MONTHS = 24
WINDOW_END = (2026, 3)  # inclusive last month -> 2024-04 .. 2026-03


# --------------------------------------------------------------------------
# Helpers
# --------------------------------------------------------------------------

def _build_months() -> list[dict]:
    """Return the 24-month axis as dicts with month id and quarter label."""
    end_y, end_m = WINDOW_END
    months: list[dict] = []
    y, m = end_y, end_m
    for _ in range(N_MONTHS):
        months.append((y, m))
        m -= 1
        if m == 0:
            m = 12
            y -= 1
    months.reverse()
    out = []
    for y, m in months:
        out.append({
            "month": f"{y}-{m:02d}",
            "year": y,
            "month_num": m,
            "quarter": f"{y}-Q{(m - 1) // 3 + 1}",
        })
    return out


def _slug(text: str) -> str:
    keep = []
    for ch in text.upper():
        if ch.isalnum():
            keep.append(ch)
        elif ch in " -/&":
            keep.append("-")
    s = "".join(keep)
    while "--" in s:
        s = s.replace("--", "-")
    return s.strip("-")


CAT_CODE = {
    "Parasiticides": "PAR",
    "Vaccines": "VAC",
    "Dermatology": "DRM",
    "Pain/Osteoarthritis": "PAN",
    "Petcare Diagnostics": "DIA",
}

# Two pack sizes per brand (SKU dimension).
PACK_SIZES = [("S", "Small / starter pack"), ("L", "Large / value pack")]


def _sku_variants(source: str, canonical: str, brand: str, pack: str) -> str:
    """Produce a deliberately messy, source-specific raw SKU string for a
    canonical SKU. The same product looks different across vendors so the
    normalization step has real work to do.
    """
    brand_token = _slug(brand)
    if source == "ciq_ecommerce":
        return f"{brand_token}_{pack}".upper()
    if source == "stackline_ecommerce":
        return f"{brand.lower().replace(' ', '_').replace('&','and')}-{pack.lower()}"
    if source == "nielsen_scanner":
        size_word = "SMALL" if pack == "S" else "LARGE"
        return f"{brand.upper()} {size_word}"
    if source == "zoetis_vet_internal":
        return f"{canonical}"  # internal uses the canonical code itself
    return canonical


# --------------------------------------------------------------------------
# Catalog construction (dimension rows)
# --------------------------------------------------------------------------

@dataclass
class Catalog:
    brands: list[dict] = field(default_factory=list)        # brand dim rows
    skus: list[dict] = field(default_factory=list)          # canonical sku rows
    sku_variants: list[dict] = field(default_factory=list)  # (source, raw)->canonical
    geography: list[dict] = field(default_factory=list)     # geo dim rows
    months: list[dict] = field(default_factory=list)


def _build_catalog() -> Catalog:
    cat = Catalog(months=_build_months())

    # Geography
    cat.geography.append({"geo": "National", "geo_level": "National", "parent": "", "share_of_parent": 1.0})
    for region, w in REGION_WEIGHTS.items():
        cat.geography.append({"geo": region, "geo_level": "Region", "parent": "National", "share_of_parent": round(w, 4)})
    for metro, meta in METROS.items():
        cat.geography.append({"geo": metro, "geo_level": "Metro", "parent": meta["parent"],
                              "share_of_parent": round(meta["share_of_region"], 4)})

    # Brands + SKUs + variants
    for category, brands in BRANDS.items():
        for brand, role, base_share, price in brands:
            cat.brands.append({
                "brand": brand,
                "category": category,
                "is_zoetis": role == "zoetis",
                "is_private_label": role == "private_label",
                "role": role,
                "base_share": base_share,
                "unit_price": price,
            })
            for pack, pack_desc in PACK_SIZES:
                canonical = f"{CAT_CODE[category]}-{_slug(brand)[:10]}-{pack}"
                cat.skus.append({
                    "sku_canonical": canonical,
                    "brand": brand,
                    "category": category,
                    "pack": pack,
                    "pack_desc": pack_desc,
                })
                for source in SOURCES:
                    cat.sku_variants.append({
                        "source": source,
                        "sku_raw": _sku_variants(source, canonical, brand, pack),
                        "sku_canonical": canonical,
                        "brand": brand,
                    })
    return cat


# --------------------------------------------------------------------------
# Ground truth
# --------------------------------------------------------------------------

def _seasonality(category: str, month_num: int) -> float:
    """Multiplicative seasonal factor (mean ~1) per category."""
    two_pi = 2 * math.pi
    if category == "Parasiticides":      # strong spring/summer flea-tick peak
        return 1 + 0.35 * math.sin(two_pi * (month_num - 3) / 12)
    if category == "Dermatology":         # summer allergy peak
        return 1 + 0.18 * math.sin(two_pi * (month_num - 4) / 12)
    if category == "Vaccines":            # mild spring (puppy season)
        return 1 + 0.12 * math.sin(two_pi * (month_num - 2) / 12)
    if category == "Pain/Osteoarthritis":  # winter peak
        return 1 + 0.12 * math.sin(two_pi * (month_num - 11) / 12)
    return 1 + 0.05 * math.sin(two_pi * (month_num - 1) / 12)  # diagnostics, flat-ish


def _channel_mix(category: str, role: str, t: float) -> dict[str, float]:
    """Channel mix for a brand at fractional time t in [0, 1] across window.

    Applies the global e-comm-rising / vet-eroding trend, with Zoetis brands
    retaining veterinary better and private label skewing to retail.
    """
    base = dict(CHANNEL_MIX_START[category])
    if role == "private_label":
        shift = min(base["Veterinary"], 0.15)
        base["Veterinary"] -= shift
        base["Retail"] += shift
    elif role == "zoetis":
        bump = min(base["Retail"] + base["E-commerce"], 0.05)
        base["Veterinary"] += bump
        base["Retail"] = max(0.0, base["Retail"] - bump * 0.5)
        base["E-commerce"] = max(0.0, base["E-commerce"] - bump * 0.5)

    vet_erosion = TREND_VET_DOWN * (0.6 if role == "zoetis" else 1.0) * t
    mix = {
        "Veterinary": max(0.01, base["Veterinary"] - vet_erosion),
        "Retail": max(0.01, base["Retail"] - TREND_RETAIL_DOWN * t),
        "E-commerce": base["E-commerce"] + TREND_ECOMM_UP * t + (vet_erosion + TREND_RETAIL_DOWN * t) * 0.0,
    }
    # absorb whatever vet/retail gave up into e-commerce so the mix sums to 1
    total = sum(mix.values())
    return {k: v / total for k, v in mix.items()}


def build_ground_truth(cat: Catalog, rng: random.Random) -> list[dict]:
    """Build the hidden ground-truth table at brand x channel x region x month.

    National rows are the exact sum of region rows (so geography rollups are
    testable). Returns a flat list of dict rows.
    """
    rows: list[dict] = []
    brand_index = {b["brand"]: b for b in cat.brands}
    for category, brands in BRANDS.items():
        cmeta = CATEGORIES[category]
        for brand, role, base_share, price in brands:
            base_monthly = cmeta["annual"] * base_share / 12.0
            for ti, mrow in enumerate(cat.months):
                t = ti / (N_MONTHS - 1)
                growth = (1 + cmeta["growth"]) ** (ti / 12.0)
                seas = _seasonality(category, mrow["month_num"])
                brand_noise = 1 + rng.gauss(0, 0.02)
                monthly_total = base_monthly * growth * seas * brand_noise
                mix = _channel_mix(category, role, t)
                for channel in CHANNELS:
                    channel_total = monthly_total * mix[channel]
                    region_sales = {}
                    for region, w in REGION_WEIGHTS.items():
                        rn = 1 + rng.gauss(0, 0.03)
                        region_sales[region] = max(0.0, channel_total * w * rn)
                    national = sum(region_sales.values())
                    # region rows
                    for region, sales in region_sales.items():
                        rows.append({
                            "month": mrow["month"],
                            "quarter": mrow["quarter"],
                            "category": category,
                            "brand": brand,
                            "is_zoetis": role == "zoetis",
                            "channel": channel,
                            "geo_level": "Region",
                            "geo": region,
                            "true_sales": round(sales, 2),
                            "true_units": int(round(sales / price)),
                        })
                    # national row = exact sum of regions
                    rows.append({
                        "month": mrow["month"],
                        "quarter": mrow["quarter"],
                        "category": category,
                        "brand": brand,
                        "is_zoetis": role == "zoetis",
                        "channel": channel,
                        "geo_level": "National",
                        "geo": "National",
                        "true_sales": round(national, 2),
                        "true_units": int(round(national / price)),
                    })
    return rows


# --------------------------------------------------------------------------
# Source derivation
# --------------------------------------------------------------------------

def derive_sources(cat: Catalog, truth: list[dict], rng: random.Random
                   ) -> dict[str, list[dict]]:
    """Derive each synthetic vendor feed from ground truth.

    Each source observes only its channel, at ``coverage`` of true sales, with
    a small persistent bias and per-row noise. Brand sales are spread across
    the brand's two SKUs using source-specific raw SKU strings. A National row
    per (source, brand, month) is emitted as an independent aggregate.
    """
    months = cat.months
    recent_month_ids = {m["month"] for m in months}
    sku_by_brand: dict[str, list[dict]] = {}
    for s in cat.skus:
        sku_by_brand.setdefault(s["brand"], []).append(s)
    price_by_brand = {b["brand"]: b["unit_price"] for b in cat.brands}

    # index truth by (brand, channel, geo_level, geo, month)
    truth_idx = {(r["brand"], r["channel"], r["geo_level"], r["geo"], r["month"]): r for r in truth}

    out: dict[str, list[dict]] = {}
    for source, meta in SOURCES.items():
        channel = meta["channel"]
        coverage = meta["coverage"]
        bias = meta["bias"]
        noise_sd = meta["noise_sd"]
        history = meta["history"]
        # most-recent ``history`` months
        active_months = [m["month"] for m in months[-history:]]
        rows: list[dict] = []
        for tr in truth:
            if tr["channel"] != channel:
                continue
            if tr["geo_level"] != "Region":
                continue  # build region rows here; national aggregated below
            if tr["month"] not in active_months:
                continue
            brand = tr["brand"]
            # SKU split weights (deterministic-ish per brand)
            skus = sku_by_brand[brand]
            split = [0.58, 0.42] if len(skus) == 2 else [1.0]
            for sku, frac in zip(skus, split):
                noise = rng.gauss(0, noise_sd)
                observed = max(0.0, tr["true_sales"] * frac * coverage * bias * (1 + noise))
                units = int(round(observed / price_by_brand[brand]))
                rows.append({
                    "source": source,
                    "month": tr["month"],
                    "quarter": tr["quarter"],
                    "category": tr["category"],
                    "brand_reported": brand,
                    "sku_raw": _sku_variants(source, sku["sku_canonical"], brand, sku["pack"]),
                    "channel": channel,
                    "geo_level": "Region",
                    "geo": tr["geo"],
                    "observed_units": units,
                    "observed_sales": round(observed, 2),
                    "coverage": coverage,
                })
        # National aggregate rows per (brand, sku, month) = sum over regions
        agg: dict[tuple, dict] = {}
        for r in rows:
            key = (r["brand_reported"], r["sku_raw"], r["month"])
            a = agg.get(key)
            if a is None:
                agg[key] = {**r, "geo_level": "National", "geo": "National"}
            else:
                a["observed_units"] += r["observed_units"]
                a["observed_sales"] = round(a["observed_sales"] + r["observed_sales"], 2)
        rows.extend(agg.values())
        out[source] = rows
    return out


# --------------------------------------------------------------------------
# Control totals (finance reconciliation targets for QC stage 4)
# --------------------------------------------------------------------------

def build_control_totals(truth: list[dict]) -> list[dict]:
    agg: dict[tuple, float] = {}
    for r in truth:
        if r["geo_level"] != "National":
            continue
        key = (r["month"], r["quarter"], r["category"], r["channel"])
        agg[key] = agg.get(key, 0.0) + r["true_sales"]
    rows = []
    for (month, quarter, category, channel), total in sorted(agg.items()):
        rows.append({
            "month": month, "quarter": quarter, "category": category,
            "channel": channel, "control_total_sales": round(total, 2),
        })
    return rows


# --------------------------------------------------------------------------
# Issue injection
# --------------------------------------------------------------------------

def inject_issues(sources: dict[str, list[dict]], control_totals: list[dict],
                  cat: Catalog, n_outliers: int, rng: random.Random) -> list[dict]:
    """Inject messy-on-purpose defects and return a manifest of what was done.

    Defects: statistical outliers (configurable count), a fixed small set of
    unmapped SKUs, hierarchy mismatches, missing rows, and off control totals.
    """
    manifest: list[dict] = []

    # --- statistical outliers: spike or drop a brand-region-month (all SKUs)
    # so the anomaly survives SKU normalization and is cleanly detectable. ---
    region_groups: dict[tuple, list[int]] = {}
    for source, rows in sources.items():
        for i, r in enumerate(rows):
            if r["geo_level"] == "Region":
                region_groups.setdefault((source, r["brand_reported"], r["geo"], r["month"]), []).append(i)
    group_keys = list(region_groups.keys())
    rng.shuffle(group_keys)
    for source, brand, geo, month in group_keys[:n_outliers]:
        if rng.random() < 0.6:
            factor = rng.uniform(3.5, 7.0)
            kind = "spike"
        else:
            factor = rng.uniform(0.05, 0.25)
            kind = "drop"
        before = 0.0
        after = 0.0
        for i in region_groups[(source, brand, geo, month)]:
            r = sources[source][i]
            before += r["observed_sales"]
            r["observed_sales"] = round(r["observed_sales"] * factor, 2)
            r["observed_units"] = int(round(r["observed_units"] * factor))
            after += r["observed_sales"]
        manifest.append({
            "type": "outlier", "subtype": kind, "source": source,
            "brand": brand, "geo": geo, "month": month,
            "detail": f"{kind} x{factor:.2f} ({before:.0f} -> {after:.0f})",
        })

    # --- unmapped SKUs: rows whose sku_raw is absent from the variant map ---
    unmapped_targets = [
        ("stackline_ecommerce", "TEMP-SKU-0091"),
        ("ciq_ecommerce", "UNKNOWN_LISTING_4471"),
        ("nielsen_scanner", "PRIVATE LABEL UNSPEC"),
        ("stackline_ecommerce", "promo-bundle-xx"),
    ]
    for source, raw in unmapped_targets:
        template = next(r for r in sources[source] if r["geo_level"] == "Region")
        row = {**template, "sku_raw": raw, "brand_reported": "",
               "observed_sales": round(rng.uniform(20_000, 90_000), 2)}
        row["observed_units"] = int(row["observed_sales"] / 25)
        sources[source].append(row)
        manifest.append({
            "type": "unmapped_sku", "source": source, "sku_raw": raw,
            "geo": row["geo"], "month": row["month"],
            "detail": "SKU string not present in dim_sku_variants",
        })

    # --- hierarchy mismatches: inflate a whole brand-month National (all SKUs)
    # so National no longer equals the sum of its regions. ---
    nat_groups: dict[tuple, list[int]] = {}
    for source, rows in sources.items():
        for i, r in enumerate(rows):
            if r["geo_level"] == "National":
                nat_groups.setdefault((source, r["brand_reported"], r["month"]), []).append(i)
    nat_keys = list(nat_groups.keys())
    rng.shuffle(nat_keys)
    for source, brand, month in nat_keys[:2]:
        before = after = 0.0
        for i in nat_groups[(source, brand, month)]:
            r = sources[source][i]
            before += r["observed_sales"]
            r["observed_sales"] = round(r["observed_sales"] * 1.25, 2)
            after += r["observed_sales"]
        manifest.append({
            "type": "hierarchy_mismatch", "source": source,
            "brand": brand, "month": month,
            "detail": f"National inflated 25% vs region sum ({before:.0f} -> {after:.0f})",
        })

    # --- missing rows: drop a handful of region rows ---
    drop_pool = []
    for source, rows in sources.items():
        for i, r in enumerate(rows):
            if r["geo_level"] == "Region":
                drop_pool.append((source, i))
    rng.shuffle(drop_pool)
    to_drop = sorted(drop_pool[:6], key=lambda x: -x[1])  # drop high index first
    for source, i in to_drop:
        r = sources[source][i]
        manifest.append({
            "type": "missing_row", "source": source, "brand": r["brand_reported"],
            "sku_raw": r["sku_raw"], "geo": r["geo"], "month": r["month"],
            "detail": "row removed from feed",
        })
        del sources[source][i]

    # --- off control totals: skew a couple of finance control figures ---
    ct_idx = list(range(len(control_totals)))
    rng.shuffle(ct_idx)
    for i in ct_idx[:2]:
        ct = control_totals[i]
        original = ct["control_total_sales"]
        ct["control_total_sales"] = round(original * rng.choice([0.85, 1.15]), 2)
        manifest.append({
            "type": "control_total_off", "month": ct["month"],
            "category": ct["category"], "channel": ct["channel"],
            "detail": f"control total moved ({original:.0f} -> {ct['control_total_sales']:.0f})",
        })

    return manifest


# --------------------------------------------------------------------------
# Writing seeds
# --------------------------------------------------------------------------

def _write_csv(path: Path, rows: list[dict], fieldnames: list[str]) -> None:
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader()
        for r in rows:
            w.writerow({k: r.get(k, "") for k in fieldnames})


def _write_json(path: Path, obj) -> None:
    with path.open("w") as f:
        json.dump(obj, f, indent=2, default=str)


def generate(seed: int = 42, issues: int = 30, randomize: bool = False,
             out_dir: Optional[Path] = None) -> dict:
    """Generate the full seed set. Returns a summary dict (also the metadata)."""
    out_dir = Path(out_dir) if out_dir else SEEDS_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    actual_seed = None if randomize else seed
    rng = random.Random(actual_seed)

    cat = _build_catalog()
    truth = build_ground_truth(cat, rng)
    sources = derive_sources(cat, truth, rng)
    control_totals = build_control_totals(truth)
    manifest = inject_issues(sources, control_totals, cat, issues, rng)

    # dimension files
    _write_csv(out_dir / "dim_brand.csv", cat.brands,
               ["brand", "category", "is_zoetis", "is_private_label", "role", "base_share", "unit_price"])
    _write_csv(out_dir / "dim_sku.csv", cat.skus,
               ["sku_canonical", "brand", "category", "pack", "pack_desc"])
    _write_csv(out_dir / "dim_sku_variants.csv", cat.sku_variants,
               ["source", "sku_raw", "sku_canonical", "brand"])
    _write_csv(out_dir / "dim_geography.csv", cat.geography,
               ["geo", "geo_level", "parent", "share_of_parent"])

    # ground truth (hidden; used by tests + share-of-truth scoring only)
    _write_csv(out_dir / "ground_truth.csv", truth,
               ["month", "quarter", "category", "brand", "is_zoetis", "channel",
                "geo_level", "geo", "true_sales", "true_units"])

    # source feeds
    src_fields = ["source", "month", "quarter", "category", "brand_reported", "sku_raw",
                  "channel", "geo_level", "geo", "observed_units", "observed_sales", "coverage"]
    source_file = {
        "ciq_ecommerce": "ciq_ecommerce.csv",
        "stackline_ecommerce": "stackline_ecommerce.csv",
        "nielsen_scanner": "nielsen_scanner.csv",
        "zoetis_vet_internal": "zoetis_vet_internal.csv",
    }
    source_row_counts = {}
    for source, rows in sources.items():
        rows_sorted = sorted(rows, key=lambda r: (r["month"], r["geo_level"], r["geo"], r["brand_reported"], r["sku_raw"]))
        _write_csv(out_dir / source_file[source], rows_sorted, src_fields)
        source_row_counts[source] = len(rows_sorted)

    # control totals
    _write_csv(out_dir / "control_totals.csv", control_totals,
               ["month", "quarter", "category", "channel", "control_total_sales"])

    # issue manifest
    issue_summary: dict[str, int] = {}
    for m in manifest:
        issue_summary[m["type"]] = issue_summary.get(m["type"], 0) + 1
    _write_json(out_dir / "injected_issues.json",
                {"summary": issue_summary, "issues": manifest})

    # metadata -- the catalog contract the provider reads back
    metadata = {
        "generated_at": date.today().isoformat(),
        "seed": actual_seed,
        "randomized": randomize,
        "n_months": N_MONTHS,
        "window": {"start": cat.months[0]["month"], "end": cat.months[-1]["month"]},
        "channels": CHANNELS,
        "categories": list(CATEGORIES.keys()),
        "months": cat.months,
        "quarters": sorted({m["quarter"] for m in cat.months}),
        "geography": cat.geography,
        "sources": {
            s: {"channel": meta["channel"], "coverage": meta["coverage"],
                "history": meta["history"], "label": meta["label"], "note": meta["note"]}
            for s, meta in SOURCES.items()
        },
        "channel_sources": {
            ch: [s for s, meta in SOURCES.items() if meta["channel"] == ch] for ch in CHANNELS
        },
        "n_brands": len(cat.brands),
        "n_skus": len(cat.skus),
        "source_row_counts": source_row_counts,
        "ground_truth_rows": len(truth),
        "issues_injected": issue_summary,
    }
    _write_json(out_dir / "metadata.json", metadata)

    summary = {
        "seed": actual_seed,
        "out_dir": str(out_dir),
        "brands": len(cat.brands),
        "skus": len(cat.skus),
        "ground_truth_rows": len(truth),
        "source_row_counts": source_row_counts,
        "issues_injected": issue_summary,
        "window": metadata["window"],
    }
    return summary


def main(argv: Optional[list[str]] = None) -> None:
    parser = argparse.ArgumentParser(description="Generate synthetic seeds for the Zoetis RIE.")
    parser.add_argument("--seed", type=int, default=42, help="deterministic seed (default 42)")
    parser.add_argument("--issues", type=int, default=30,
                        help="number of statistical outliers to inject (default 30); "
                             "a fixed set of structural defects is added on top")
    parser.add_argument("--random", dest="randomize", action="store_true",
                        help="ignore --seed and use system entropy for variety")
    parser.add_argument("--out", type=str, default=None, help="output dir (default app/data/seeds)")
    args = parser.parse_args(argv)

    summary = generate(seed=args.seed, issues=args.issues,
                       randomize=args.randomize, out_dir=args.out)
    print("Generated Zoetis RIE seeds")
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
