"""End-to-end API smoke tests via FastAPI TestClient (offline, in-process)."""
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_and_catalog():
    h = client.get("/api/health").json()
    assert h["status"] == "ok" and h["seeds_present"]

    cat = client.get("/api/catalog").json()
    assert len(cat["categories"]) == 5
    assert len(cat["brands"]) == 25
    assert set(cat["channels"]) == {"Veterinary", "Retail", "E-commerce"}
    assert any(b["is_zoetis"] for b in cat["brands"])


def test_market_share_endpoint():
    r = client.get("/api/market-share", params={
        "category": "Parasiticides", "channel": "All",
        "period_type": "quarter", "period": "latest"})
    assert r.status_code == 200
    data = r.json()
    assert len(data["rows"]) == 5
    # shares sum to ~100 and exactly one Zoetis brand is flagged + named
    assert sum(row["share_pct"] for row in data["rows"]) == pytest.approx(100.0, abs=0.5)
    assert sum(1 for row in data["rows"] if row["is_zoetis"]) == 1
    assert data["zoetis_brand"] is not None
    # every row carries a well-formed band
    for row in data["rows"]:
        s = row["sales"]
        assert s["lower"] <= s["point"] <= s["upper"]
        assert s["confidence"] in ("High", "Medium", "Low")
    # ranked descending by sales
    pts = [row["sales"]["point"] for row in data["rows"]]
    assert pts == sorted(pts, reverse=True)


def test_triangulation_endpoint_ecommerce_blends_two_sources():
    r = client.get("/api/triangulation", params={
        "brand": "Simparica Trio", "channel": "E-commerce",
        "period_type": "quarter", "period": "latest"})
    data = r.json()
    assert data["n_sources"] == 2
    srcs = {s["source"] for s in data["sources"]}
    assert srcs == {"ciq_ecommerce", "stackline_ecommerce"}
    assert abs(sum(s["weight"] for s in data["sources"]) - 1.0) < 1e-6
    assert data["estimate"]["lower"] <= data["estimate"]["point"] <= data["estimate"]["upper"]
    assert "band" in data["interpretation"].lower() or "+/-" in data["interpretation"]


def test_channel_view_shows_ecom_rising_vet_eroding():
    r = client.get("/api/channel", params={"category": "Parasiticides"})
    data = r.json()
    assert len(data["quarters"]) == 8
    mix = {m["channel"]: m for m in data["mix"]}
    assert mix["E-commerce"]["delta_pct"] > 0     # e-commerce rising
    assert mix["Veterinary"]["delta_pct"] < 0     # veterinary eroding
    assert "e-commerce" in data["story"].lower()


def test_qc_endpoint_blocks_then_resolves():
    blocked = client.get("/api/qc").json()
    assert len(blocked["stages"]) == 5
    assert blocked["delivery_ready"] is False
    assert blocked["overall_status"] in ("REVIEW", "FAIL")
    assert 0 <= blocked["quality_score"] <= 100

    ready = client.get("/api/qc", params={"resolve": True}).json()
    assert ready["delivery_ready"] is True
    assert ready["overall_status"] == "PASS"


def test_procurement_score_and_cost():
    default = client.get("/api/procurement/score").json()
    assert default["winner"] == "Stackline"

    posted = client.post("/api/procurement/score", json={"weights": {
        "historical_depth": 0.55, "cost_efficiency": 0.37, "sku_granularity": 0.02,
        "retailer_coverage": 0.02, "refresh_frequency": 0.02, "integration_ease": 0.02}}).json()
    assert posted["winner"] == "CIQ"

    cost = client.get("/api/procurement/cost", params={"tier": "Enterprise"}).json()
    assert cost["service_tier"] == "Enterprise"
    assert any(r["vendor_path"] == "ciq_stackline" for r in cost["rows"])


def test_insights_endpoint():
    r = client.get("/api/insights", params={"category": "Parasiticides", "channel": "All"})
    data = r.json()
    assert len(data["insights"]) >= 3
    assert all({"headline", "body", "confidence"} <= set(i) for i in data["insights"])
    assert "band" in " ".join(i["body"] for i in data["insights"]).lower()
