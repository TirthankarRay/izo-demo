"""Five-stage data-validation engine -- each stage a pure, testable function.

The QC workflow mirrors a monthly market-intelligence delivery: nothing ships
to the client until every stage is PASS or its flags are explicitly resolved.
The five stages are exactly those in the brief:

    1. File Validation        -- schema, completeness, row counts vs prior period
    2. Statistical Anomaly    -- z-score / IQR outliers, period-over-period limits
    3. Hierarchy Checks       -- SKU->brand mapping, channel + geography rollups
    4. KPI Validation         -- shares sum to 100%, control-total reconciliation,
                                 CI bounds sane
    5. Automated Reporting    -- assemble the delivery package + pass/fail summary

Each ``stage_*`` function takes plain data and returns a result dict with
records_in / records_passed / flags_raised / status and a list of flagged
items. ``run_qc`` is the (impure) orchestrator that pulls data from the
provider, computes the few estimates stage 4 needs, and runs the stages.
"""
from __future__ import annotations

import statistics
from typing import Callable, Optional

# Status / severity vocabulary
PASS, REVIEW, FAIL = "PASS", "REVIEW", "FAIL"
SEV_INFO, SEV_WARN, SEV_FAIL = "info", "warn", "fail"
_SEV_RANK = {SEV_FAIL: 0, SEV_WARN: 1, SEV_INFO: 2}

# The engine keeps ALL flags (so tests + the score see everything); the API
# layer truncates each stage's flag list for payload sanity.
API_FLAG_CAP = 40


# --------------------------------------------------------------------------
# helpers
# --------------------------------------------------------------------------
def _iqr_bounds(values: list[float], k: float = 1.5) -> tuple[float, float]:
    """Tukey fences. Uses quantiles; falls back gracefully on tiny samples."""
    if len(values) < 4:
        lo, hi = min(values), max(values)
        return lo, hi
    s = sorted(values)
    try:
        q1, _, q3 = statistics.quantiles(s, n=4, method="inclusive")
    except statistics.StatisticsError:
        return min(values), max(values)
    iqr = q3 - q1
    return q1 - k * iqr, q3 + k * iqr


def _status_from_flags(flagged: list[dict], warn_review: bool = True) -> str:
    if any(f["severity"] == SEV_FAIL for f in flagged):
        return FAIL
    if warn_review and any(f["severity"] == SEV_WARN for f in flagged):
        return REVIEW
    return PASS


def _result(stage_no: int, name: str, records_in: int, flagged: list[dict],
            summary: str, status: Optional[str] = None) -> dict:
    flags_raised = len(flagged)
    # most important first: fail > warn > info, then by magnitude
    flagged.sort(key=lambda f: (_SEV_RANK.get(f["severity"], 3), -f.pop("_score", 0.0)))
    st = status or _status_from_flags(flagged)
    records_passed = max(0, records_in - flags_raised)
    pass_rate = records_passed / records_in if records_in else 1.0
    # a stage's quality score is its pass rate, capped by status so a REVIEW/FAIL
    # stage cannot look near-perfect just because the bad rows are a small fraction
    cap = {PASS: 100.0, REVIEW: 90.0, FAIL: 75.0}[st]
    score = round(min(pass_rate * 100.0, cap), 1)
    return {
        "stage_no": stage_no,
        "name": name,
        "status": st,
        "records_in": records_in,
        "records_passed": records_passed,
        "flags_raised": flags_raised,
        "score": score,
        "summary": summary,
        "flagged": flagged,
    }


def _flag(stage: str, severity: str, entity: str, reason: str,
          score: float = 0.0, **detail) -> dict:
    return {"stage": stage, "severity": severity, "entity": entity,
            "reason": reason, "_score": float(score), "detail": detail}


# --------------------------------------------------------------------------
# Stage 1 -- File Validation
# --------------------------------------------------------------------------
def stage_file_validation(raw_sources: dict[str, list[dict]],
                          required_columns: list[str],
                          row_drop_tol: float = 0.12) -> dict:
    """Schema, completeness, and row-count-vs-prior-period checks."""
    flagged: list[dict] = []
    records_in = 0
    name = "File Validation"

    for source, rows in raw_sources.items():
        records_in += len(rows)
        # schema: required columns present on every row
        missing_cols = set()
        empty_required = 0
        by_month: dict[str, int] = {}
        keys_by_month: dict[str, set] = {}
        for r in rows:
            for col in required_columns:
                if col not in r:
                    missing_cols.add(col)
            for col in ("month", "geo", "observed_sales"):
                if str(r.get(col, "")).strip() == "":
                    empty_required += 1
            if r.get("geo_level") == "Region":
                by_month[r["month"]] = by_month.get(r["month"], 0) + 1
                keys_by_month.setdefault(r["month"], set()).add(
                    (r["brand_reported"], r["sku_raw"], r["geo"]))
        if missing_cols:
            flagged.append(_flag(name, SEV_FAIL, source,
                                 f"missing required columns: {sorted(missing_cols)}", score=100))
        if empty_required:
            flagged.append(_flag(name, SEV_WARN, source,
                                 f"{empty_required} rows with empty required fields",
                                 score=1.0, empty_rows=empty_required))
        # row counts vs prior period: flag months that drop sharply below the norm
        if by_month:
            counts = sorted(by_month.values())
            median = counts[len(counts) // 2]
            for month in sorted(by_month):
                cnt = by_month[month]
                if median and cnt < median * (1 - row_drop_tol):
                    flagged.append(_flag(
                        name, SEV_WARN, f"{source}/{month}",
                        f"row count {cnt} is {100*(1-cnt/median):.0f}% below prior-period norm {median}",
                        score=1 - cnt / median, count=cnt, expected=median))
        # completeness: a (brand, sku, geo) cell present in most active months but
        # absent in one is a missing row -- catches individual dropped records.
        active_months = sorted(keys_by_month)
        if len(active_months) >= 4:
            freq: dict[tuple, int] = {}
            for keys in keys_by_month.values():
                for k in keys:
                    freq[k] = freq.get(k, 0) + 1
            expected = {k for k, c in freq.items() if c >= 0.8 * len(active_months)}
            for month in active_months:
                for k in sorted(expected - keys_by_month[month]):
                    flagged.append(_flag(
                        name, SEV_WARN, f"{source}/{month}",
                        f"missing expected row: {k[0]} / {k[1]} / {k[2]}",
                        score=2.0, brand=k[0], sku_raw=k[1], geo=k[2]))

    summary = (f"Checked {records_in:,} rows across {len(raw_sources)} feeds; "
               f"{len(flagged)} file-level flag(s).")
    return _result(1, name, records_in, flagged, summary)


# --------------------------------------------------------------------------
# Stage 2 -- Statistical Anomaly Detection
# --------------------------------------------------------------------------
def stage_anomaly_detection(normalized_rows: list[dict], iqr_k: float = 3.0,
                            z_thresh: float = 3.5, min_len: int = 8,
                            mom_limit: float = 0.75) -> dict:
    """IQR + z-score outliers and period-over-period variance limits, per
    (source, brand, channel, geo) monthly series."""
    name = "Statistical Anomaly Detection"
    groups: dict[tuple, list[dict]] = {}
    for r in normalized_rows:
        key = (r["source"], r["brand"], r["channel"], r["geo_level"], r["geo"])
        groups.setdefault(key, []).append(r)

    flagged: list[dict] = []
    records_in = 0
    for key, rows in groups.items():
        rows = sorted(rows, key=lambda x: x["month"])
        values = [x["observed_sales"] for x in rows]
        if len(values) < min_len:
            records_in += len(values)
            continue
        records_in += len(values)
        lo, hi = _iqr_bounds(values, iqr_k)
        mean = statistics.fmean(values)
        sd = statistics.pstdev(values) or 1.0
        source, brand, channel, geo_level, geo = key
        prev = None
        for r in rows:
            v = r["observed_sales"]
            z = (v - mean) / sd
            mom = None if (prev in (None, 0)) else (v - prev) / prev
            reasons = []
            span = (hi - lo) or 1.0
            iqr_dist = max(0.0, (v - hi) / span, (lo - v) / span)
            if v < lo or v > hi:
                reasons.append("IQR outlier")
            if abs(z) > z_thresh:
                reasons.append(f"z={z:.1f}")
            if mom is not None and abs(mom) > mom_limit:
                reasons.append(f"MoM {mom*100:+.0f}%")
            if reasons:
                score = max(abs(z), iqr_dist, abs(mom) if mom is not None else 0.0)
                flagged.append(_flag(
                    name, SEV_WARN,
                    f"{source}/{brand}/{channel}/{geo}/{r['month']}",
                    "; ".join(reasons), score=score,
                    value=round(v, 0), iqr_low=round(lo, 0), iqr_high=round(hi, 0),
                    z=round(z, 2)))
            prev = v

    summary = (f"Scanned {records_in:,} observations across {len(groups)} series; "
               f"flagged {len(flagged)} statistical anomal{'y' if len(flagged)==1 else 'ies'}.")
    return _result(2, name, records_in, flagged, summary)


# --------------------------------------------------------------------------
# Stage 3 -- Hierarchy Checks
# --------------------------------------------------------------------------
def stage_hierarchy_checks(raw_sources: dict[str, list[dict]],
                           variant_keys: set[tuple[str, str]],
                           normalized_rows: list[dict],
                           valid_channels: set[str],
                           source_channel: dict[str, str],
                           rollup_tol: float = 0.05) -> dict:
    """SKU->brand mapping, channel hierarchy, and geography rollups."""
    name = "Hierarchy Checks"
    flagged: list[dict] = []
    records_in = 0

    # 3a. SKU -> brand mapping + channel hierarchy on raw rows
    for source, rows in raw_sources.items():
        for r in rows:
            records_in += 1
            if (source, r["sku_raw"]) not in variant_keys:
                flagged.append(_flag(
                    name, SEV_WARN, f"{source}/{r['sku_raw']}",
                    "SKU does not map to any brand (unmapped)", score=50,
                    month=r.get("month"), geo=r.get("geo")))
            if r.get("channel") not in valid_channels or \
                    r.get("channel") != source_channel.get(source):
                flagged.append(_flag(
                    name, SEV_FAIL, f"{source}/{r['sku_raw']}",
                    f"channel '{r.get('channel')}' invalid for source", score=100))

    # 3b. geography rollup: National should equal sum of regions per (source, brand, month)
    region_sum: dict[tuple, float] = {}
    national: dict[tuple, float] = {}
    for r in normalized_rows:
        key = (r["source"], r["brand"], r["month"])
        if r["geo_level"] == "Region":
            region_sum[key] = region_sum.get(key, 0.0) + r["observed_sales"]
        elif r["geo_level"] == "National":
            national[key] = national.get(key, 0.0) + r["observed_sales"]
    for key, nat in national.items():
        records_in += 1
        rs = region_sum.get(key, 0.0)
        if nat > 0 and abs(nat - rs) / nat > rollup_tol:
            source, brand, month = key
            flagged.append(_flag(
                name, SEV_WARN, f"{source}/{brand}/{month}",
                f"national {nat:,.0f} != sum(regions) {rs:,.0f} "
                f"({100*(nat-rs)/nat:+.0f}%)", score=abs(nat - rs) / nat,
                national=round(nat, 0), region_sum=round(rs, 0)))

    summary = (f"Validated {records_in:,} mapping/rollup checks; "
               f"{len(flagged)} hierarchy flag(s).")
    return _result(3, name, records_in, flagged, summary)


# --------------------------------------------------------------------------
# Stage 4 -- KPI Validation
# --------------------------------------------------------------------------
def stage_kpi_validation(recon_rows: list[dict], share_rows: list[dict],
                         ci_rows: list[dict], recon_tol: float = 0.10,
                         share_eps: float = 0.5) -> dict:
    """Shares sum to 100%, sales reconcile to control totals, CI bounds sane."""
    name = "KPI Validation"
    flagged: list[dict] = []
    records_in = len(recon_rows) + len(share_rows) + len(ci_rows)

    # control-total reconciliation
    for row in recon_rows:
        control = row.get("control_total")
        est = row.get("estimated_total", 0.0)
        if control and control > 0:
            rel = abs(est - control) / control
            if rel > recon_tol:
                flagged.append(_flag(
                    name, SEV_WARN,
                    f"{row['category']}/{row['channel']}/{row['month']}",
                    f"estimate {est:,.0f} vs control {control:,.0f} ({rel*100:.0f}% gap)",
                    score=rel, estimated=round(est, 0), control=round(control, 0)))

    # shares sum to 100%
    for row in share_rows:
        if abs(row["share_sum"] - 100.0) > share_eps:
            flagged.append(_flag(
                name, SEV_FAIL,
                f"{row['category']}/{row['channel']}/{row['geo']}/{row['month']}",
                f"shares sum to {row['share_sum']:.1f}%, not 100%", score=100))

    # CI sanity
    for row in ci_rows:
        if not (row["lower"] <= row["point"] <= row["upper"]) or row["lower"] < 0:
            flagged.append(_flag(
                name, SEV_FAIL, row["entity"],
                f"CI bounds invalid: [{row['lower']:.0f}, {row['point']:.0f}, {row['upper']:.0f}]",
                score=100))

    summary = (f"Reconciled {len(recon_rows)} control totals, checked "
               f"{len(share_rows)} share sums + {len(ci_rows)} CI bounds; "
               f"{len(flagged)} KPI flag(s).")
    return _result(4, name, records_in, flagged, summary)


# --------------------------------------------------------------------------
# Stage 5 -- Automated Reporting
# --------------------------------------------------------------------------
def stage_reporting(stages: list[dict]) -> dict:
    """Assemble the delivery package + overall pass/fail summary."""
    name = "Automated Reporting"
    has_fail = any(s["status"] == FAIL for s in stages)
    has_review = any(s["status"] == REVIEW for s in stages)
    status = FAIL if has_fail else (REVIEW if has_review else PASS)
    total_flags = sum(s["flags_raised"] for s in stages)
    records_in = len(stages)
    flagged: list[dict] = []
    if status != PASS:
        flagged.append(_flag(
            name, SEV_WARN if not has_fail else SEV_FAIL, "delivery-package",
            f"{sum(1 for s in stages if s['status'] != PASS)} of {len(stages)} "
            f"stages need attention ({total_flags} total flags)"))
    summary = (f"Delivery package assembled: overall {status}; "
               f"{total_flags} flag(s) across {len(stages)} stages.")
    return _result(5, name, records_in, flagged, summary, status=status)


# --------------------------------------------------------------------------
# Orchestrator
# --------------------------------------------------------------------------
REQUIRED_COLUMNS = ["source", "month", "category", "brand_reported", "sku_raw",
                    "channel", "geo_level", "geo", "observed_sales", "coverage"]


def run_qc(provider, resolve: bool = False,
           estimate_builder: Optional[Callable] = None) -> dict:
    """Run all five stages against the provider's current data.

    ``resolve=True`` simulates an analyst explicitly clearing the flags so the
    delivery is approved (the "explicitly resolved" path from the brief).
    """
    from app.core import analytics  # local import avoids a cycle

    raw_sources = provider.all_raw_sources()
    normalized = provider.normalized_rows()
    variant_keys = set(provider._variant_map.keys())
    valid_channels = set(provider.list_channels())
    source_channel = {s: m["channel"] for s, m in provider.sources_meta().items()}

    s1 = stage_file_validation(raw_sources, REQUIRED_COLUMNS)
    s2 = stage_anomaly_detection(normalized)
    s3 = stage_hierarchy_checks(raw_sources, variant_keys, normalized,
                                valid_channels, source_channel)

    # Stage 4 inputs: reconcile estimated national category/channel/month totals
    # to finance control totals; verify share sums + CI bounds.
    control_idx = {(c["category"], c["channel"], c["month"]): c["control_total_sales"]
                   for c in provider.control_totals()}
    recon_rows, ci_rows, share_rows = [], [], []
    for category in provider.list_categories():
        for channel in provider.list_channels():
            for month in provider.list_months():
                est = analytics.market_estimate(provider, channel, "National",
                                                "National", [month], category=category)
                if not est:
                    continue
                ctrl = control_idx.get((category, channel, month))
                recon_rows.append({"category": category, "channel": channel,
                                   "month": month, "estimated_total": est["point"],
                                   "control_total": ctrl})
                ci_rows.append({"entity": f"{category}/{channel}/{month}",
                                "lower": est["lower"], "point": est["point"],
                                "upper": est["upper"]})
            # share sum across brands for this category/channel at latest month
        for month in (provider.list_months()[-1],):
            for channel in provider.list_channels():
                table = analytics.market_share_table(
                    provider, category, channel, "National", "National", "month", month)
                share_sum = sum(r["share_pct"] for r in table["rows"])
                if table["rows"]:
                    share_rows.append({"category": category, "channel": channel,
                                       "geo": "National", "month": month,
                                       "share_sum": share_sum})
    s4 = stage_kpi_validation(recon_rows, share_rows, ci_rows)

    stages = [s1, s2, s3, s4]
    s5 = stage_reporting(stages)
    stages.append(s5)

    if resolve:  # analyst explicitly clears flags -> everything approved
        for s in stages:
            s["status"] = PASS
            s["score"] = 100.0

    # composite data-quality score = mean of the four validation stages' scores
    quality_score = round(sum(s["score"] for s in stages[:4]) / 4.0, 1)

    overall = PASS if resolve else s5["status"]
    delivery_ready = overall == PASS
    n_attention = sum(1 for s in stages[:4] if s["status"] != PASS)
    if delivery_ready:
        delivery_note = ("All stages PASS -- delivery package approved, on track "
                         "for the 10th business day.")
    else:
        delivery_note = (f"Delivery on hold: {n_attention} stage(s) need review. "
                         f"Resolve or clear flags to approve delivery.")

    return {
        "overall_status": overall,
        "quality_score": quality_score,
        "delivery_ready": delivery_ready,
        "delivery_by_business_day": 10,
        "delivery_note": delivery_note,
        "stages": stages,
        "totals": {
            "records_checked": sum(s["records_in"] for s in stages[:4]),
            "total_flags": sum(s["flags_raised"] for s in stages[:4]),
            "stages_passing": sum(1 for s in stages if s["status"] == PASS),
            "resolved": resolve,
        },
    }
