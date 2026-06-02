"""Procurement decision tool: weighted vendor scoring + cost model -- PURE.

This unblocks the real CIQ-vs-Stackline buy decision. Each e-commerce data
vendor is rated 0-100 on six procurement criteria (these capability ratings are
the fixed "data"); the buyer adjusts the *weights* live and the winner re-ranks.

The cost model makes the pass-through, zero-markup principle explicit: external
vendor data is billed to Zoetis at vendor cost; Improzo analytics / managed
services are priced separately by tier and are the only Improzo margin. All
service figures are illustrative placeholders, clearly labelled.
"""
from __future__ import annotations

from typing import Optional

# --------------------------------------------------------------------------
# Criteria + vendor capability ratings (0-100, higher is better)
# --------------------------------------------------------------------------
CRITERIA = [
    {"key": "sku_granularity",  "label": "SKU granularity",
     "description": "Depth of SKU / listing-level detail."},
    {"key": "retailer_coverage", "label": "Retailer coverage",
     "description": "Breadth of retailers / marketplaces captured."},
    {"key": "refresh_frequency", "label": "Refresh frequency",
     "description": "How current and how often the data refreshes."},
    {"key": "historical_depth",  "label": "Historical depth",
     "description": "Length and completeness of back history."},
    {"key": "cost_efficiency",   "label": "Cost efficiency",
     "description": "Value per dollar of the data feed."},
    {"key": "integration_ease",  "label": "Integration ease",
     "description": "Effort to ingest, map and maintain the feed."},
]

VENDORS = {
    "ciq": {
        "label": "CIQ",
        "ratings": {"sku_granularity": 70, "retailer_coverage": 78,
                    "refresh_frequency": 75, "historical_depth": 92,
                    "cost_efficiency": 80, "integration_ease": 78},
        "blurb": "E-commerce panel: history-rich, ~82% coverage.",
    },
    "stackline": {
        "label": "Stackline",
        "ratings": {"sku_granularity": 95, "retailer_coverage": 85,
                    "refresh_frequency": 90, "historical_depth": 65,
                    "cost_efficiency": 70, "integration_ease": 82},
        "blurb": "E-commerce: SKU-granular and recent, ~88% coverage.",
    },
    "nielsen_digital": {
        "label": "Nielsen Digital",
        "ratings": {"sku_granularity": 60, "retailer_coverage": 92,
                    "refresh_frequency": 70, "historical_depth": 80,
                    "cost_efficiency": 60, "integration_ease": 72},
        "blurb": "Retail-scanner heritage extended to digital, ~91% coverage.",
    },
}

DEFAULT_WEIGHTS = {
    "sku_granularity": 0.20, "retailer_coverage": 0.20, "refresh_frequency": 0.15,
    "historical_depth": 0.15, "cost_efficiency": 0.18, "integration_ease": 0.12,
}


def normalize_weights(weights: Optional[dict[str, float]]) -> dict[str, float]:
    """Fill missing criteria from defaults, clamp negatives, normalize to 1.0."""
    keys = [c["key"] for c in CRITERIA]
    raw = {k: float(weights.get(k, DEFAULT_WEIGHTS[k])) if weights else DEFAULT_WEIGHTS[k]
           for k in keys}
    raw = {k: max(0.0, v) for k, v in raw.items()}
    total = sum(raw.values())
    if total <= 0:
        return dict(DEFAULT_WEIGHTS)
    return {k: v / total for k, v in raw.items()}


def score_vendors(weights: Optional[dict[str, float]] = None) -> dict:
    """Weighted-score every vendor and rank them. Pure: weights in, ranking out."""
    norm = normalize_weights(weights)
    results = []
    for vid, v in VENDORS.items():
        per_criterion = {}
        total = 0.0
        for k in norm:
            raw = v["ratings"][k]
            weighted = raw * norm[k]
            per_criterion[k] = {"raw": raw, "weighted": round(weighted, 2)}
            total += weighted
        results.append({
            "vendor": vid, "label": v["label"], "blurb": v["blurb"],
            "total_score": round(total, 2), "per_criterion": per_criterion,
        })
    results.sort(key=lambda r: r["total_score"], reverse=True)
    for i, r in enumerate(results, 1):
        r["rank"] = i
        r["is_winner"] = i == 1

    winner = results[0]
    runner_up = results[1]
    margin = winner["total_score"] - runner_up["total_score"]
    # which criterion most separates winner from runner-up, given the weights
    swing_key = max(
        norm,
        key=lambda k: (winner["per_criterion"][k]["weighted"]
                       - runner_up["per_criterion"][k]["weighted"]),
    )
    swing_label = next(c["label"] for c in CRITERIA if c["key"] == swing_key)
    rationale = (
        f"{winner['label']} leads with {winner['total_score']:.1f} vs "
        f"{runner_up['label']} {runner_up['total_score']:.1f} "
        f"(margin {margin:.1f}). The deciding strength at these weights is "
        f"{swing_label.lower()}."
    )
    criteria_with_weights = [{**c, "weight": round(norm[c["key"]], 4)} for c in CRITERIA]
    return {
        "criteria": criteria_with_weights,
        "vendors": results,
        "winner": winner["label"],
        "winner_rationale": rationale,
        "normalized_weights": {k: round(v, 4) for k, v in norm.items()},
    }


# --------------------------------------------------------------------------
# Cost model (pass-through vendor data + tiered Improzo services)
# --------------------------------------------------------------------------
# Annual external data cost per vendor path (USD). Combination paths apply a
# modest multi-feed bundle efficiency. PLACEHOLDER figures for the demo.
VENDOR_DATA_COST = {
    "ciq": 180_000,
    "stackline": 220_000,
    "nielsen_digital": 310_000,
}

DATA_PATHS = [
    {"key": "ciq", "label": "CIQ only", "vendors": ["ciq"],
     "note": "Single e-commerce panel; history-rich but narrower."},
    {"key": "stackline", "label": "Stackline only", "vendors": ["stackline"],
     "note": "Single e-commerce feed; SKU-granular but recent-only."},
    {"key": "nielsen_digital", "label": "Nielsen Digital only", "vendors": ["nielsen_digital"],
     "note": "Broad retailer coverage; lower SKU granularity."},
    {"key": "ciq_stackline", "label": "CIQ + Stackline (e-comm blend)",
     "vendors": ["ciq", "stackline"], "recommended": True,
     "note": "Recommended: blends coverage + history with SKU granularity; tightest e-comm bands."},
    {"key": "full_triangulation", "label": "Full triangulation (CIQ + Stackline + Nielsen)",
     "vendors": ["ciq", "stackline", "nielsen_digital"],
     "note": "Maximum coverage across e-comm + retail; highest data cost."},
]
BUNDLE_EFFICIENCY = {1: 1.0, 2: 0.92, 3: 0.86}  # discount factor by # of feeds

# Improzo managed-service fee by tier (USD/yr) -- PLACEHOLDER, priced separately.
SERVICE_TIERS = {
    "Essential":    120_000,
    "Professional": 200_000,
    "Enterprise":   320_000,
}
DEFAULT_TIER = "Professional"


def path_data_cost(vendors: list[str]) -> float:
    base = sum(VENDOR_DATA_COST[v] for v in vendors)
    return round(base * BUNDLE_EFFICIENCY.get(len(vendors), 0.86), 2)


def cost_model(service_tier: str = DEFAULT_TIER) -> dict:
    """Annual cost by vendor path for a chosen Improzo service tier. Pure."""
    if service_tier not in SERVICE_TIERS:
        service_tier = DEFAULT_TIER
    service_cost = SERVICE_TIERS[service_tier]
    rows = []
    for path in DATA_PATHS:
        data_cost = path_data_cost(path["vendors"])
        note = path["note"]
        if path.get("recommended"):
            note = "★ " + note
        rows.append({
            "vendor_path": path["key"],
            "label": path["label"],
            "vendor_data_cost": data_cost,
            "improzo_service_cost": float(service_cost),
            "annual_total": round(data_cost + service_cost, 2),
            "note": note,
        })
    return {
        "service_tier": service_tier,
        "rows": rows,
        "tiers": list(SERVICE_TIERS.keys()),
        "principle": (
            "Pass-through, zero-markup: external vendor data is billed to Zoetis "
            "at vendor cost. Improzo analytics & managed-service fees are priced "
            "separately by tier and are the only Improzo margin."
        ),
        "disclaimer": (
            "All figures are illustrative placeholders for this demo and clearly "
            "labelled as such; replace with contracted vendor and service rates."
        ),
    }
