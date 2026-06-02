"""Market-share + leaderboard endpoint."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core import analytics
from app.data.provider import get_provider
from app.models.schemas import MarketShareResponse

router = APIRouter(prefix="/api", tags=["market-share"])


@router.get("/market-share", response_model=MarketShareResponse)
def market_share(
    category: str = Query(..., description="animal-health category"),
    channel: str = Query("All", description="channel or 'All'"),
    geo_level: str = Query("National"),
    geo: str = Query("National"),
    period_type: str = Query("quarter", pattern="^(month|quarter)$"),
    period: Optional[str] = Query(None, description="month/quarter id or 'latest'"),
) -> dict:
    """Estimated sales + market share per brand for a category slice, ranked,
    each with a 95% confidence band. The Zoetis brand is flagged via is_zoetis."""
    provider = get_provider()
    return analytics.market_share_table(provider, category, channel, geo_level,
                                        geo, period_type, period)
