import { useEffect, useState } from "react";
import { Card, ErrorState, Gauge, Loading, StatusPill } from "../components/ui";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import type { QCReport } from "../lib/types";

export function QC() {
  const [resolve, setResolve] = useState(false);
  const qc = useAsync<QCReport>(() => api.qc(resolve), [resolve]);
  const [stageNo, setStageNo] = useState(2);

  useEffect(() => { if (qc.data && !qc.data.stages.some((s) => s.stage_no === stageNo)) setStageNo(qc.data.stages[0].stage_no); }, [qc.data, stageNo]);

  const stage = qc.data?.stages.find((s) => s.stage_no === stageNo);

  return (
    <>
      <div className="page-head">
        <h1>QC Scorecard & Data Validation</h1>
        <p>Five-stage monthly validation. Nothing ships to the client until every stage is PASS or its flags are explicitly resolved.</p>
      </div>

      {qc.error && <ErrorState message={qc.error} />}
      {qc.loading && !qc.data && <Loading what="QC report" />}

      {qc.data && (
        <>
          <Card className="pad-lg">
            <div className="row" style={{ alignItems: "center", gap: 28 }}>
              <Gauge value={qc.data.quality_score} label="Data quality" />
              <div style={{ flex: 1, minWidth: 260 }}>
                <div className="row" style={{ alignItems: "center", gap: 10, marginBottom: 6 }}>
                  <StatusPill status={qc.data.overall_status} />
                  <span className={`pill ${qc.data.delivery_ready ? "pass" : "review"}`}>
                    {qc.data.delivery_ready ? "✓ Delivery approved" : "⏸ Delivery on hold"}
                  </span>
                  <span className="note">target: {qc.data.delivery_by_business_day}th business day</span>
                </div>
                <div className="note" style={{ marginBottom: 10 }}>{qc.data.delivery_note}</div>
                <div className="row" style={{ gap: 8 }}>
                  <button className={`btn ${resolve ? "" : "primary"}`} onClick={() => setResolve(false)} disabled={!resolve}>Re-run validation</button>
                  <button className={`btn ${resolve ? "primary" : ""}`} onClick={() => setResolve(true)} disabled={resolve}>Resolve flags & approve delivery</button>
                </div>
              </div>
              <div style={{ minWidth: 150 }}>
                <div className="note">Records checked</div>
                <div style={{ fontSize: 22, fontWeight: 800 }}>{Number(qc.data.totals.records_checked).toLocaleString()}</div>
                <div className="note" style={{ marginTop: 6 }}>Total flags</div>
                <div style={{ fontSize: 22, fontWeight: 800, color: qc.data.delivery_ready ? "var(--pass)" : "var(--review)" }}>
                  {Number(qc.data.totals.total_flags).toLocaleString()}
                </div>
              </div>
            </div>
          </Card>

          <div className="section">
            <div className="grid" style={{ gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
              {qc.data.stages.map((s) => (
                <div key={s.stage_no} className="card" onClick={() => setStageNo(s.stage_no)}
                  style={{ cursor: "pointer", borderColor: stageNo === s.stage_no ? "var(--primary)" : undefined, borderWidth: stageNo === s.stage_no ? 2 : 1 }}>
                  <div className="note" style={{ fontWeight: 700 }}>Stage {s.stage_no}</div>
                  <div style={{ fontWeight: 700, fontSize: 13, margin: "2px 0 8px", minHeight: 34 }}>{s.name}</div>
                  <StatusPill status={s.status} />
                  <div style={{ marginTop: 10, display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
                    <span style={{ fontSize: 20, fontWeight: 800 }}>{s.score.toFixed(0)}</span>
                    <span className="note">{s.flags_raised} flag{s.flags_raised === 1 ? "" : "s"}</span>
                  </div>
                  <div style={{ height: 5, background: "var(--bg-soft)", borderRadius: 4, marginTop: 6 }}>
                    <div style={{ width: `${s.score}%`, height: "100%", borderRadius: 4,
                      background: s.status === "PASS" ? "var(--pass)" : s.status === "REVIEW" ? "var(--review)" : "var(--fail)" }} />
                  </div>
                </div>
              ))}
            </div>
          </div>

          {stage && (
            <div className="section">
              <Card title={`Stage ${stage.stage_no}: ${stage.name}`} hint={stage.summary}>
                <div className="row" style={{ gap: 20, marginBottom: 12 }}>
                  <div className="note">Records in: <b>{stage.records_in.toLocaleString()}</b></div>
                  <div className="note">Passed: <b>{stage.records_passed.toLocaleString()}</b></div>
                  <div className="note">Flags: <b>{stage.flags_raised.toLocaleString()}</b></div>
                  <div className="note">Status: <StatusPill status={stage.status} /></div>
                </div>
                {stage.flagged.length === 0 ? (
                  <div className="callout" style={{ borderColor: "var(--pass)", background: "var(--pass-soft)" }}>
                    No flags — this stage passed cleanly.
                  </div>
                ) : (
                  <table className="data">
                    <thead><tr><th>Severity</th><th>Entity</th><th>Reason</th></tr></thead>
                    <tbody>
                      {stage.flagged.map((f, i) => (
                        <tr key={i}>
                          <td><span className={`pill ${f.severity === "fail" ? "fail" : f.severity === "warn" ? "review" : "neutral"}`}>
                            {f.severity.toUpperCase()}</span></td>
                          <td style={{ fontFamily: "ui-monospace, monospace", fontSize: 12 }}>{f.entity}</td>
                          <td>{f.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
                {stage.flags_raised > stage.flagged.length && (
                  <div className="note" style={{ marginTop: 8 }}>Showing top {stage.flagged.length} of {stage.flags_raised} flags by severity.</div>
                )}
              </Card>
            </div>
          )}
        </>
      )}
    </>
  );
}
