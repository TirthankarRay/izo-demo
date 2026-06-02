"""Pydantic request/response contracts shared across the API.

These are mirrored on the frontend in ``src/lib/types.ts``. Keeping the shapes
explicit is the "typed contracts end to end" quality bar from the brief.
"""
from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Shared
# --------------------------------------------------------------------------
class Band(BaseModel):
    """A point estimate with its 95% confidence band."""
    point: float
    lower: float
    upper: float
    rel_width: float = 0.0          # +/- fraction of the point estimate
    confidence: str = "Medium"      # High | Medium | Low


class Health(BaseModel):
    status: str
    service: str
    seeds_present: bool
    seed: Optional[int] = None
    window: Optional[dict] = None


# --------------------------------------------------------------------------
# Catalog
# --------------------------------------------------------------------------
class BrandRef(BaseModel):
    brand: str
    category: str
    is_zoetis: bool
    is_private_label: bool
    role: str


class Catalog(BaseModel):
    categories: list[str]
    channels: list[str]
    brands: list[BrandRef]
    geographies: list[dict]
    geo_levels: list[str]
    months: list[dict]
    quarters: list[str]
    sources: dict
    channel_sources: dict
    window: dict


# --------------------------------------------------------------------------
# Market share / triangulation
# --------------------------------------------------------------------------
class MarketShareRow(BaseModel):
    rank: int
    brand: str
    category: str
    is_zoetis: bool
    is_private_label: bool
    sales: Band
    share_pct: float
    share_lower: float
    share_upper: float


class MarketShareResponse(BaseModel):
    category: str
    channel: str
    geo_level: str
    geo: str
    period_type: str
    period: str
    months: list[str]
    total_sales: Band
    zoetis_brand: Optional[str]
    zoetis_share_pct: float
    rows: list[MarketShareRow]


class SourceContribution(BaseModel):
    source: str
    label: str
    coverage: float
    observed_sales: float
    grossed_up: float
    weight: float


class TriangulationDetail(BaseModel):
    brand: str
    category: str
    is_zoetis: bool
    channel: str
    geo_level: str
    geo: str
    period_type: str
    period: str
    estimate: Band
    n_sources: int
    combined_coverage: float
    rel_dispersion: float
    sources: list[SourceContribution]
    interpretation: str


# --------------------------------------------------------------------------
# Channel view
# --------------------------------------------------------------------------
class ChannelPoint(BaseModel):
    quarter: str
    channel: str
    sales: Band
    mix_pct: float


class ChannelMix(BaseModel):
    channel: str
    start_pct: float
    end_pct: float
    delta_pct: float


class ChannelViewResponse(BaseModel):
    scope: str
    category: Optional[str]
    brand: Optional[str]
    geo_level: str
    geo: str
    quarters: list[str]
    series: list[ChannelPoint]
    mix: list[ChannelMix]
    story: str


# --------------------------------------------------------------------------
# QC
# --------------------------------------------------------------------------
class FlaggedItem(BaseModel):
    stage: str
    severity: str           # info | warn | fail
    entity: str
    reason: str
    detail: dict = Field(default_factory=dict)


class QCStage(BaseModel):
    stage_no: int
    name: str
    status: str             # PASS | REVIEW | FAIL
    records_in: int
    records_passed: int
    flags_raised: int
    score: float            # 0-100 per-stage quality
    summary: str
    flagged: list[FlaggedItem]


class QCReport(BaseModel):
    overall_status: str     # PASS | REVIEW | FAIL
    quality_score: float    # 0-100
    delivery_ready: bool
    delivery_by_business_day: int
    delivery_note: str
    stages: list[QCStage]
    totals: dict


# --------------------------------------------------------------------------
# Procurement
# --------------------------------------------------------------------------
class Criterion(BaseModel):
    key: str
    label: str
    weight: float
    description: str


class VendorScore(BaseModel):
    vendor: str
    label: str
    total_score: float
    rank: int
    is_winner: bool
    per_criterion: dict      # key -> {raw, weighted}


class ScoreRequest(BaseModel):
    weights: Optional[dict[str, float]] = None  # criterion key -> weight (auto-normalized)


class ScoreResponse(BaseModel):
    criteria: list[Criterion]
    vendors: list[VendorScore]
    winner: str
    winner_rationale: str
    normalized_weights: dict[str, float]


class CostRow(BaseModel):
    vendor_path: str
    label: str
    vendor_data_cost: float
    improzo_service_cost: float
    annual_total: float
    note: str


class CostModelResponse(BaseModel):
    service_tier: str
    rows: list[CostRow]
    principle: str
    tiers: list[str]
    disclaimer: str


# --------------------------------------------------------------------------
# Insights
# --------------------------------------------------------------------------
class Insight(BaseModel):
    headline: str
    body: str
    confidence: str
    tags: list[str]
    metrics: dict = Field(default_factory=dict)


class InsightsResponse(BaseModel):
    category: str
    channel: str
    geo_level: str
    geo: str
    period: str
    insights: list[Insight]
    generated_note: str
