"""Analytics orchestration -- composes the pure engine over provider data.

This is the service layer that sits between the HTTP routes and the two lower
layers it depends on:
  * ``data/provider.py`` for normalized observations + coverage (I/O), and
  * ``core/engine.py`` for triangulation + CI (pure math).

It owns the looping/aggregation logic (over brands, channels, geographies,
months) that turns raw per-source observations into the estimate tables the UI
consumes. It contains no file or network I/O of its own and no invented
numbers -- only composition. Swapping synthetic seeds for real feeds changes
the provider's internals; this layer is untouched.
"""
from __future__ import annotations

from typing import Optional

from app.core import engine
from app.data.provider import DataProvider


# --------------------------------------------------------------------------
# Small helpers
# --------------------------------------------------------------------------
def confidence_label(rel_width: float) -> str:
    """Map a band's +/- fraction to a High/Medium/Low confidence label."""
    if rel_width <= 0.06:
        return "High"
    if rel_width <= 0.12:
        return "Medium"
    return "Low"


def band_dict(est: Optional[dict]) -> dict:
    """Normalize an engine estimate into the API Band shape (+ confidence)."""
    if not est or est.get("point", 0) <= 0:
        return {"point": 0.0, "lower": 0.0, "upper": 0.0,
                "rel_width": 0.0, "confidence": "Low"}
    rel = est.get("rel_width", 0.0)
    return {
        "point": round(est["point"], 2),
        "lower": round(est["lower"], 2),
        "upper": round(est["upper"], 2),
        "rel_width": round(rel, 4),
        "confidence": confidence_label(rel),
    }


def resolve_period(provider: DataProvider, period_type: str,
                   period: Optional[str]) -> tuple[str, str, list[str]]:
    """Return (period_type, period_label, months) for a period selector.

    period_type in {"month", "quarter"}; a missing/"latest" period defaults to
    the most recent of that type.
    """
    if period_type == "quarter":
        quarters = provider.list_quarters()
        if not period or period == "latest" or period not in quarters:
            period = quarters[-1]
        return "quarter", period, provider.months_for_quarter(period)
    months = provider.list_months()
    if not period or period == "latest" or period not in months:
        period = months[-1]
    return "month", period, [period]


def channels_for(provider: DataProvider, channel: Optional[str]) -> list[str]:
    if channel and channel != "All" and channel in provider.list_channels():
        return [channel]
    return provider.list_channels()


# --------------------------------------------------------------------------
# Core estimate primitives
# --------------------------------------------------------------------------
def brand_channel_estimate(provider: DataProvider, brand: str, channel: str,
                           geo_level: str, geo: str, months: list[str]) -> Optional[dict]:
    """Estimate for one brand in one channel, summed over ``months``."""
    cov = provider.coverage_for(channel)
    per_month = []
    for m in months:
        obs = provider.observed_by_source(channel=channel, month=m, brand=brand,
                                          geo_level=geo_level, geo=geo)
        if obs:
            per_month.append(engine.estimate(obs, cov))
    if not per_month:
        return None
    agg = engine.aggregate_estimates(per_month)
    return agg


def brand_estimate(provider: DataProvider, brand: str, channels: list[str],
                   geo_level: str, geo: str, months: list[str]
                   ) -> tuple[Optional[dict], dict]:
    """Estimate for one brand across ``channels`` (+ per-channel breakdown)."""
    per_channel = {}
    for ch in channels:
        e = brand_channel_estimate(provider, brand, ch, geo_level, geo, months)
        if e:
            per_channel[ch] = e
    if not per_channel:
        return None, {}
    return engine.aggregate_estimates(list(per_channel.values())), per_channel


def market_estimate(provider: DataProvider, channel: str, geo_level: str, geo: str,
                    months: list[str], category: Optional[str] = None,
                    brand: Optional[str] = None) -> Optional[dict]:
    """Aggregate estimate over a set of brands (filtered) for one channel,
    summed across ``months``. Used for channel-mix and market totals."""
    cov = provider.coverage_for(channel)
    brand_list = [brand] if brand else [b["brand"] for b in provider.list_brands(category)]
    per_month = []
    for m in months:
        slice_ests = []
        for br in brand_list:
            obs = provider.observed_by_source(channel=channel, month=m, brand=br,
                                              geo_level=geo_level, geo=geo)
            if obs:
                slice_ests.append(engine.estimate(obs, cov))
        if slice_ests:
            per_month.append(engine.aggregate_estimates(slice_ests))
    if not per_month:
        return None
    return engine.aggregate_estimates(per_month)


# --------------------------------------------------------------------------
# Market share leaderboard
# --------------------------------------------------------------------------
def market_share_table(provider: DataProvider, category: str, channel: str,
                       geo_level: str, geo: str, period_type: str,
                       period: Optional[str]) -> dict:
    period_type, period_label, months = resolve_period(provider, period_type, period)
    channels = channels_for(provider, channel)
    channel_label = channel if (channel and channel != "All") else "All channels"

    estimates: dict[str, dict] = {}
    for b in provider.list_brands(category):
        agg, _ = brand_estimate(provider, b["brand"], channels, geo_level, geo, months)
        if agg:
            estimates[b["brand"]] = {"info": b, "est": agg}

    total_point = sum(v["est"]["point"] for v in estimates.values())
    total_lower = sum(v["est"]["lower"] for v in estimates.values())
    total_upper = sum(v["est"]["upper"] for v in estimates.values())

    rows = []
    zoetis_brand = None
    zoetis_share = 0.0
    for brand, v in estimates.items():
        est, info = v["est"], v["info"]
        share = engine.market_share(est["point"], total_point)
        slo, shi = engine.share_band(est["lower"], est["upper"], total_point)
        if info["is_zoetis"]:
            zoetis_brand = brand
            zoetis_share = share
        rows.append({
            "brand": brand,
            "category": info["category"],
            "is_zoetis": info["is_zoetis"],
            "is_private_label": info["is_private_label"],
            "sales": band_dict(est),
            "share_pct": round(share, 2),
            "share_lower": round(slo, 2),
            "share_upper": round(shi, 2),
        })
    rows.sort(key=lambda r: r["sales"]["point"], reverse=True)
    for i, r in enumerate(rows, 1):
        r["rank"] = i

    total_rel = (total_upper - total_point) / total_point if total_point else 0.0
    return {
        "category": category,
        "channel": channel_label,
        "geo_level": geo_level,
        "geo": geo,
        "period_type": period_type,
        "period": period_label,
        "months": months,
        "total_sales": {
            "point": round(total_point, 2), "lower": round(total_lower, 2),
            "upper": round(total_upper, 2), "rel_width": round(total_rel, 4),
            "confidence": confidence_label(total_rel),
        },
        "zoetis_brand": zoetis_brand,
        "zoetis_share_pct": round(zoetis_share, 2),
        "rows": rows,
    }


# --------------------------------------------------------------------------
# Triangulation drill-down (how one number was built)
# --------------------------------------------------------------------------
def triangulation_detail(provider: DataProvider, brand: str, channel: str,
                         geo_level: str, geo: str, period_type: str,
                         period: Optional[str]) -> dict:
    period_type, period_label, months = resolve_period(provider, period_type, period)
    cov = provider.coverage_for(channel)
    sources_meta = provider.sources_meta()

    # Sum observed per source across the period months, then build the estimate.
    observed_sum: dict[str, float] = {}
    for m in months:
        for src, val in provider.observed_by_source(
                channel=channel, month=m, brand=brand, geo_level=geo_level, geo=geo).items():
            observed_sum[src] = observed_sum.get(src, 0.0) + val

    est = engine.estimate(observed_sum, cov)
    info = provider.brand_info(brand) or {}

    contributions = []
    for src, observed in sorted(observed_sum.items()):
        contributions.append({
            "source": src,
            "label": sources_meta.get(src, {}).get("label", src),
            "coverage": cov.get(src, 0.0),
            "observed_sales": round(observed, 2),
            "grossed_up": round(est["source_estimates"].get(src, 0.0), 2),
            "weight": round(est["weights"].get(src, 0.0), 4),
        })

    # Plain-language interpretation of the construction.
    n = est["n_sources"]
    if n >= 2:
        agree = "closely" if est["rel_dispersion"] < 0.03 else "broadly"
        interp = (
            f"{channel} blends {n} sources covering ~{est['combined_coverage']*100:.0f}% "
            f"of the channel; they agree {agree} (dispersion {est['rel_dispersion']*100:.1f}%), "
            f"so the 95% band is +/-{est['rel_width']*100:.1f}%."
        )
    elif n == 1:
        only = contributions[0]["label"] if contributions else "a single source"
        interp = (
            f"{channel} is estimated from {only} alone (~{est['combined_coverage']*100:.0f}% "
            f"coverage). With no second source to cross-check, the band is wider: "
            f"+/-{est['rel_width']*100:.1f}%."
        )
    else:
        interp = "No source covers this slice."

    return {
        "brand": brand,
        "category": info.get("category", ""),
        "is_zoetis": info.get("is_zoetis", False),
        "channel": channel,
        "geo_level": geo_level,
        "geo": geo,
        "period_type": period_type,
        "period": period_label,
        "estimate": band_dict(est),
        "n_sources": est["n_sources"],
        "combined_coverage": round(est["combined_coverage"], 4),
        "rel_dispersion": round(est["rel_dispersion"], 4),
        "sources": contributions,
        "interpretation": interp,
    }


# --------------------------------------------------------------------------
# Channel view (split + trend + mix story)
# --------------------------------------------------------------------------
def channel_view(provider: DataProvider, category: Optional[str], brand: Optional[str],
                 geo_level: str, geo: str) -> dict:
    quarters = provider.list_quarters()
    channels = provider.list_channels()
    series = []
    # per-quarter channel sales
    quarter_totals: dict[str, float] = {}
    quarter_channel: dict[tuple[str, str], dict] = {}
    for q in quarters:
        months = provider.months_for_quarter(q)
        qtotal = 0.0
        for ch in channels:
            est = market_estimate(provider, ch, geo_level, geo, months,
                                  category=category, brand=brand)
            est = est or {"point": 0, "lower": 0, "upper": 0, "rel_width": 0}
            quarter_channel[(q, ch)] = est
            qtotal += est["point"]
        quarter_totals[q] = qtotal
        for ch in channels:
            est = quarter_channel[(q, ch)]
            mix = (100.0 * est["point"] / qtotal) if qtotal else 0.0
            series.append({
                "quarter": q,
                "channel": ch,
                "sales": band_dict(est),
                "mix_pct": round(mix, 2),
            })

    # mix at first vs last quarter -> the story
    first_q, last_q = quarters[0], quarters[-1]
    mix = []
    for ch in channels:
        s = quarter_channel[(first_q, ch)]["point"]
        e = quarter_channel[(last_q, ch)]["point"]
        st = (100.0 * s / quarter_totals[first_q]) if quarter_totals[first_q] else 0.0
        en = (100.0 * e / quarter_totals[last_q]) if quarter_totals[last_q] else 0.0
        mix.append({"channel": ch, "start_pct": round(st, 2),
                    "end_pct": round(en, 2), "delta_pct": round(en - st, 2)})

    ecom = next((m for m in mix if m["channel"] == "E-commerce"), None)
    vet = next((m for m in mix if m["channel"] == "Veterinary"), None)
    scope_label = brand or category or "the market"
    if ecom and vet:
        story = (
            f"Across {first_q}->{last_q}, e-commerce share of {scope_label} rose "
            f"{ecom['delta_pct']:+.1f} pts to {ecom['end_pct']:.1f}% while veterinary "
            f"eroded {vet['delta_pct']:+.1f} pts to {vet['end_pct']:.1f}%. "
            f"Channel mix is shifting online."
        )
    else:
        story = "Channel mix trend over the trailing eight quarters."

    scope = "brand" if brand else ("category" if category else "market")
    return {
        "scope": scope, "category": category, "brand": brand,
        "geo_level": geo_level, "geo": geo, "quarters": quarters,
        "series": series, "mix": mix, "story": story,
    }


def _primary_channel(provider: DataProvider, brand: str, geo_level: str,
                     geo: str, months: list[str]) -> str:
    """The channel where ``brand`` sells most over ``months`` (for narratives)."""
    best, best_val = provider.list_channels()[0], -1.0
    for ch in provider.list_channels():
        e = brand_channel_estimate(provider, brand, ch, geo_level, geo, months)
        if e and e["point"] > best_val:
            best, best_val = ch, e["point"]
    return best


def insight_context(provider: DataProvider, category: str, channel: str,
                    geo_level: str, geo: str) -> dict:
    """Compute the structured facts the narrative templates fill in.

    Compares the latest quarter to the prior quarter for share moves and
    competitive swings, and reads source agreement for the Zoetis brand's
    primary channel.
    """
    quarters = provider.list_quarters()
    period, prior = quarters[-1], quarters[-2]
    now = market_share_table(provider, category, channel, geo_level, geo, "quarter", period)
    prev = market_share_table(provider, category, channel, geo_level, geo, "quarter", prior)
    prior_share = {r["brand"]: r["share_pct"] for r in prev["rows"]}

    zbrand = now["zoetis_brand"]
    z_row = next((r for r in now["rows"] if r["brand"] == zbrand), None)
    z_share_now = now["zoetis_share_pct"]
    z_share_prior = prior_share.get(zbrand, z_share_now)

    deltas = [
        {"brand": r["brand"], "delta": round(r["share_pct"] - prior_share.get(r["brand"], r["share_pct"]), 2),
         "is_zoetis": r["is_zoetis"]}
        for r in now["rows"]
    ]
    top_mover = max(deltas, key=lambda x: x["delta"]) if deltas else None
    top_decliner = min(deltas, key=lambda x: x["delta"]) if deltas else None

    cv = channel_view(provider, category, None, geo_level, geo)

    primary = channel if (channel and channel != "All") else _primary_channel(
        provider, zbrand, geo_level, geo, provider.months_for_quarter(period))
    tri = triangulation_detail(provider, zbrand, primary, geo_level, geo, "quarter", period)

    z_sales = z_row["sales"] if z_row else {"point": 0, "lower": 0, "upper": 0,
                                            "rel_width": 0, "confidence": "Low"}
    return {
        "category": category,
        "channel": now["channel"],
        "geo_level": geo_level,
        "geo": geo,
        "period": period,
        "prior_period": prior,
        "zoetis_brand": zbrand,
        "zoetis_share_now": z_share_now,
        "zoetis_share_prior": z_share_prior,
        "zoetis_share_delta": round(z_share_now - z_share_prior, 2),
        "zoetis_rank": z_row["rank"] if z_row else 0,
        "zoetis_sales": z_sales,
        "channel_mix": cv["mix"],
        "top_mover": top_mover,
        "top_decliner": top_decliner,
        "source_agreement": {"dispersion": tri["rel_dispersion"],
                             "n_sources": tri["n_sources"], "channel": primary},
        "low_confidence": z_sales["confidence"] == "Low",
    }
