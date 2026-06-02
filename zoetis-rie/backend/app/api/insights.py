"""Insight narratives endpoint -- deterministic, template-driven prose."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core import analytics, narratives
from app.data.provider import get_provider
from app.models.schemas import InsightsResponse

router = APIRouter(prefix="/api", tags=["insights"])


@router.get("/insights", response_model=InsightsResponse)
def insights(
    category: str = Query(..., description="animal-health category"),
    channel: str = Query("All"),
    geo_level: str = Query("National"),
    geo: str = Query("National"),
) -> dict:
    """Plain-language insights for a category slice -- conclusion first, every
    narrative citing its confidence band. No LLM: filled from computed numbers."""
    provider = get_provider()
    facts = analytics.insight_context(provider, category, channel, geo_level, geo)
    items = narratives.build_insights(facts)
    return {
        "category": category,
        "channel": facts["channel"],
        "geo_level": geo_level,
        "geo": geo,
        "period": facts["period"],
        "insights": items,
        "generated_note": ("Generated deterministically from computed estimates "
                           "via string templates -- no LLM, reproducible."),
    }
