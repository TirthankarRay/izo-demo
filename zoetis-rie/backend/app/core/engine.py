"""Triangulation + confidence-interval math -- PURE functions, no I/O.

This is the analytical heart of the RIE. Every function here takes plain
numbers / dicts and returns plain numbers / dicts. It never reads a file, never
calls the provider, never touches the network. That keeps the math trivially
unit-testable against ground truth and means it is identical whether the inputs
came from synthetic seeds or real vendor feeds.

Triangulation model
-------------------
Each source observes ``observed = true_sales * coverage * bias * (1 + noise)``
for the channel it covers. We recover an estimate of the truth by grossing each
source up by its coverage and blending the covering sources, weighted by
coverage (more coverage == more reliable):

    point = sum(observed_s) / sum(coverage_s)         # == coverage-weighted
                                                       #    mean of observed/coverage

Confidence interval
-------------------
A 95% band is built from two ingredients, exactly as the brief asks:
  * cross-source dispersion -- how much the grossed-up sources disagree, and
  * coverage gap -- how much of the channel the combined sources miss.
Narrow band when sources agree and coverage is high; wide band otherwise.
Single-source channels (retail, vet) get a modest penalty because there is no
second source to cross-check them.
"""
from __future__ import annotations

import math
import statistics
from typing import Optional

# Tunable constants (documented so analysts can defend the numbers).
Z95 = 1.96                      # 95% normal critical value
COVERAGE_ALPHA = 0.5            # how strongly a coverage gap widens the band
SINGLE_SOURCE_PENALTY = 0.015   # extra rel. uncertainty when only one source
MIN_REL_UNCERTAINTY = 0.012     # floor so a band never collapses to zero


def gross_up(observed: float, coverage: float) -> float:
    """Scale an observed (partial-coverage) value up to a full-market estimate."""
    if coverage <= 0:
        return 0.0
    return observed / coverage


def combined_coverage(coverages: list[float]) -> float:
    """Union coverage of independent sources: 1 - prod(1 - c_i).

    Two e-commerce sources at 0.82 and 0.88 together cover ~0.978 -- more than
    either alone, which is why blending tightens the band.
    """
    prod_missing = 1.0
    for c in coverages:
        prod_missing *= (1.0 - max(0.0, min(1.0, c)))
    return 1.0 - prod_missing


def triangulate(observed_by_source: dict[str, float],
                coverage_by_source: dict[str, float]) -> dict:
    """Blend covering sources into a single coverage-weighted point estimate.

    Only sources present in ``observed_by_source`` with positive coverage
    contribute. Returns the point estimate plus the intermediate quantities
    (per-source grossed-up estimates, weights, dispersion) that the CI needs.
    """
    contributing = {
        s: observed_by_source[s]
        for s in observed_by_source
        if coverage_by_source.get(s, 0.0) > 0.0
    }
    if not contributing:
        return {"point": 0.0, "n_sources": 0, "sources": {},
                "grossed_up": {}, "weights": {}, "rel_dispersion": 0.0,
                "combined_coverage": 0.0}

    cov = {s: coverage_by_source[s] for s in contributing}
    grossed = {s: gross_up(contributing[s], cov[s]) for s in contributing}

    total_cov = sum(cov.values())
    # coverage-weighted mean of grossed-up estimates == sum(obs)/sum(cov)
    point = sum(contributing.values()) / total_cov if total_cov else 0.0
    weights = {s: cov[s] / total_cov for s in cov} if total_cov else {}

    est_values = list(grossed.values())
    if len(est_values) >= 2 and point > 0:
        rel_dispersion = statistics.stdev(est_values) / point
    else:
        rel_dispersion = 0.0

    return {
        "point": point,
        "n_sources": len(contributing),
        "sources": contributing,
        "grossed_up": grossed,
        "weights": weights,
        "rel_dispersion": rel_dispersion,
        "combined_coverage": combined_coverage(list(cov.values())),
    }


def relative_uncertainty(rel_dispersion: float, comb_coverage: float,
                         n_sources: int) -> float:
    """Combine dispersion + coverage gap (+ single-source penalty) in quadrature."""
    coverage_gap = max(0.0, 1.0 - comb_coverage)
    single = SINGLE_SOURCE_PENALTY if n_sources <= 1 else 0.0
    return math.sqrt(
        rel_dispersion ** 2
        + (COVERAGE_ALPHA * coverage_gap) ** 2
        + single ** 2
        + MIN_REL_UNCERTAINTY ** 2
    )


def confidence_interval(point: float, rel_dispersion: float,
                        comb_coverage: float, n_sources: int) -> dict:
    """95% band around ``point`` from dispersion + coverage. Pure."""
    if point <= 0:
        return {"lower": 0.0, "upper": 0.0, "half_width": 0.0,
                "rel_width": 0.0, "rel_uncertainty": 0.0}
    u = relative_uncertainty(rel_dispersion, comb_coverage, n_sources)
    half_width = Z95 * u * point
    lower = max(0.0, point - half_width)
    upper = point + half_width
    return {
        "lower": lower,
        "upper": upper,
        "half_width": half_width,
        "rel_width": half_width / point,   # +/- fraction of the point estimate
        "rel_uncertainty": u,
    }


def estimate(observed_by_source: dict[str, float],
             coverage_by_source: dict[str, float]) -> dict:
    """Full estimate for one brand-channel-geo-period slice: point + 95% band."""
    tri = triangulate(observed_by_source, coverage_by_source)
    ci = confidence_interval(
        tri["point"], tri["rel_dispersion"],
        tri["combined_coverage"], tri["n_sources"],
    )
    return {
        "point": tri["point"],
        "lower": ci["lower"],
        "upper": ci["upper"],
        "half_width": ci["half_width"],
        "rel_width": ci["rel_width"],
        "rel_uncertainty": ci["rel_uncertainty"],
        "n_sources": tri["n_sources"],
        "combined_coverage": tri["combined_coverage"],
        "rel_dispersion": tri["rel_dispersion"],
        "source_estimates": tri["grossed_up"],
        "weights": tri["weights"],
    }


def aggregate_estimates(estimates: list[dict]) -> dict:
    """Aggregate independent slice estimates (e.g. regions -> national, or
    channels -> total brand). Points sum; half-widths combine in quadrature
    (assuming independence), so the aggregate band is proportionally tighter.
    """
    points = [e["point"] for e in estimates]
    point = sum(points)
    half = math.sqrt(sum(e["half_width"] ** 2 for e in estimates))
    if point <= 0:
        return {"point": 0.0, "lower": 0.0, "upper": 0.0,
                "half_width": 0.0, "rel_width": 0.0}
    return {
        "point": point,
        "lower": max(0.0, point - half),
        "upper": point + half,
        "half_width": half,
        "rel_width": half / point,
    }


def market_share(brand_point: float, total_point: float) -> float:
    """Brand share of a category/channel/geo/period total, in percent."""
    if total_point <= 0:
        return 0.0
    return 100.0 * brand_point / total_point


def share_band(brand_lower: float, brand_upper: float, total_point: float) -> tuple[float, float]:
    """Approximate 95% band on a share %, propagating the brand band against a
    (treated-as-fixed) category total."""
    if total_point <= 0:
        return 0.0, 0.0
    return 100.0 * brand_lower / total_point, 100.0 * brand_upper / total_point


def relative_change(curr: float, prior: float) -> Optional[float]:
    """Percent change curr vs prior, or None if prior is zero/undefined."""
    if prior is None or prior == 0:
        return None
    return 100.0 * (curr - prior) / prior
