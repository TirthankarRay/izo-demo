import { Link, useNavigate } from "react-router-dom";
import { Cell, Pie, PieChart, ResponsiveContainer, Tooltip } from "recharts";
import { FilterBar } from "../components/FilterBar";
import { Card, ConfidencePill, ErrorState, Gauge, Loading, Stat, ZoetisTag } from "../components/ui";
import { api } from "../lib/api";
import { CHANNEL_COLORS, pct, signedPct, usd } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useFilters } from "../state/filters";

const CAPS = [
  { to: "/market-share", icon: "▣", title: "Market Share & Triangulation", sub: "Channels →", subTo: "/channels",
    desc: "Coverage-weighted estimates with 95% confidence bands, brand leaderboard, and per-source triangulation." },
  { to: "/qc", icon: "✓", title: "QC Scorecard", desc: "Five-stage validation engine, flagged-record drill-down, quality score and delivery gating." },
  { to: "/procurement", icon: "⚖", title: "Procurement Decision", desc: "Live-reweighted vendor scoring (CIQ vs Stackline vs Nielsen) and a pass-through cost model." },
  { to: "/insights", icon: "✎", title: "Insight Narratives", desc: "Plain-language, confidence-aware narratives — conclusion first, evidence second." },
];

export function Dashboard() {
  const { filters } = useFilters();
  const navigate = useNavigate();
  const cat = filters.category;
  const ready = !!cat;

  const ms = useAsync(() => api.marketShare({
    category: cat, channel: filters.channel, geo_level: filters.geo_level,
    geo: filters.geo, period_type: filters.period_type, period: filters.period,
  }), [cat, filters.channel, filters.geo_level, filters.geo, filters.period_type, filters.period]);

  const ch = useAsync(() => api.channel({ category: cat, geo_level: filters.geo_level, geo: filters.geo }),
    [cat, filters.geo_level, filters.geo]);

  const qc = useAsync(() => api.qc(false), []);

  if (!ready) return <Loading what="catalog" />;

  return (
    <>
      <div className="page-head">
        <h1>Retail Intelligence Dashboard</h1>
        <p>Market-share intelligence for Zoetis across veterinary, retail and e-commerce — every number triangulated from multiple sources and shipped with a confidence band.</p>
      </div>
      <FilterBar />

      {ms.error && <ErrorState message={ms.error} />}

      <div className="grid cols-4">
        <Card>
          {ms.data ? (
            <Stat label={`${cat} market`} value={usd(ms.data.total_sales.point)}
              meta={<>{ms.data.channel} · <ConfidencePill confidence={ms.data.total_sales.confidence} /></>} />
          ) : <Loading what="market" />}
        </Card>
        <Card>
          {ms.data ? (
            <Stat label="Zoetis brand share"
              value={pct(ms.data.zoetis_share_pct)}
              sub={ms.data.zoetis_brand ? `#${ms.data.rows.find((r) => r.is_zoetis)?.rank}` : ""}
              meta={<>{ms.data.zoetis_brand} <ZoetisTag /></>} />
          ) : <Loading what="share" />}
        </Card>
        <Card>
          {ch.data ? (() => {
            const e = ch.data.mix.find((m) => m.channel === "E-commerce");
            const v = ch.data.mix.find((m) => m.channel === "Veterinary");
            return <Stat label="E-commerce shift (8 q)"
              value={`${signedPct(e?.delta_pct ?? 0)} pts`}
              delta={{ value: e?.delta_pct ?? 0, text: `to ${pct(e?.end_pct ?? 0)}` }}
              meta={`Vet ${signedPct(v?.delta_pct ?? 0)} pts → ${pct(v?.end_pct ?? 0)}`} />;
          })() : <Loading what="channels" />}
        </Card>
        <Card>
          {qc.data ? (
            <Stat label="Data quality score" value={qc.data.quality_score.toFixed(0)}
              sub="/100"
              meta={<span className={`pill ${qc.data.delivery_ready ? "pass" : "review"}`}>
                {qc.data.delivery_ready ? "Delivery ready" : "Delivery on hold"}</span>} />
          ) : <Loading what="QC" />}
        </Card>
      </div>

      <div className="grid cols-2" style={{ marginTop: 16 }}>
        <Card title="Brand share leaderboard" hint={`${cat} · ${ms.data?.channel ?? ""} · ${ms.data?.period ?? ""}`}>
          {ms.data ? <Leaderboard rows={ms.data.rows} /> : <Loading />}
          <div className="note" style={{ marginTop: 10 }}>Bar length = market share. The Zoetis brand is marked in gold.</div>
        </Card>

        <Card title="Channel mix" hint={`${cat} · latest quarter`}>
          {ch.data ? <ChannelMix data={ch.data.mix} story={ch.data.story} /> : <Loading />}
        </Card>
      </div>

      <div className="section">
        <h2>Explore the four capabilities</h2>
        <div className="grid cols-4">
          {CAPS.map((c) => (
            <div key={c.to} className="card cap-card" role="link" tabIndex={0}
              onClick={() => navigate(c.to)}
              onKeyDown={(e) => { if (e.key === "Enter") navigate(c.to); }}>
              <div className="cap-icon">{c.icon}</div>
              <h3>{c.title}</h3>
              <p>{c.desc}</p>
              <div className="go">
                Open →{c.subTo && (
                  <Link to={c.subTo} style={{ marginLeft: 10 }} onClick={(e) => e.stopPropagation()}>{c.sub}</Link>
                )}
              </div>
            </div>
          ))}
        </div>
      </div>

      <div className="section">
        <Card title="Delivery readiness" hint="QC gate before any data ships">
          {qc.data ? (
            <div className="row" style={{ alignItems: "center", gap: 24 }}>
              <Gauge value={qc.data.quality_score} label="Quality" />
              <div style={{ flex: 1, minWidth: 240 }}>
                <div className="row" style={{ gap: 8, marginBottom: 8 }}>
                  {qc.data.stages.map((s) => (
                    <span key={s.stage_no} className={`pill ${s.status.toLowerCase()}`}>{s.stage_no}. {s.name.split(" ")[0]}</span>
                  ))}
                </div>
                <div className="note">{qc.data.delivery_note}</div>
                <Link to="/qc" className="btn ghost" style={{ paddingLeft: 0 }}>Open QC scorecard →</Link>
              </div>
            </div>
          ) : <Loading what="QC" />}
        </Card>
      </div>
    </>
  );
}

function Leaderboard({ rows }: { rows: import("../lib/types").MarketShareRow[] }) {
  const max = Math.max(...rows.map((r) => r.share_pct), 1);
  return (
    <div style={{ display: "flex", flexDirection: "column", gap: 9 }}>
      {rows.map((r) => (
        <div key={r.brand} style={{ display: "grid", gridTemplateColumns: "170px 1fr 52px", gap: 10, alignItems: "center" }}>
          <div style={{ fontSize: 12.5, fontWeight: r.is_zoetis ? 700 : 500, whiteSpace: "nowrap", overflow: "hidden", textOverflow: "ellipsis" }}>
            {r.is_zoetis && <span style={{ color: "var(--zoetis)" }}>◆ </span>}{r.brand}
          </div>
          <div style={{ height: 14, background: "var(--bg-soft)", borderRadius: 7, overflow: "hidden" }}>
            <div style={{ width: `${(r.share_pct / max) * 100}%`, height: "100%",
              background: r.is_zoetis ? "var(--zoetis-bar)" : r.is_private_label ? "#94a3b8" : "var(--primary)", borderRadius: 7 }} />
          </div>
          <div className="num" style={{ fontWeight: 700, fontSize: 12.5 }}>{pct(r.share_pct)}</div>
        </div>
      ))}
    </div>
  );
}

function ChannelMix({ data, story }: { data: import("../lib/types").ChannelMix[]; story: string }) {
  const pie = data.map((m) => ({ name: m.channel, value: m.end_pct }));
  return (
    <div>
      <div className="row" style={{ alignItems: "center", gap: 16 }}>
        <div style={{ width: 150, height: 150 }}>
          <ResponsiveContainer>
            <PieChart>
              <Pie data={pie} dataKey="value" innerRadius={42} outerRadius={68} paddingAngle={2}>
                {pie.map((p) => <Cell key={p.name} fill={CHANNEL_COLORS[p.name]} />)}
              </Pie>
              <Tooltip formatter={(v: number) => `${v.toFixed(1)}%`} />
            </PieChart>
          </ResponsiveContainer>
        </div>
        <div className="legend" style={{ flexDirection: "column", gap: 8 }}>
          {data.map((m) => (
            <span key={m.channel}>
              <span className="dot" style={{ background: CHANNEL_COLORS[m.channel] }} />
              <b>{m.channel}</b>&nbsp;{pct(m.end_pct)}
              <span className={`delta ${m.delta_pct > 0 ? "up" : m.delta_pct < 0 ? "down" : "flat"}`} style={{ marginLeft: 6 }}>
                {signedPct(m.delta_pct)} pts
              </span>
            </span>
          ))}
        </div>
      </div>
      <div className="callout gold" style={{ marginTop: 12 }}>{story}</div>
    </div>
  );
}
