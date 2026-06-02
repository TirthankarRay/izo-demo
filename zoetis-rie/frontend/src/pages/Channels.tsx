import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import { FilterBar } from "../components/FilterBar";
import { Card, ErrorState, Loading, Stat } from "../components/ui";
import { api } from "../lib/api";
import { CHANNEL_COLORS, pct, signedPct, usd } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import { useFilters } from "../state/filters";
import type { ChannelViewResponse } from "../lib/types";

const CHANNELS = ["Veterinary", "Retail", "E-commerce"];

export function Channels() {
  const { filters, catalog } = useFilters();
  const cat = filters.category;

  const cv = useAsync(() => api.channel({ category: cat, geo_level: filters.geo_level, geo: filters.geo }),
    [cat, filters.geo_level, filters.geo]);

  if (!cat || !catalog) return <Loading what="catalog" />;

  const sales = cv.data ? pivot(cv.data, "sales") : [];
  const mix = cv.data ? pivot(cv.data, "mix") : [];

  return (
    <>
      <div className="page-head">
        <h1>Channel View</h1>
        <p>Veterinary vs retail vs e-commerce split and trend across the trailing eight quarters, with the channel-mix shift made explicit.</p>
      </div>
      <FilterBar show={["category", "geo"]} />
      {cv.error && <ErrorState message={cv.error} />}

      {cv.data && (
        <>
          <div className="grid cols-4" style={{ marginBottom: 16 }}>
            {cv.data.mix.map((m) => (
              <Card key={m.channel}>
                <Stat label={m.channel} value={pct(m.end_pct)}
                  delta={{ value: m.delta_pct, text: `${signedPct(m.delta_pct)} pts` }}
                  meta={`from ${pct(m.start_pct)} · 8q`} />
              </Card>
            ))}
            <Card>
              <Stat label="Scope" value={cat.split(" ")[0]} meta={`${filters.geo} · ${cv.data.quarters.length} quarters`} />
            </Card>
          </div>

          <div className="callout gold" style={{ marginBottom: 16 }}>{cv.data.story}</div>

          <div className="grid cols-2">
            <Card title="Channel sales by quarter" hint="estimated sales, stacked">
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <BarChart data={sales} margin={{ top: 8, right: 12, bottom: 0, left: 8 }}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="quarter" tick={{ fontSize: 11 }} stroke="var(--muted)" />
                    <YAxis tickFormatter={(v) => usd(v)} tick={{ fontSize: 11 }} stroke="var(--muted)" width={54} />
                    <Tooltip formatter={(v: number, n) => [usd(v), n as string]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {CHANNELS.map((c) => (
                      <Bar key={c} dataKey={c} stackId="s" fill={CHANNEL_COLORS[c]} radius={c === "E-commerce" ? [4, 4, 0, 0] : undefined} />
                    ))}
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </Card>

            <Card title="Channel mix %" hint="share of channel spend, 100% stacked">
              <div style={{ width: "100%", height: 280 }}>
                <ResponsiveContainer>
                  <AreaChart data={mix} margin={{ top: 8, right: 12, bottom: 0, left: 8 }} stackOffset="expand">
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--line)" vertical={false} />
                    <XAxis dataKey="quarter" tick={{ fontSize: 11 }} stroke="var(--muted)" />
                    <YAxis tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} tick={{ fontSize: 11 }} stroke="var(--muted)" width={42} />
                    <Tooltip formatter={(v: number, n) => [pct(v), n as string]} />
                    <Legend wrapperStyle={{ fontSize: 12 }} />
                    {CHANNELS.map((c) => (
                      <Area key={c} type="monotone" dataKey={c} stackId="m" stroke={CHANNEL_COLORS[c]} fill={CHANNEL_COLORS[c]} fillOpacity={0.55} />
                    ))}
                  </AreaChart>
                </ResponsiveContainer>
              </div>
            </Card>
          </div>
        </>
      )}
      {cv.loading && <Loading what="channels" />}
    </>
  );
}

// Pivot the long [{quarter, channel, sales, mix_pct}] series into wide rows
// keyed by channel for the stacked charts.
function pivot(cv: ChannelViewResponse, kind: "sales" | "mix") {
  const byQ = new Map<string, Record<string, number | string>>();
  for (const p of cv.series) {
    const row = byQ.get(p.quarter) ?? { quarter: p.quarter };
    row[p.channel] = kind === "sales" ? p.sales.point : p.mix_pct;
    byQ.set(p.quarter, row);
  }
  return cv.quarters.map((q) => byQ.get(q) ?? { quarter: q });
}
