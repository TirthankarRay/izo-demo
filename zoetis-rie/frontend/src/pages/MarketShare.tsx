import { useEffect, useState } from "react";
import {
  Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { FilterBar } from "../components/FilterBar";
import { BandBar, Card, ConfidencePill, ErrorState, Loading, Stat, ZoetisTag } from "../components/ui";
import { api } from "../lib/api";
import { pct, usd } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useFilters } from "../state/filters";
import type { ChannelViewResponse, MarketShareRow, TriangulationDetail } from "../lib/types";

export function MarketShare() {
  const { filters, catalog } = useFilters();
  const cat = filters.category;
  const [selected, setSelected] = useState<string | null>(null);

  const ms = useAsync(() => api.marketShare({
    category: cat, channel: filters.channel, geo_level: filters.geo_level,
    geo: filters.geo, period_type: filters.period_type, period: filters.period,
  }), [cat, filters.channel, filters.geo_level, filters.geo, filters.period_type, filters.period]);

  // default the triangulation drill-down to the Zoetis brand
  useEffect(() => {
    if (ms.data && (!selected || !ms.data.rows.some((r) => r.brand === selected))) {
      setSelected(ms.data.zoetis_brand ?? ms.data.rows[0]?.brand ?? null);
    }
  }, [ms.data]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!cat || !catalog) return <Loading what="catalog" />;
  const max = ms.data ? Math.max(...ms.data.rows.map((r) => r.sales.upper), 1) : 1;

  return (
    <>
      <div className="page-head">
        <h1>Market Share & Triangulation</h1>
        <p>Estimated sales and share per brand, triangulated from coverage-weighted sources. Every estimate carries a 95% confidence band — click a brand to see how its number was built.</p>
      </div>
      <FilterBar />
      {ms.error && <ErrorState message={ms.error} />}

      {ms.data && (
        <div className="grid cols-4" style={{ marginBottom: 16 }}>
          <Card><Stat label={`${cat} market`} value={usd(ms.data.total_sales.point)}
            meta={<ConfidencePill confidence={ms.data.total_sales.confidence} />} /></Card>
          <Card><Stat label="Zoetis brand" value={pct(ms.data.zoetis_share_pct)}
            meta={<>{ms.data.zoetis_brand} <ZoetisTag /></>} /></Card>
          <Card><Stat label="Leader" value={ms.data.rows[0]?.brand.split(" ")[0] ?? "—"}
            meta={`${pct(ms.data.rows[0]?.share_pct ?? 0)} share`} /></Card>
          <Card><Stat label="Brands tracked" value={ms.data.rows.length}
            meta={`${ms.data.channel} · ${ms.data.period}`} /></Card>
        </div>
      )}

      <div className="grid" style={{ gridTemplateColumns: "1.6fr 1fr", gap: 16 }}>
        <Card title="Estimated sales & market share" hint="point estimate with 95% band">
          {ms.data ? (
            <table className="data">
              <thead>
                <tr>
                  <th>#</th><th>Brand</th><th style={{ width: 180 }}>Sales (95% band)</th>
                  <th className="num">Share</th><th className="num">Confidence</th>
                </tr>
              </thead>
              <tbody>
                {ms.data.rows.map((r) => (
                  <tr key={r.brand} className={`clickable ${r.is_zoetis ? "zoetis-row" : ""} ${selected === r.brand ? "" : ""}`}
                    onClick={() => setSelected(r.brand)}
                    style={selected === r.brand ? { outline: "2px solid var(--primary)", outlineOffset: -2 } : undefined}>
                    <td className="rank">{r.rank}</td>
                    <td>
                      <div style={{ fontWeight: r.is_zoetis ? 700 : 600 }}>{r.brand}</div>
                      {r.is_zoetis ? <ZoetisTag /> : r.is_private_label ? <span className="tag">Private label</span> : null}
                    </td>
                    <td><BandBar band={r.sales} max={max} zoetis={r.is_zoetis} /></td>
                    <td className="num"><b>{pct(r.share_pct)}</b><div className="note">{pct(r.share_lower)}–{pct(r.share_upper)}</div></td>
                    <td className="num"><span className={`pill conf-${r.sales.confidence}`}>{r.sales.confidence}</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Loading />}
        </Card>

        <TriPanel brand={selected} />
      </div>

      <div className="section">
        <ZoetisTrend brand={ms.data?.zoetis_brand ?? null} />
      </div>
    </>
  );
}

function TriPanel({ brand }: { brand: string | null }) {
  const { filters, catalog } = useFilters();
  const channels = catalog?.channels ?? [];
  const [channel, setChannel] = useState(filters.channel !== "All" ? filters.channel : "E-commerce");
  useEffect(() => { if (filters.channel !== "All") setChannel(filters.channel); }, [filters.channel]);

  const tri = useAsync<TriangulationDetail | null>(
    () => (brand ? api.triangulation({
      brand, channel, geo_level: filters.geo_level, geo: filters.geo,
      period_type: filters.period_type, period: filters.period,
    }) : Promise.resolve(null)),
    [brand, channel, filters.geo_level, filters.geo, filters.period_type, filters.period]);

  return (
    <Card title="Triangulation" hint={brand ?? ""}>
      <div className="row" style={{ gap: 6, marginBottom: 12 }}>
        {channels.map((c) => (
          <button key={c} className={`btn ${channel === c ? "primary" : ""}`} style={{ padding: "5px 10px", fontSize: 12 }}
            onClick={() => setChannel(c)}>{c}</button>
        ))}
      </div>
      {tri.loading && <Loading what="sources" />}
      {tri.error && <div className="note" style={{ color: "var(--fail)" }}>{tri.error}</div>}
      {tri.data && (
        <>
          <div className="row" style={{ gap: 18, marginBottom: 10 }}>
            <div className="stat"><div className="label">Estimate</div>
              <div className="value" style={{ fontSize: 20 }}>{usd(tri.data.estimate.point)}</div>
              <div className="note">{usd(tri.data.estimate.lower)} – {usd(tri.data.estimate.upper)}</div></div>
            <div className="stat"><div className="label">Coverage</div>
              <div className="value" style={{ fontSize: 20 }}>{pct(tri.data.combined_coverage * 100, 0)}</div>
              <div className="note">{tri.data.n_sources} source{tri.data.n_sources > 1 ? "s" : ""}</div></div>
            <div className="stat"><div className="label">Dispersion</div>
              <div className="value" style={{ fontSize: 20 }}>{pct(tri.data.rel_dispersion * 100)}</div>
              <div className="note">cross-source</div></div>
          </div>
          <div className="divider" />
          {tri.data.sources.length === 0 && <div className="note">No source covers this slice.</div>}
          {tri.data.sources.map((s) => {
            const wmax = Math.max(...tri.data!.sources.map((x) => x.grossed_up), 1);
            return (
              <div className="src-bar" key={s.source}>
                <div title={s.label} style={{ whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>{s.label}</div>
                <div className="track"><div className="fill" style={{ width: `${(s.grossed_up / wmax) * 100}%` }} /></div>
                <div className="num" style={{ fontSize: 12 }}>{usd(s.grossed_up)}<div className="note">w {(s.weight * 100).toFixed(0)}%</div></div>
              </div>
            );
          })}
          <div className="callout" style={{ marginTop: 12 }}>{tri.data.interpretation}</div>
        </>
      )}
    </Card>
  );
}

function ZoetisTrend({ brand }: { brand: string | null }) {
  const { filters } = useFilters();
  const cv = useAsync<ChannelViewResponse | null>(
    () => (brand ? api.channel({ brand, geo_level: filters.geo_level, geo: filters.geo }) : Promise.resolve(null)),
    [brand, filters.geo_level, filters.geo]);

  if (!brand) return null;
  const data = cv.data ? aggregateByQuarter(cv.data) : [];

  return (
    <Card title={`${brand} sales trend`} hint="quarterly total with 95% confidence band">
      {cv.loading && <Loading />}
      {cv.data && (
        <div style={{ width: "100%", height: 240 }}>
          <ResponsiveContainer>
            <ComposedChart data={data} margin={{ top: 8, right: 16, bottom: 0, left: 6 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
              <XAxis dataKey="quarter" tick={{ fontSize: 11 }} stroke="var(--muted)" />
              <YAxis tickFormatter={(v) => usd(v)} tick={{ fontSize: 11 }} stroke="var(--muted)" width={54} />
              <Tooltip formatter={(v: number, name) => [usd(v), name as string]} />
              <Area type="monotone" dataKey="band" stroke="none" fill="var(--zoetis-bar)" fillOpacity={0.18} name="95% band" />
              <Line type="monotone" dataKey="point" stroke="var(--zoetis)" strokeWidth={2.5} dot={{ r: 3 }} name="Estimate" />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      )}
      <div className="note">The shaded gold range is the 95% confidence band — it narrows in recent quarters as e-commerce coverage improves.</div>
    </Card>
  );
}

// Sum a brand's per-channel quarterly series into a brand total per quarter,
// combining the bands in quadrature (matching the backend's aggregation).
function aggregateByQuarter(cv: ChannelViewResponse) {
  const byQ = new Map<string, { point: number; half2: number }>();
  for (const p of cv.series) {
    const cur = byQ.get(p.quarter) ?? { point: 0, half2: 0 };
    cur.point += p.sales.point;
    const half = p.sales.upper - p.sales.point;
    cur.half2 += half * half;
    byQ.set(p.quarter, cur);
  }
  return cv.quarters.map((q) => {
    const v = byQ.get(q) ?? { point: 0, half2: 0 };
    const half = Math.sqrt(v.half2);
    return { quarter: q, point: Math.round(v.point), band: [Math.round(v.point - half), Math.round(v.point + half)] as [number, number] };
  });
}

export type { MarketShareRow };
