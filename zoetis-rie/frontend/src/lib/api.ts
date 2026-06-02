// Typed client for the FastAPI endpoints. In dev, requests are same-origin and
// proxied to the backend (see vite.config.ts). Set VITE_API_BASE to point at a
// separately deployed backend.
import type {
  Catalog,
  ChannelViewResponse,
  CostModelResponse,
  Health,
  InsightsResponse,
  MarketShareResponse,
  QCReport,
  ScoreResponse,
  TriangulationDetail,
} from "./types";

const BASE = (import.meta.env.VITE_API_BASE as string | undefined) ?? "";

type Params = Record<string, string | number | boolean | undefined | null>;

function qs(params?: Params): string {
  if (!params) return "";
  const sp = new URLSearchParams();
  for (const [k, v] of Object.entries(params)) {
    if (v !== undefined && v !== null) sp.set(k, String(v));
  }
  const s = sp.toString();
  return s ? `?${s}` : "";
}

async function getJSON<T>(path: string, params?: Params): Promise<T> {
  const res = await fetch(`${BASE}${path}${qs(params)}`);
  if (!res.ok) {
    const body = await res.text().catch(() => "");
    throw new Error(`${res.status} ${res.statusText} on ${path} -- ${body.slice(0, 200)}`);
  }
  return res.json() as Promise<T>;
}

async function postJSON<T>(path: string, payload: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
  if (!res.ok) throw new Error(`${res.status} ${res.statusText} on ${path}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => getJSON<Health>("/api/health"),
  catalog: () => getJSON<Catalog>("/api/catalog"),

  marketShare: (p: Params) => getJSON<MarketShareResponse>("/api/market-share", p),
  triangulation: (p: Params) => getJSON<TriangulationDetail>("/api/triangulation", p),
  channel: (p: Params) => getJSON<ChannelViewResponse>("/api/channel", p),

  qc: (resolve = false) => getJSON<QCReport>("/api/qc", { resolve }),

  scoreDefault: () => getJSON<ScoreResponse>("/api/procurement/score"),
  score: (weights: Record<string, number>) =>
    postJSON<ScoreResponse>("/api/procurement/score", { weights }),
  cost: (tier: string) => getJSON<CostModelResponse>("/api/procurement/cost", { tier }),

  insights: (p: Params) => getJSON<InsightsResponse>("/api/insights", p),
};
