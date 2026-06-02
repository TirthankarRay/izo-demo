"""Template-driven insight narratives -- PURE, deterministic, no LLM.

Natural-language insights are assembled from string templates filled with the
already-computed numbers (share moves, channel shifts, source agreement, CI
width). There is no model call and no randomness: the same facts always yield
the same prose, so a demo reproduces exactly and a client deliverable reads the
same every month.

Style: conclusion first, evidence second, no fluff. Every narrative cites the
confidence band and explicitly flags low-confidence estimates.
"""
from __future__ import annotations

from typing import Optional


def _fmt_usd(v: float) -> str:
    if v >= 1_000_000_000:
        return f"${v/1_000_000_000:.2f}B"
    if v >= 1_000_000:
        return f"${v/1_000_000:.1f}M"
    if v >= 1_000:
        return f"${v/1_000:.0f}K"
    return f"${v:.0f}"


def _pts(v: float) -> str:
    return f"{v:+.1f} pts"


def _confidence_phrase(confidence: str, rel_width: float) -> str:
    band = f"+/-{rel_width*100:.1f}%"
    if confidence == "High":
        return f"high confidence ({band} band)"
    if confidence == "Medium":
        return f"moderate confidence ({band} band)"
    return f"LOW confidence ({band} band) -- treat directionally"


# --------------------------------------------------------------------------
# Individual narrative templates -- each returns an Insight dict or None
# --------------------------------------------------------------------------
def _share_move(f: dict) -> Optional[dict]:
    delta = f["zoetis_share_delta"]
    brand = f["zoetis_brand"]
    if brand is None:
        return None
    direction = "gained" if delta >= 0 else "ceded"
    verb = "extends its lead" if (delta >= 0 and f["zoetis_rank"] == 1) else (
        "closes the gap" if delta >= 0 else "slips")
    headline = (f"{brand} {verb}: {abs(delta):.1f} pts {('to' if delta>=0 else 'to')} "
                f"{f['zoetis_share_now']:.1f}% share in {f['category']}")
    body = (
        f"In {f['period']}, {brand} (Zoetis) holds {f['zoetis_share_now']:.1f}% of the "
        f"{f['category']} / {f['channel']} market at {f['geo']} -- {direction} "
        f"{_pts(delta)} versus {f['prior_period']}. Estimated sales "
        f"{_fmt_usd(f['zoetis_sales']['point'])} "
        f"({_fmt_usd(f['zoetis_sales']['lower'])}-{_fmt_usd(f['zoetis_sales']['upper'])}, "
        f"{_confidence_phrase(f['zoetis_sales']['confidence'], f['zoetis_sales']['rel_width'])}), "
        f"ranked #{f['zoetis_rank']}."
    )
    return {"headline": headline, "body": body,
            "confidence": f["zoetis_sales"]["confidence"],
            "tags": ["market share", "zoetis"],
            "metrics": {"share_now": f["zoetis_share_now"],
                        "share_delta": delta, "rank": f["zoetis_rank"]}}


def _channel_shift(f: dict) -> Optional[dict]:
    mix = {m["channel"]: m for m in f["channel_mix"]}
    ecom = mix.get("E-commerce")
    vet = mix.get("Veterinary")
    if not ecom or not vet:
        return None
    headline = (f"Channel mix is shifting online in {f['category']}: "
                f"e-commerce {_pts(ecom['delta_pct'])}, veterinary {_pts(vet['delta_pct'])}")
    body = (
        f"Over the trailing eight quarters, e-commerce rose from {ecom['start_pct']:.1f}% "
        f"to {ecom['end_pct']:.1f}% of {f['category']} while veterinary eroded from "
        f"{vet['start_pct']:.1f}% to {vet['end_pct']:.1f}%. The shift favors brands with "
        f"strong online presence and pressures vet-anchored portfolios."
    )
    return {"headline": headline, "body": body, "confidence": "High",
            "tags": ["channel mix", "trend"],
            "metrics": {"ecommerce_delta": ecom["delta_pct"],
                        "vet_delta": vet["delta_pct"]}}


def _notable_swing(f: dict) -> Optional[dict]:
    mover = f.get("top_mover")
    decliner = f.get("top_decliner")
    if not mover or not decliner:
        return None
    mtag = " (Zoetis)" if mover["is_zoetis"] else ""
    dtag = " (Zoetis)" if decliner["is_zoetis"] else ""
    headline = (f"Biggest movers: {mover['brand']}{mtag} {_pts(mover['delta'])}, "
                f"{decliner['brand']}{dtag} {_pts(decliner['delta'])}")
    body = (
        f"The largest share gain in {f['category']} ({f['channel']}, {f['period']} vs "
        f"{f['prior_period']}) is {mover['brand']}{mtag} at {_pts(mover['delta'])}; the "
        f"largest decline is {decliner['brand']}{dtag} at {_pts(decliner['delta'])}. "
        f"Watch these two for competitive response."
    )
    return {"headline": headline, "body": body, "confidence": "Medium",
            "tags": ["competitive", "movement"],
            "metrics": {"top_mover_delta": mover["delta"],
                        "top_decliner_delta": decliner["delta"]}}


def _source_agreement(f: dict) -> Optional[dict]:
    sa = f.get("source_agreement")
    if not sa:
        return None
    disp = sa["dispersion"]
    n = sa["n_sources"]
    if n >= 2:
        agree = "closely" if disp < 0.03 else ("broadly" if disp < 0.06 else "weakly")
        headline = (f"{f['zoetis_brand']} estimate triangulates {n} sources that agree "
                    f"{agree} (dispersion {disp*100:.1f}%)")
        conf = "High" if disp < 0.03 else ("Medium" if disp < 0.06 else "Low")
        body = (
            f"In {sa['channel']}, {n} independent sources cross-validate the {f['zoetis_brand']} "
            f"estimate; their {agree} agreement (cross-source dispersion {disp*100:.1f}%) is why "
            f"the band is {('tight' if disp < 0.03 else 'moderate')}. More agreement, narrower band."
        )
    else:
        headline = (f"{f['zoetis_brand']} {sa['channel']} estimate rests on a single source "
                    f"-- wider band, lower confidence")
        conf = "Low"
        body = (
            f"{sa['channel']} is covered by only one source here, so there is no second feed to "
            f"cross-check it. The confidence band is correspondingly wider; prioritize a second "
            f"feed if this channel drives decisions."
        )
    return {"headline": headline, "body": body, "confidence": conf,
            "tags": ["confidence", "triangulation"],
            "metrics": {"dispersion": disp, "n_sources": n}}


def _confidence_caveat(f: dict) -> Optional[dict]:
    if not f.get("low_confidence"):
        return None
    brand = f["zoetis_brand"]
    rw = f["zoetis_sales"]["rel_width"]
    headline = f"Caveat: {brand} estimate is low-confidence ({rw*100:.1f}% band) this period"
    body = (
        f"The {brand} estimate carries a wide 95% band (+/-{rw*100:.1f}%), driven by limited "
        f"source coverage or source disagreement in this slice. Read the share move as "
        f"directional, not precise, until coverage improves."
    )
    return {"headline": headline, "body": body, "confidence": "Low",
            "tags": ["confidence", "caveat"], "metrics": {"rel_width": rw}}


_TEMPLATES = [_share_move, _channel_shift, _notable_swing, _source_agreement, _confidence_caveat]


def build_insights(facts: dict) -> list[dict]:
    """Assemble the ordered list of insight narratives from computed facts."""
    insights = []
    for tmpl in _TEMPLATES:
        ins = tmpl(facts)
        if ins:
            insights.append(ins)
    return insights
