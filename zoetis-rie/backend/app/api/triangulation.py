"""Triangulation drill-down endpoint -- how a single estimate was built."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core import analytics
from app.data.provider import get_provider
from app.models.schemas import TriangulationDetail

router = APIRouter(prefix="/api", tags=["triangulation"])


@router.get("/triangulation", response_model=TriangulationDetail)
def triangulation(
    brand: str = Query(..., description="brand to explain"),
    channel: str = Query(..., description="channel (sources differ by channel)"),
    geo_level: str = Query("National"),
    geo: str = Query("National"),
    period_type: str = Query("quarter", pattern="^(month|quarter)$"),
    period: Optional[str] = Query(None),
) -> dict:
    """Show the per-source observed values, coverage gross-up, blend weights and
    the resulting point estimate + 95% band, with a plain-language reading."""
    provider = get_provider()
    return analytics.triangulation_detail(provider, brand, channel, geo_level,
                                          geo, period_type, period)
