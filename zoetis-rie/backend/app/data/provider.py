"""Data abstraction layer -- THE SEAM for real vendor feeds later.

Everything above this file (engine, QC, scoring, narratives, API) reads data
ONLY through ``DataProvider``. Today it reads synthetic CSV/JSON seeds written
by ``generator.py``. In the real Phase-1 MVP, the *internals* of this class are
swapped for live vendor connectors (CIQ, Stackline, Nielsen) -- but the public
method signatures stay identical, so nothing downstream changes.

The provider is responsible for the messy, vendor-shaped concerns that the
analytics engine should never see:
  * SKU normalization (the same product under different vendor SKU strings),
  * mapping raw vendor rows to canonical brands,
  * geography derivation (key metros modeled as a share of their region),
  * exposing source coverage so the engine can coverage-weight.

It deliberately does NOT do analytics (no triangulation, no CI, no shares) --
that lives in the pure engine and the analytics orchestration layer.
"""
from __future__ import annotations

import csv
import json
import threading
from pathlib import Path
from typing import Iterable, Optional

SEEDS_DIR = Path(__file__).resolve().parent / "seeds"


def _read_csv(path: Path) -> list[dict]:
    with path.open(newline="") as f:
        return list(csv.DictReader(f))


def _to_bool(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


class SeedsNotFound(RuntimeError):
    """Raised when the seed files are missing -- run the generator first."""


class DataProvider:
    """Stable read interface over the synthetic-data layer.

    Construct once and reuse (it loads everything into memory). Use
    :func:`get_provider` for the process-wide singleton the API depends on.
    """

    def __init__(self, seeds_dir: Optional[Path] = None):
        self.seeds_dir = Path(seeds_dir) if seeds_dir else SEEDS_DIR
        meta_path = self.seeds_dir / "metadata.json"
        if not meta_path.exists():
            raise SeedsNotFound(
                f"No seeds at {self.seeds_dir}. Run: python -m app.data.generator --seed 42"
            )
        self.metadata = json.loads(meta_path.read_text())

        # --- dimensions -------------------------------------------------
        self._brands = _read_csv(self.seeds_dir / "dim_brand.csv")
        for b in self._brands:
            b["is_zoetis"] = _to_bool(b["is_zoetis"])
            b["is_private_label"] = _to_bool(b["is_private_label"])
            b["base_share"] = float(b["base_share"])
            b["unit_price"] = float(b["unit_price"])
        self._brand_by_name = {b["brand"]: b for b in self._brands}

        self._skus = _read_csv(self.seeds_dir / "dim_sku.csv")
        self._geography = _read_csv(self.seeds_dir / "dim_geography.csv")
        for g in self._geography:
            g["share_of_parent"] = float(g["share_of_parent"])
        self._geo_by_name = {g["geo"]: g for g in self._geography}

        # SKU variant map: (source, sku_raw) -> canonical/brand
        variants = _read_csv(self.seeds_dir / "dim_sku_variants.csv")
        self._variant_map: dict[tuple[str, str], dict] = {
            (v["source"], v["sku_raw"]): v for v in variants
        }

        # --- facts ------------------------------------------------------
        self._sources_raw: dict[str, list[dict]] = {}
        source_file = {
            "ciq_ecommerce": "ciq_ecommerce.csv",
            "stackline_ecommerce": "stackline_ecommerce.csv",
            "nielsen_scanner": "nielsen_scanner.csv",
            "zoetis_vet_internal": "zoetis_vet_internal.csv",
        }
        for source, fname in source_file.items():
            rows = _read_csv(self.seeds_dir / fname)
            for r in rows:
                r["observed_sales"] = float(r["observed_sales"])
                r["observed_units"] = int(float(r["observed_units"]))
                r["coverage"] = float(r["coverage"])
            self._sources_raw[source] = rows

        self._control_totals = _read_csv(self.seeds_dir / "control_totals.csv")
        for c in self._control_totals:
            c["control_total_sales"] = float(c["control_total_sales"])

        gt_path = self.seeds_dir / "ground_truth.csv"
        self._ground_truth = _read_csv(gt_path) if gt_path.exists() else []
        for r in self._ground_truth:
            r["true_sales"] = float(r["true_sales"])
            r["true_units"] = int(float(r["true_units"]))
            r["is_zoetis"] = _to_bool(r["is_zoetis"])

        issues_path = self.seeds_dir / "injected_issues.json"
        self._injected = json.loads(issues_path.read_text()) if issues_path.exists() else {"issues": []}

        # --- normalize + index -----------------------------------------
        self._unmapped: list[dict] = []
        self._norm_rows: list[dict] = []
        self._norm_index: dict[tuple, list[dict]] = {}
        self._build_normalized()

    # ------------------------------------------------------------------
    # Normalization
    # ------------------------------------------------------------------
    def normalize_sku(self, source: str, sku_raw: str) -> Optional[dict]:
        """Map a raw vendor SKU string to its canonical SKU/brand, or None."""
        return self._variant_map.get((source, sku_raw))

    def _build_normalized(self) -> None:
        """Normalize raw rows to canonical brand grain and build an index.

        Rows whose SKU does not normalize are set aside in ``_unmapped`` (the
        QC engine reports them); they never reach analytics.
        """
        agg: dict[tuple, dict] = {}
        for source, rows in self._sources_raw.items():
            for r in rows:
                mapped = self.normalize_sku(source, r["sku_raw"])
                if mapped is None:
                    self._unmapped.append({**r})
                    continue
                brand = mapped["brand"]
                key = (source, r["channel"], r["category"], brand,
                       r["geo_level"], r["geo"], r["month"])
                a = agg.get(key)
                if a is None:
                    agg[key] = {
                        "source": source, "channel": r["channel"], "category": r["category"],
                        "brand": brand, "geo_level": r["geo_level"], "geo": r["geo"],
                        "month": r["month"], "quarter": r["quarter"],
                        "observed_sales": r["observed_sales"], "observed_units": r["observed_units"],
                        "coverage": r["coverage"],
                    }
                else:
                    a["observed_sales"] += r["observed_sales"]
                    a["observed_units"] += r["observed_units"]
        self._norm_rows = list(agg.values())
        for r in self._norm_rows:
            r["is_zoetis"] = self._brand_by_name.get(r["brand"], {}).get("is_zoetis", False)
            key = (r["channel"], r["geo_level"], r["geo"], r["month"])
            self._norm_index.setdefault(key, []).append(r)

    # ------------------------------------------------------------------
    # Catalog accessors
    # ------------------------------------------------------------------
    def catalog(self) -> dict:
        """Everything the UI needs to populate filters and label things."""
        return {
            "categories": self.metadata["categories"],
            "channels": self.metadata["channels"],
            "brands": [
                {"brand": b["brand"], "category": b["category"],
                 "is_zoetis": b["is_zoetis"], "is_private_label": b["is_private_label"],
                 "role": b["role"]}
                for b in self._brands
            ],
            "geographies": self.metadata["geography"],
            "geo_levels": ["National", "Region", "Metro"],
            "months": self.metadata["months"],
            "quarters": self.metadata["quarters"],
            "sources": self.metadata["sources"],
            "channel_sources": self.metadata["channel_sources"],
            "window": self.metadata["window"],
        }

    def list_categories(self) -> list[str]:
        return list(self.metadata["categories"])

    def list_channels(self) -> list[str]:
        return list(self.metadata["channels"])

    def list_brands(self, category: Optional[str] = None) -> list[dict]:
        return [b for b in self._brands if category is None or b["category"] == category]

    def brand_info(self, brand: str) -> Optional[dict]:
        return self._brand_by_name.get(brand)

    def list_months(self) -> list[str]:
        return [m["month"] for m in self.metadata["months"]]

    def list_quarters(self) -> list[str]:
        return list(self.metadata["quarters"])

    def months_for_quarter(self, quarter: str) -> list[str]:
        return [m["month"] for m in self.metadata["months"] if m["quarter"] == quarter]

    def list_geographies(self, level: Optional[str] = None) -> list[dict]:
        return [g for g in self._geography if level is None or g["geo_level"] == level]

    def coverage_for(self, channel: str) -> dict[str, float]:
        """Map of source -> coverage for sources that observe ``channel``."""
        srcs = self.metadata["channel_sources"].get(channel, [])
        return {s: self.metadata["sources"][s]["coverage"] for s in srcs}

    def sources_meta(self) -> dict:
        return self.metadata["sources"]

    # ------------------------------------------------------------------
    # Observation queries (the main read path for analytics)
    # ------------------------------------------------------------------
    def observed(self, *, channel: str, month: str, geo_level: str = "National",
                 geo: str = "National", category: Optional[str] = None,
                 brand: Optional[str] = None) -> list[dict]:
        """Normalized per-source observations for one channel/geo/month slice.

        Metros are derived on the fly as a share of their parent region, since
        the synthetic feeds carry national + region grain. This derivation is a
        data-layer concern and is documented as a modeled disaggregation.
        Returns a list of dicts (one per source per brand).
        """
        if geo_level == "Metro":
            meta = self._geo_by_name.get(geo)
            if not meta:
                return []
            parent, share = meta["parent"], meta["share_of_parent"]
            base = self._norm_index.get((channel, "Region", parent, month), [])
            out = []
            for r in base:
                if category and r["category"] != category:
                    continue
                if brand and r["brand"] != brand:
                    continue
                out.append({**r, "geo_level": "Metro", "geo": geo,
                            "observed_sales": r["observed_sales"] * share,
                            "observed_units": int(round(r["observed_units"] * share))})
            return out

        rows = self._norm_index.get((channel, geo_level, geo, month), [])
        return [r for r in rows
                if (category is None or r["category"] == category)
                and (brand is None or r["brand"] == brand)]

    def observed_by_source(self, *, channel: str, month: str, brand: str,
                           geo_level: str = "National", geo: str = "National"
                           ) -> dict[str, float]:
        """{source: observed_sales} for one brand/channel/geo/month."""
        return {r["source"]: r["observed_sales"]
                for r in self.observed(channel=channel, month=month, geo_level=geo_level,
                                       geo=geo, brand=brand)}

    def brands_in(self, *, channel: str, month: str, geo_level: str = "National",
                  geo: str = "National", category: Optional[str] = None) -> list[str]:
        seen = []
        for r in self.observed(channel=channel, month=month, geo_level=geo_level,
                               geo=geo, category=category):
            if r["brand"] not in seen:
                seen.append(r["brand"])
        return seen

    # ------------------------------------------------------------------
    # Raw / QC accessors
    # ------------------------------------------------------------------
    def raw_source(self, source: str) -> list[dict]:
        """Raw (un-normalized) rows of a source feed -- for QC file checks."""
        return self._sources_raw[source]

    def all_raw_sources(self) -> dict[str, list[dict]]:
        return self._sources_raw

    def unmapped_rows(self) -> list[dict]:
        """Raw rows whose SKU did not normalize -- QC hierarchy stage flags these."""
        return self._unmapped

    def normalized_rows(self) -> list[dict]:
        """All normalized observations (brand grain) -- QC operates on these."""
        return self._norm_rows

    def control_totals(self) -> list[dict]:
        return self._control_totals

    def injected_issues(self) -> dict:
        """The generator's manifest of injected defects (reference / demo only).

        QC detects issues independently; this is exposed so the UI can show
        what *should* be catchable and tests can score detection.
        """
        return self._injected

    # ------------------------------------------------------------------
    # Ground truth (tests + share-of-truth scoring ONLY -- never production)
    # ------------------------------------------------------------------
    def ground_truth(self, *, channel: Optional[str] = None, month: Optional[str] = None,
                     geo_level: str = "National", geo: str = "National",
                     category: Optional[str] = None, brand: Optional[str] = None
                     ) -> list[dict]:
        out = []
        for r in self._ground_truth:
            if channel and r["channel"] != channel:
                continue
            if month and r["month"] != month:
                continue
            if r["geo_level"] != geo_level or r["geo"] != geo:
                continue
            if category and r["category"] != category:
                continue
            if brand and r["brand"] != brand:
                continue
            out.append(r)
        return out

    def true_sales(self, *, channel: str, month: str, brand: str,
                   geo_level: str = "National", geo: str = "National") -> float:
        rows = self.ground_truth(channel=channel, month=month, brand=brand,
                                 geo_level=geo_level, geo=geo)
        return sum(r["true_sales"] for r in rows)


# --------------------------------------------------------------------------
# Process-wide singleton
# --------------------------------------------------------------------------
_provider: Optional[DataProvider] = None
_lock = threading.Lock()


def get_provider(seeds_dir: Optional[Path] = None) -> DataProvider:
    """Lazily construct and cache the shared provider."""
    global _provider
    if _provider is None or seeds_dir is not None:
        with _lock:
            if _provider is None or seeds_dir is not None:
                _provider = DataProvider(seeds_dir=seeds_dir)
    return _provider


def reset_provider() -> None:
    """Drop the cached provider (used by tests that regenerate seeds)."""
    global _provider
    _provider = None
