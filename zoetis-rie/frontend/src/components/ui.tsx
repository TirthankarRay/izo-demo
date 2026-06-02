// Small shared UI primitives: cards, stats, pills, confidence-band visual, gauge.
import type { ReactNode } from "react";
import type { Band } from "../lib/types";
import { usd } from "../lib/format";

export function Card({ children, className = "", title, hint }: {
  children: ReactNode; className?: string; title?: ReactNode; hint?: ReactNode;
}) {
  return (
    <div className={`card ${className}`}>
      {title && (
        <div className="card-title" style={{ marginBottom: 12 }}>
          {title} {hint && <span className="hint">{hint}</span>}
        </div>
      )}
      {children}
    </div>
  );
}

export function Stat({ label, value, sub, meta, delta }: {
  label: string; value: ReactNode; sub?: ReactNode; meta?: ReactNode;
  delta?: { value: number; text: string };
}) {
  const cls = delta ? (delta.value > 0.05 ? "up" : delta.value < -0.05 ? "down" : "flat") : "";
  return (
    <div className="stat">
      <div className="label">{label}</div>
      <div className="value">{value} {sub && <small>{sub}</small>}</div>
      <div className="meta">
        {delta && <span className={`delta ${cls}`}>{delta.text}</span>}
        {delta && meta ? " · " : ""}
        {meta}
      </div>
    </div>
  );
}

export function ZoetisTag() {
  return <span className="zoetis-tag">◆ Zoetis</span>;
}

export function StatusPill({ status }: { status: string }) {
  const c = status.toLowerCase();
  return <span className={`pill ${c}`}>{status}</span>;
}

export function ConfidencePill({ confidence }: { confidence: string }) {
  return <span className={`pill conf-${confidence}`}>{confidence} confidence</span>;
}

/** Confidence-band visual: shaded lower–upper range with a point marker. */
export function BandBar({ band, max, zoetis = false, showCaption = true }: {
  band: Band; max: number; zoetis?: boolean; showCaption?: boolean;
}) {
  const safeMax = max > 0 ? max : 1;
  const left = Math.max(0, Math.min(100, (band.lower / safeMax) * 100));
  const right = Math.max(0, Math.min(100, (band.upper / safeMax) * 100));
  const point = Math.max(0, Math.min(100, (band.point / safeMax) * 100));
  return (
    <div className="band">
      <div className="band-track">
        <div className={`band-range ${zoetis ? "zoetis" : ""}`}
          style={{ left: `${left}%`, width: `${Math.max(1.5, right - left)}%` }} />
        <div className={`band-point ${zoetis ? "zoetis" : ""}`} style={{ left: `calc(${point}% - 1.5px)` }} />
      </div>
      {showCaption && (
        <div className="band-caption">
          <span>{usd(band.lower)}</span>
          <span style={{ fontWeight: 700, color: "var(--ink)" }}>{usd(band.point)}</span>
          <span>{usd(band.upper)}</span>
        </div>
      )}
    </div>
  );
}

export function Gauge({ value, label }: { value: number; label?: string }) {
  const r = 42;
  const c = 2 * Math.PI * r;
  const off = c * (1 - Math.max(0, Math.min(100, value)) / 100);
  const color = value >= 92 ? "var(--pass)" : value >= 80 ? "var(--review)" : "var(--fail)";
  return (
    <div className="gauge">
      <div className="gauge-ring">
        <svg width="96" height="96" viewBox="0 0 96 96">
          <circle cx="48" cy="48" r={r} fill="none" stroke="var(--bg-soft)" strokeWidth="9" />
          <circle cx="48" cy="48" r={r} fill="none" stroke={color} strokeWidth="9"
            strokeLinecap="round" strokeDasharray={c} strokeDashoffset={off}
            transform="rotate(-90 48 48)" />
        </svg>
        <div className="num" style={{ color }}>{value.toFixed(0)}</div>
      </div>
      {label && <div><div style={{ fontWeight: 700 }}>{label}</div><div className="note">out of 100</div></div>}
    </div>
  );
}

export function Loading({ what = "data" }: { what?: string }) {
  return <div className="loading-wrap"><span className="spinner" /> Loading {what}…</div>;
}

export function ErrorState({ message }: { message: string }) {
  return (
    <div className="card" style={{ borderColor: "var(--fail)", color: "var(--fail)" }}>
      <div className="card-title" style={{ color: "var(--fail)" }}>Couldn’t load data</div>
      <div className="note" style={{ color: "var(--fail)" }}>{message}</div>
      <div className="note" style={{ marginTop: 8 }}>
        Is the backend running? Start it with <code>uvicorn app.main:app --reload</code> in <code>backend/</code>.
      </div>
    </div>
  );
}

export function Synthetic() {
  return (
    <div className="footer">
      <strong>SYNTHETIC DATA</strong> — every figure on this page is generated for demonstration only.
      No real Zoetis, CIQ, Stackline or Nielsen data. Built as the Phase-1 MVP of the Retail Intelligence Engine.
    </div>
  );
}
