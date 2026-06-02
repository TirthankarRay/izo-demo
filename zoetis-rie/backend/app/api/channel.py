"""Channel-view endpoint -- vet/retail/e-comm split, trend and mix story."""
from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Query

from app.core import analytics
from app.data.provider import get_provider
from app.models.schemas import ChannelViewResponse

router = APIRouter(prefix="/api", tags=["channel"])


@router.get("/channel", response_model=ChannelViewResponse)
def channel_view(
    category: Optional[str] = Query(None, description="filter to one category"),
    brand: Optional[str] = Query(None, description="filter to one brand"),
    geo_level: str = Query("National"),
    geo: str = Query("National"),
) -> dict:
    """Per-quarter channel sales (with bands) + channel-mix percentages over the
    trailing eight quarters, surfacing the e-commerce-rising / vet-eroding story."""
    provider = get_provider()
    return analytics.channel_view(provider, category, brand, geo_level, geo)
