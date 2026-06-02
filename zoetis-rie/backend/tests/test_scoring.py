"""Procurement scoring + cost-model tests, plus narrative generation."""
from __future__ import annotations

import pytest

from app.core import narratives, scoring


# --------------------------------------------------------------------------
# Weighted scoring
# --------------------------------------------------------------------------
def test_normalize_weights():
    n = scoring.normalize_weights(None)
    assert sum(n.values()) == pytest.approx(1.0)
    # negatives clamped, missing filled, renormalized
    n2 = scoring.normalize_weights({"sku_granularity": -5, "cost_efficiency": 2})
    assert all(v >= 0 for v in n2.values())
    assert sum(n2.values()) == pytest.approx(1.0)
    # all-zero falls back to defaults
    z = scoring.normalize_weights({k: 0 for k in scoring.DEFAULT_WEIGHTS})
    assert sum(z.values()) == pytest.approx(1.0)


def test_default_winner_is_stackline():
    res = scoring.score_vendors(None)
    assert res["winner"] == "Stackline"
    ranks = sorted(v["rank"] for v in res["vendors"])
    assert ranks == [1, 2, 3]
    assert sum(1 for v in res["vendors"] if v["is_winner"]) == 1


def test_weights_reorder_winner_to_ciq():
    # crank historical depth + cost efficiency (CIQ's strengths) -> CIQ wins
    weights = {"sku_granularity": 0.02, "retailer_coverage": 0.02,
               "refresh_frequency": 0.02, "historical_depth": 0.55,
               "cost_efficiency": 0.37, "integration_ease": 0.02}
    res = scoring.score_vendors(weights)
    assert res["winner"] == "CIQ"


def test_weights_reorder_winner_to_nielsen():
    weights = {"sku_granularity": 0.02, "retailer_coverage": 0.9,
               "refresh_frequency": 0.02, "historical_depth": 0.02,
               "cost_efficiency": 0.02, "integration_ease": 0.02}
    res = scoring.score_vendors(weights)
    assert res["winner"] == "Nielsen Digital"


# --------------------------------------------------------------------------
# Cost model (pass-through / zero-markup)
# --------------------------------------------------------------------------
def test_cost_model_pass_through():
    cm = scoring.cost_model("Professional")
    assert cm["service_tier"] == "Professional"
    for row in cm["rows"]:
        # annual total is strictly data + service (no markup on data)
        assert row["annual_total"] == pytest.approx(
            row["vendor_data_cost"] + row["improzo_service_cost"])
        # service cost equals the chosen tier figure for every path
        assert row["improzo_service_cost"] == scoring.SERVICE_TIERS["Professional"]
    # the recommended blend path is present and marked
    assert any("recommended" in r["note"].lower() or "★" in r["note"] for r in cm["rows"])
    assert set(cm["tiers"]) == set(scoring.SERVICE_TIERS.keys())


def test_cost_model_bundle_efficiency():
    # two-feed blend should cost less than the naive sum of the two feeds
    blend = scoring.path_data_cost(["ciq", "stackline"])
    naive = scoring.VENDOR_DATA_COST["ciq"] + scoring.VENDOR_DATA_COST["stackline"]
    assert blend < naive


# --------------------------------------------------------------------------
# Narratives (deterministic, cite the band)
# --------------------------------------------------------------------------
def _facts():
    return {
        "category": "Parasiticides", "channel": "All channels", "geo": "National",
        "geo_level": "National", "period": "2026-Q1", "prior_period": "2025-Q4",
        "zoetis_brand": "Simparica Trio", "zoetis_share_now": 28.8,
        "zoetis_share_prior": 27.5, "zoetis_share_delta": 1.3, "zoetis_rank": 1,
        "zoetis_sales": {"point": 9_600_000, "lower": 9_100_000, "upper": 10_100_000,
                         "rel_width": 0.05, "confidence": "High"},
        "channel_mix": [
            {"channel": "E-commerce", "start_pct": 16.0, "end_pct": 26.0, "delta_pct": 10.0},
            {"channel": "Veterinary", "start_pct": 64.0, "end_pct": 57.0, "delta_pct": -7.0},
            {"channel": "Retail", "start_pct": 20.0, "end_pct": 17.0, "delta_pct": -3.0},
        ],
        "top_mover": {"brand": "Simparica Trio", "delta": 1.3, "is_zoetis": True},
        "top_decliner": {"brand": "FleaStop Pro", "delta": -1.1, "is_zoetis": False},
        "source_agreement": {"dispersion": 0.02, "n_sources": 2, "channel": "E-commerce"},
        "low_confidence": False,
    }


def test_narratives_are_deterministic_and_cite_band():
    f = _facts()
    a = narratives.build_insights(f)
    b = narratives.build_insights(f)
    assert a == b                       # deterministic
    assert len(a) >= 3
    joined = " ".join(i["body"] for i in a)
    assert "band" in joined.lower()     # cites the confidence band
    assert "Simparica Trio" in joined


def test_narratives_flag_low_confidence():
    f = _facts()
    f["low_confidence"] = True
    f["zoetis_sales"]["confidence"] = "Low"
    f["zoetis_sales"]["rel_width"] = 0.18
    a = narratives.build_insights(f)
    assert any(i["confidence"] == "Low" for i in a)
    assert any("low-confidence" in i["headline"].lower() or "low confidence" in i["body"].lower()
               for i in a)
