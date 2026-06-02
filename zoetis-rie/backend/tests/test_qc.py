"""QC engine tests -- pure stage functions and detection of injected defects.

The brief requires the QC rules to be tested. We test each of the five stages
in isolation on tiny hand-built inputs, then run the full engine against the
seed-42 data and assert it actually catches the defects the generator recorded
in its manifest (unmapped SKUs, hierarchy mismatches, outliers, off control
totals).
"""
from __future__ import annotations

from app.core import qc_engine as qc
from app.data.provider import get_provider


# --------------------------------------------------------------------------
# Pure stage unit tests
# --------------------------------------------------------------------------
def test_stage1_flags_missing_column_and_row_drop():
    rows = []
    # 5 healthy months at 10 region rows each, then a sparse month
    for m in ["2025-01", "2025-02", "2025-03", "2025-04", "2025-05"]:
        for i in range(10):
            rows.append({"source": "s", "month": m, "category": "C", "brand_reported": "B",
                         "sku_raw": f"X{i}", "channel": "Retail", "geo_level": "Region",
                         "geo": "South", "observed_sales": 100.0, "coverage": 0.9})
    for i in range(3):  # big drop
        rows.append({"source": "s", "month": "2025-06", "category": "C", "brand_reported": "B",
                     "sku_raw": f"X{i}", "channel": "Retail", "geo_level": "Region",
                     "geo": "South", "observed_sales": 100.0, "coverage": 0.9})
    res = qc.stage_file_validation({"s": rows}, qc.REQUIRED_COLUMNS)
    assert res["status"] in (qc.REVIEW, qc.FAIL)
    assert any("below prior-period" in f["reason"] for f in res["flagged"])

    # missing a required column -> FAIL
    bad = [{k: v for k, v in rows[0].items() if k != "observed_sales"}]
    res2 = qc.stage_file_validation({"s": bad}, qc.REQUIRED_COLUMNS)
    assert res2["status"] == qc.FAIL


def test_stage2_flags_obvious_spike():
    rows = []
    base = 1000.0
    for i, m in enumerate([f"2025-{mm:02d}" for mm in range(1, 13)]):
        val = base if i != 6 else base * 6  # one spike
        rows.append({"source": "s", "brand": "B", "channel": "Retail",
                     "geo_level": "Region", "geo": "South", "month": m,
                     "observed_sales": val})
    res = qc.stage_anomaly_detection(rows)
    assert res["flags_raised"] >= 1
    assert any("2025-07" in f["entity"] for f in res["flagged"])


def test_stage3_flags_unmapped_and_rollup_mismatch():
    raw = {"s": [
        {"source": "s", "sku_raw": "GOOD", "channel": "Retail", "month": "2025-01", "geo": "South"},
        {"source": "s", "sku_raw": "ORPHAN", "channel": "Retail", "month": "2025-01", "geo": "South"},
    ]}
    variant_keys = {("s", "GOOD")}
    normalized = [
        {"source": "s", "brand": "B", "month": "2025-01", "geo_level": "Region",
         "geo": "South", "observed_sales": 100.0},
        {"source": "s", "brand": "B", "month": "2025-01", "geo_level": "National",
         "geo": "National", "observed_sales": 200.0},  # should be ~100, inflated
    ]
    res = qc.stage_hierarchy_checks(raw, variant_keys, normalized,
                                    {"Retail"}, {"s": "Retail"})
    assert any("unmapped" in f["reason"].lower() for f in res["flagged"])
    assert any("!= sum(regions)" in f["reason"] for f in res["flagged"])


def test_stage4_flags_reconciliation_share_and_ci():
    recon = [{"category": "C", "channel": "Retail", "month": "2025-01",
              "estimated_total": 1000.0, "control_total": 1300.0}]  # 30% gap
    shares = [{"category": "C", "channel": "Retail", "geo": "National",
               "month": "2025-01", "share_sum": 96.0}]  # not 100
    ci = [{"entity": "x", "lower": 50.0, "point": 40.0, "upper": 30.0}]  # inverted
    res = qc.stage_kpi_validation(recon, shares, ci)
    reasons = " ".join(f["reason"] for f in res["flagged"])
    assert "control" in reasons and "100%" in reasons and "CI bounds" in reasons
    assert res["status"] == qc.FAIL  # share + CI are fail-severity


def test_stage5_overall_status():
    mk = lambda st: {"status": st, "flags_raised": 1 if st != qc.PASS else 0}
    assert qc.stage_reporting([mk(qc.PASS), mk(qc.PASS)])["status"] == qc.PASS
    assert qc.stage_reporting([mk(qc.PASS), mk(qc.REVIEW)])["status"] == qc.REVIEW
    assert qc.stage_reporting([mk(qc.FAIL), mk(qc.REVIEW)])["status"] == qc.FAIL


# --------------------------------------------------------------------------
# Full-engine detection against the seed-42 manifest
# --------------------------------------------------------------------------
def _entities(stage):
    return [f["entity"] for f in stage["flagged"]]


def test_run_qc_detects_injected_defects():
    provider = get_provider()
    report = qc.run_qc(provider)
    manifest = provider.injected_issues()["issues"]
    stages = {s["stage_no"]: s for s in report["stages"]}

    # default run should NOT be clean -- QC must catch the injected mess
    assert report["overall_status"] in (qc.REVIEW, qc.FAIL)
    assert report["delivery_ready"] is False
    assert 0 <= report["quality_score"] <= 100

    # --- unmapped SKUs (stage 3) ---
    unmapped = [m for m in manifest if m["type"] == "unmapped_sku"]
    s3_entities = " | ".join(_entities(stages[3]))
    for m in unmapped:
        assert m["sku_raw"] in s3_entities, f"unmapped SKU {m['sku_raw']} not flagged"

    # --- hierarchy mismatches (stage 3) ---
    for m in [x for x in manifest if x["type"] == "hierarchy_mismatch"]:
        token = f"{m['source']}/{m['brand']}/{m['month']}"
        assert token in s3_entities, f"hierarchy mismatch {token} not flagged"

    # --- outliers (stage 2): catch the large majority ---
    outliers = [m for m in manifest if m["type"] == "outlier"]
    s2_keys = set()
    for f in stages[2]["flagged"]:
        parts = f["entity"].split("/")  # source/brand/channel/geo/month
        if len(parts) == 5:
            s2_keys.add((parts[0], parts[1], parts[3], parts[4]))
    caught = sum(1 for m in outliers
                 if (m["source"], m["brand"], m["geo"], m["month"]) in s2_keys)
    assert caught / len(outliers) >= 0.8, f"only caught {caught}/{len(outliers)} outliers"

    # --- off control totals (stage 4) ---
    s4_entities = " | ".join(_entities(stages[4]))
    for m in [x for x in manifest if x["type"] == "control_total_off"]:
        token = f"{m['category']}/{m['channel']}/{m['month']}"
        assert token in s4_entities, f"control-total defect {token} not flagged"


def test_run_qc_resolve_approves_delivery():
    provider = get_provider()
    report = qc.run_qc(provider, resolve=True)
    assert report["overall_status"] == qc.PASS
    assert report["delivery_ready"] is True
    assert all(s["status"] == qc.PASS for s in report["stages"])
