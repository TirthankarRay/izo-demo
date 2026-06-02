"""FastAPI application entry point for the Zoetis Retail Intelligence Engine.

Wires CORS, mounts one router per capability, and exposes health + catalog.
On startup it guarantees a deterministic seed-42 dataset exists so the platform
runs out-of-the-box with a single command and zero external dependencies.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import (channel, insights, market_share, procurement, qc,
                     triangulation)
from app.data import generator
from app.data.provider import SeedsNotFound, get_provider, reset_provider
from app.models.schemas import Catalog, Health

log = logging.getLogger("rie")


@asynccontextmanager
async def lifespan(_app: FastAPI):
    """Guarantee a deterministic seed-42 dataset exists before serving."""
    try:
        get_provider()
    except SeedsNotFound:
        log.warning("No seeds found -- generating default --seed 42 dataset.")
        generator.generate(seed=42, issues=30)
        reset_provider()
        get_provider()
    yield


app = FastAPI(
    title="Zoetis Retail Intelligence Engine (RIE)",
    description="Market-share triangulation, QC, procurement and insights on "
                "synthetic animal-health data. Phase-1 MVP demo.",
    version="1.0.0",
    lifespan=lifespan,
)

# Open CORS for the demo (no auth, single-tenant, offline).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/health", response_model=Health, tags=["meta"])
def health() -> Health:
    try:
        p = get_provider()
        return Health(status="ok", service="zoetis-rie", seeds_present=True,
                      seed=p.metadata.get("seed"), window=p.metadata.get("window"))
    except SeedsNotFound:
        return Health(status="degraded", service="zoetis-rie", seeds_present=False)


@app.get("/api/catalog", response_model=Catalog, tags=["meta"])
def catalog() -> dict:
    """Everything the UI needs to populate its global filter bar."""
    return get_provider().catalog()


# One router per capability.
app.include_router(market_share.router)
app.include_router(triangulation.router)
app.include_router(channel.router)
app.include_router(qc.router)
app.include_router(procurement.router)
app.include_router(insights.router)


@app.get("/", tags=["meta"])
def root() -> dict:
    return {
        "service": "Zoetis Retail Intelligence Engine",
        "docs": "/docs",
        "capabilities": ["market-share", "triangulation", "channel", "qc",
                         "procurement", "insights"],
        "note": "All data is synthetic. No external calls, no auth.",
    }
