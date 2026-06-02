"""QC scorecard endpoint -- runs the 5-stage validation engine."""
from __future__ import annotations

from fastapi import APIRouter, Query

from app.core import qc_engine
from app.data.provider import get_provider
from app.models.schemas import QCReport

router = APIRouter(prefix="/api", tags=["qc"])


@router.get("/qc", response_model=QCReport)
def qc_report(resolve: bool = Query(False, description="simulate clearing flags to approve delivery")) -> dict:
    """Run all five validation stages over the current data and return the
    scorecard, quality score and delivery-readiness. ``resolve=true`` simulates
    an analyst explicitly clearing flags to approve delivery."""
    provider = get_provider()
    report = qc_engine.run_qc(provider, resolve=resolve)
    # API caps each stage's flag list for payload sanity (flags_raised is true count)
    for stage in report["stages"]:
        stage["flagged"] = stage["flagged"][:qc_engine.API_FLAG_CAP]
    return report


@router.get("/qc/injected", tags=["qc"])
def injected_issues() -> dict:
    """The generator's manifest of injected defects -- shown in the UI as 'what
    QC should catch'. QC detects these independently."""
    return get_provider().injected_issues()
