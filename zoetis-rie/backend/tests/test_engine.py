"""Engine math tests -- pure functions and truth-recovery against ground truth.

The contract from the brief: "triangulated estimates must land within a
tolerance of ground truth." We verify that here at national grain (where noise
averages out) for every brand-channel-period slice the generator did NOT
deliberately corrupt, plus we check the confidence band is well-formed and
actually covers the truth most of the time.
"""
from __future__ import annotations

import math

import pytest

from app.core import engine
from app.data.provider import get_provider


# --------------------------------------------------------------------------
# Pure-function unit tests (no data needed)
# --------------------------------------------------------------------------

def test_gross_up():
    assert engine.gross_up(82.0, 0.82) == pytest.approx(100.0)
    assert engine.gross_up(0.0, 0.9) == 0.0
    assert engine.gross_up(50.0, 0.0) == 0.0  # guard against div-by-zero


def test_combined_coverage_union():
    # two e-commerce sources together cover more than either alone
    c = engine.combined_coverage([0.82, 0.88])
    assert c == pytest.approx(1 - 0.18 * 0.12)
    assert c > 0.82 and c > 0.88
    assert engine.combined_coverage([0.91]) == pytest.approx(0.91)


def test_triangulate_recovers_blended_truth():
    # ciq sees 82% of 1000, stackline 88% of 1000 -> both should gross up to ~1000
    obs = {"ciq_ecommerce": 820.0, "stackline_ecommerce": 880.0}
    cov = {"ciq_ecommerce": 0.82, "stackline_ecommerce": 0.88}
    tri = engine.triangulate(obs, cov)
    assert tri["point"] == pytest.approx(1000.0)
    assert tri["n_sources"] == 2
    assert tri["rel_dispersion"] == pytest.approx(0.0, abs=1e-9)


def test_triangulate_ignores_zero_coverage_sources():
    obs = {"a": 100.0, "b": 50.0}
    cov = {"a": 1.0, "b": 0.0}
    tri = engine.triangulate(obs, cov)
    assert tri["n_sources"] == 1
    assert tri["point"] == pytest.approx(100.0)


def test_ci_well_formed_and_ordered():
    ci = engine.confidence_interval(1000.0, rel_dispersion=0.03,
                                    comb_coverage=0.978, n_sources=2)
    assert 0.0 <= ci["lower"] <= 1000.0 <= ci["upper"]
    assert ci["half_width"] > 0


def test_ci_narrows_when_sources_agree_and_coverage_high():
    agree_high = engine.confidence_interval(1000.0, 0.01, 0.978, 2)["rel_width"]
    disagree = engine.confidence_interval(1000.0, 0.10, 0.978, 2)["rel_width"]
    low_cov = engine.confidence_interval(1000.0, 0.01, 0.70, 1)["rel_width"]
    assert agree_high < disagree       # disagreement widens the band
    assert agree_high < low_cov        # coverage gap + single source widens it


def test_single_source_wider_than_two_source_all_else_equal():
    one = engine.relative_uncertainty(0.0, 0.91, 1)
    two = engine.relative_uncertainty(0.0, 0.91, 2)
    assert one > two


def test_aggregate_band_tightens_relatively():
    # summing 4 independent equal slices: absolute band grows ~2x, point grows 4x,
    # so the *relative* band roughly halves.
    one = {"point": 100.0, "lower": 90.0, "upper": 110.0, "half_width": 10.0, "rel_width": 0.10}
    agg = engine.aggregate_estimates([one] * 4)
    assert agg["point"] == pytest.approx(400.0)
    assert agg["half_width"] == pytest.approx(20.0)
    assert agg["rel_width"] == pytest.approx(0.05)


def test_market_share_and_band():
    assert engine.market_share(250.0, 1000.0) == pytest.approx(25.0)
    assert engine.market_share(1.0, 0.0) == 0.0
    lo, hi = engine.share_band(200.0, 300.0, 1000.0)
    assert (lo, hi) == pytest.approx((20.0, 30.0))


# --------------------------------------------------------------------------
# Truth-recovery tests against the committed seed-42 data
# --------------------------------------------------------------------------

NATIONAL_TOL = 0.07   # national estimates must be within 7% of truth
COVER_MIN = 0.80      # >=80% of national slices: truth must fall in the 95% band


def _corrupted_slices(provider) -> set[tuple]:
    """(brand, channel, month) slices the generator deliberately corrupted, so
    we exclude them from truth-recovery checks."""
    src_channel = {s: m["channel"] for s, m in provider.sources_meta().items()}
    skip = set()
    for issue in provider.injected_issues().get("issues", []):
        brand = issue.get("brand")
        month = issue.get("month")
        source = issue.get("source")
        if not brand or not month or source not in src_channel:
            continue
        skip.add((brand, src_channel[source], month))
    return skip


def _national_slices(provider):
    skip = _corrupted_slices(provider)
    for channel in provider.list_channels():
        cov = provider.coverage_for(channel)
        for month in provider.list_months():
            for brand_info in provider.list_brands():
                brand = brand_info["brand"]
                if (brand, channel, month) in skip:
                    continue
                obs = provider.observed_by_source(channel=channel, month=month, brand=brand)
                if not obs:
                    continue  # source has no history this month (e.g. stackline early)
                truth = provider.true_sales(channel=channel, month=month, brand=brand)
                if truth <= 0:
                    continue
                est = engine.estimate(obs, cov)
                yield brand, channel, month, est, truth


def test_triangulation_recovers_truth_within_tolerance():
    provider = get_provider()
    errors = []
    checked = 0
    for brand, channel, month, est, truth in _national_slices(provider):
        rel_err = abs(est["point"] - truth) / truth
        errors.append(rel_err)
        checked += 1
        assert rel_err < NATIONAL_TOL, (
            f"{brand}/{channel}/{month}: est={est['point']:.0f} truth={truth:.0f} "
            f"err={rel_err:.1%}")
    assert checked > 500, f"expected to check many slices, only did {checked}"
    median = sorted(errors)[len(errors) // 2]
    assert median < 0.03, f"median national error {median:.2%} should be tight"


def test_confidence_band_covers_truth_most_of_the_time():
    provider = get_provider()
    covered = total = 0
    for _brand, _channel, _month, est, truth in _national_slices(provider):
        total += 1
        if est["lower"] <= truth <= est["upper"]:
            covered += 1
    assert total > 0
    rate = covered / total
    assert rate >= COVER_MIN, f"band covered truth only {rate:.1%} of the time"


def test_ecommerce_band_tighter_than_single_source_channels():
    """E-commerce blends two sources, so on average its relative band should be
    tighter than the single-source veterinary channel."""
    provider = get_provider()
    month = provider.list_months()[-1]

    def avg_rel_width(channel):
        cov = provider.coverage_for(channel)
        widths = []
        for b in provider.list_brands():
            obs = provider.observed_by_source(channel=channel, month=month, brand=b["brand"])
            if obs:
                widths.append(engine.estimate(obs, cov)["rel_width"])
        return sum(widths) / len(widths)

    assert avg_rel_width("E-commerce") < avg_rel_width("Veterinary")
