// Typed contracts mirroring the FastAPI pydantic schemas (app/models/schemas.py).
// Keep these in sync with the backend -- this is the "typed contracts end to end"
// quality bar from the brief.

export interface Band {
  point: number;
  lower: number;
  upper: number;
  rel_width: number;
  confidence: "High" | "Medium" | "Low";
}

export interface BrandRef {
  brand: string;
  category: string;
  is_zoetis: boolean;
  is_private_label: boolean;
  role: string;
}

export interface MonthRef {
  month: string;
  year: number;
  month_num: number;
  quarter: string;
}

export interface GeoRef {
  geo: string;
  geo_level: string;
  parent: string;
  share_of_parent: number;
}

export interface SourceMeta {
  channel: string;
  coverage: number;
  history: number;
  label: string;
  note: string;
}

export interface Catalog {
  categories: string[];
  channels: string[];
  brands: BrandRef[];
  geographies: GeoRef[];
  geo_levels: string[];
  months: MonthRef[];
  quarters: string[];
  sources: Record<string, SourceMeta>;
  channel_sources: Record<string, string[]>;
  window: { start: string; end: string };
}

export interface MarketShareRow {
  rank: number;
  brand: string;
  category: string;
  is_zoetis: boolean;
  is_private_label: boolean;
  sales: Band;
  share_pct: number;
  share_lower: number;
  share_upper: number;
}

export interface MarketShareResponse {
  category: string;
  channel: string;
  geo_level: string;
  geo: string;
  period_type: string;
  period: string;
  months: string[];
  total_sales: Band;
  zoetis_brand: string | null;
  zoetis_share_pct: number;
  rows: MarketShareRow[];
}

export interface SourceContribution {
  source: string;
  label: string;
  coverage: number;
  observed_sales: number;
  grossed_up: number;
  weight: number;
}

export interface TriangulationDetail {
  brand: string;
  category: string;
  is_zoetis: boolean;
  channel: string;
  geo_level: string;
  geo: string;
  period_type: string;
  period: string;
  estimate: Band;
  n_sources: number;
  combined_coverage: number;
  rel_dispersion: number;
  sources: SourceContribution[];
  interpretation: string;
}

export interface ChannelPoint {
  quarter: string;
  channel: string;
  sales: Band;
  mix_pct: number;
}
export interface ChannelMix {
  channel: string;
  start_pct: number;
  end_pct: number;
  delta_pct: number;
}
export interface ChannelViewResponse {
  scope: string;
  category: string | null;
  brand: string | null;
  geo_level: string;
  geo: string;
  quarters: string[];
  series: ChannelPoint[];
  mix: ChannelMix[];
  story: string;
}

export interface FlaggedItem {
  stage: string;
  severity: "info" | "warn" | "fail";
  entity: string;
  reason: string;
  detail: Record<string, unknown>;
}
export interface QCStage {
  stage_no: number;
  name: string;
  status: "PASS" | "REVIEW" | "FAIL";
  records_in: number;
  records_passed: number;
  flags_raised: number;
  score: number;
  summary: string;
  flagged: FlaggedItem[];
}
export interface QCReport {
  overall_status: "PASS" | "REVIEW" | "FAIL";
  quality_score: number;
  delivery_ready: boolean;
  delivery_by_business_day: number;
  delivery_note: string;
  stages: QCStage[];
  totals: Record<string, number | boolean>;
}

export interface Criterion {
  key: string;
  label: string;
  weight: number;
  description: string;
}
export interface VendorScore {
  vendor: string;
  label: string;
  blurb?: string;
  total_score: number;
  rank: number;
  is_winner: boolean;
  per_criterion: Record<string, { raw: number; weighted: number }>;
}
export interface ScoreResponse {
  criteria: Criterion[];
  vendors: VendorScore[];
  winner: string;
  winner_rationale: string;
  normalized_weights: Record<string, number>;
}
export interface CostRow {
  vendor_path: string;
  label: string;
  vendor_data_cost: number;
  improzo_service_cost: number;
  annual_total: number;
  note: string;
}
export interface CostModelResponse {
  service_tier: string;
  rows: CostRow[];
  principle: string;
  tiers: string[];
  disclaimer: string;
}

export interface Insight {
  headline: string;
  body: string;
  confidence: "High" | "Medium" | "Low";
  tags: string[];
  metrics: Record<string, number>;
}
export interface InsightsResponse {
  category: string;
  channel: string;
  geo_level: string;
  geo: string;
  period: string;
  insights: Insight[];
  generated_note: string;
}

export interface Health {
  status: string;
  service: string;
  seeds_present: boolean;
  seed: number | null;
  window: { start: string; end: string } | null;
}
