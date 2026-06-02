import { useEffect, useState } from "react";
import { Card, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import { usdFull } from "../lib/format";
import { useAsync } from "../lib/useAsync";
import type { ScoreResponse } from "../lib/types";

export function Procurement() {
  const def = useAsync<ScoreResponse>(() => api.scoreDefault(), []);
  const [weights, setWeights] = useState<Record<string, number> | null>(null);

  useEffect(() => {
    if (def.data && !weights) {
      const w: Record<string, number> = {};
      for (const c of def.data.criteria) w[c.key] = Math.round((def.data.normalized_weights[c.key] ?? 0) * 100);
      setWeights(w);
    }
  }, [def.data, weights]);

  const scored = useAsync<ScoreResponse | null>(
    () => (weights ? api.score(weights) : Promise.resolve(null)), [weights]);

  const data = scored.data ?? def.data;
  const criteria = def.data?.criteria ?? [];

  return (
    <>
      <div className="page-head">
        <h1>Procurement Decision Tool</h1>
        <p>Weight the criteria that matter to Zoetis and the recommended e-commerce data vendor re-ranks live. This is what unblocks the CIQ-vs-Stackline buy decision.</p>
      </div>

      {def.error && <ErrorState message={def.error} />}
      {!data && <Loading what="scoring" />}

      {data && weights && (
        <>
          <div className="grid" style={{ gridTemplateColumns: "1fr 1fr", gap: 16 }}>
            <Card title="Criteria weights" hint="drag to re-rank — auto-normalized">
              {criteria.map((c) => (
                <div className="slider-row" key={c.key}>
                  <div className="crit">{c.label}<small>{c.description}</small></div>
                  <input type="range" min={0} max={100} value={weights[c.key] ?? 0}
                    onChange={(e) => setWeights({ ...weights, [c.key]: Number(e.target.value) })} />
                  <div className="wval">{((data.normalized_weights[c.key] ?? 0) * 100).toFixed(0)}%</div>
                </div>
              ))}
              <div className="divider" />
              <button className="btn" onClick={() => {
                const w: Record<string, number> = {};
                for (const c of def.data!.criteria) w[c.key] = Math.round((def.data!.normalized_weights[c.key] ?? 0) * 100);
                setWeights(w);
              }}>Reset to defaults</button>
            </Card>

            <Card title="Vendor ranking" hint="weighted score out of 100">
              <div className="callout gold" style={{ marginBottom: 14 }}>
                <b>Winner: {data.winner}.</b> {data.winner_rationale}
              </div>
              {data.vendors.map((v) => {
                const max = Math.max(...data.vendors.map((x) => x.total_score), 1);
                return (
                  <div key={v.vendor} style={{ marginBottom: 12 }}>
                    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: 4 }}>
                      <span style={{ fontWeight: 700 }}>
                        {v.is_winner && <span style={{ color: "var(--pass)" }}>✓ </span>}{v.label}
                        {v.is_winner && <span className="pill pass" style={{ marginLeft: 8 }}>WINNER</span>}
                      </span>
                      <span style={{ fontWeight: 800, fontVariantNumeric: "tabular-nums" }}>{v.total_score.toFixed(1)}</span>
                    </div>
                    <div style={{ height: 14, background: "var(--bg-soft)", borderRadius: 7, overflow: "hidden" }}>
                      <div style={{ width: `${(v.total_score / max) * 100}%`, height: "100%", borderRadius: 7,
                        background: v.is_winner ? "var(--pass)" : "var(--primary)" }} />
                    </div>
                    {v.blurb && <div className="note" style={{ marginTop: 3 }}>{v.blurb}</div>}
                  </div>
                );
              })}
            </Card>
          </div>

          <div className="section">
            <Card title="Scoring matrix" hint="vendor capability ratings (0–100) by criterion">
              <table className="data">
                <thead>
                  <tr>
                    <th>Criterion</th><th className="num">Weight</th>
                    {data.vendors.map((v) => <th key={v.vendor} className="num">{v.label}</th>)}
                  </tr>
                </thead>
                <tbody>
                  {criteria.map((c) => (
                    <tr key={c.key}>
                      <td>{c.label}</td>
                      <td className="num">{((data.normalized_weights[c.key] ?? 0) * 100).toFixed(0)}%</td>
                      {data.vendors.map((v) => (
                        <td key={v.vendor} className="num">{v.per_criterion[c.key]?.raw ?? "—"}</td>
                      ))}
                    </tr>
                  ))}
                  <tr style={{ borderTop: "2px solid var(--line-strong)" }}>
                    <td style={{ fontWeight: 800 }}>Weighted total</td><td></td>
                    {data.vendors.map((v) => (
                      <td key={v.vendor} className="num" style={{ fontWeight: 800, color: v.is_winner ? "var(--pass)" : undefined }}>
                        {v.total_score.toFixed(1)}
                      </td>
                    ))}
                  </tr>
                </tbody>
              </table>
            </Card>
          </div>

          <CostModel />
        </>
      )}
    </>
  );
}

function CostModel() {
  const [tier, setTier] = useState("Professional");
  const cost = useAsync(() => api.cost(tier), [tier]);

  return (
    <div className="section">
      <Card title="Annual cost model" hint="pass-through vendor data + tiered Improzo services">
        {cost.error && <div className="note" style={{ color: "var(--fail)" }}>{cost.error}</div>}
        {cost.data && (
          <>
            <div className="row" style={{ alignItems: "center", gap: 12, marginBottom: 14 }}>
              <span className="note" style={{ fontWeight: 700 }}>Improzo service tier:</span>
              {cost.data.tiers.map((t) => (
                <button key={t} className={`btn ${tier === t ? "primary" : ""}`} style={{ padding: "6px 12px" }}
                  onClick={() => setTier(t)}>{t}</button>
              ))}
            </div>
            <table className="data">
              <thead>
                <tr>
                  <th>Vendor path</th>
                  <th className="num">Vendor data (at cost)</th>
                  <th className="num">Improzo services</th>
                  <th className="num">Annual total</th>
                  <th>Note</th>
                </tr>
              </thead>
              <tbody>
                {cost.data.rows.map((r) => {
                  const recommended = r.note.includes("★");
                  return (
                    <tr key={r.vendor_path} style={recommended ? { background: "var(--zoetis-soft)" } : undefined}>
                      <td style={{ fontWeight: recommended ? 700 : 600 }}>{r.label}</td>
                      <td className="num">{usdFull(r.vendor_data_cost)}</td>
                      <td className="num">{usdFull(r.improzo_service_cost)}</td>
                      <td className="num" style={{ fontWeight: 800 }}>{usdFull(r.annual_total)}</td>
                      <td className="note">{r.note}</td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
            <div className="callout" style={{ marginTop: 14 }}>{cost.data.principle}</div>
            <div className="note" style={{ marginTop: 8, fontStyle: "italic" }}>{cost.data.disclaimer}</div>
          </>
        )}
        {cost.loading && !cost.data && <Loading what="cost model" />}
      </Card>
    </div>
  );
}
