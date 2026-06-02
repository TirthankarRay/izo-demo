"""Procurement decision tool -- weighted vendor scoring + cost model."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core import scoring
from app.models.schemas import CostModelResponse, ScoreRequest, ScoreResponse

router = APIRouter(prefix="/api/procurement", tags=["procurement"])


@router.get("/score", response_model=ScoreResponse)
def score_default() -> dict:
    """Vendor ranking at the default criterion weights."""
    return scoring.score_vendors(None)


@router.post("/score", response_model=ScoreResponse)
def score(req: ScoreRequest) -> dict:
    """Re-rank vendors for user-adjusted criterion weights (auto-normalized).
    This is what the live sliders call on every change."""
    return scoring.score_vendors(req.weights)


@router.get("/cost", response_model=CostModelResponse)
def cost(tier: str = Query(scoring.DEFAULT_TIER, description="Improzo service tier")) -> dict:
    """Annual cost by vendor path for a chosen Improzo service tier, with the
    pass-through / zero-markup principle made explicit."""
    return scoring.cost_model(tier)
