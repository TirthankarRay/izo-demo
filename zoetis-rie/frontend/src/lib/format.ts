// Formatting helpers shared across pages.

export function usd(v: number): string {
  if (v >= 1_000_000_000) return `$${(v / 1_000_000_000).toFixed(2)}B`;
  if (v >= 1_000_000) return `$${(v / 1_000_000).toFixed(1)}M`;
  if (v >= 1_000) return `$${(v / 1_000).toFixed(0)}K`;
  return `$${v.toFixed(0)}`;
}

export function usdFull(v: number): string {
  return v.toLocaleString("en-US", { style: "currency", currency: "USD", maximumFractionDigits: 0 });
}

export function pct(v: number, digits = 1): string {
  return `${v.toFixed(digits)}%`;
}

export function signedPct(v: number, digits = 1): string {
  return `${v >= 0 ? "+" : ""}${v.toFixed(digits)}`;
}

export function deltaClass(v: number): "up" | "down" | "flat" {
  if (v > 0.05) return "up";
  if (v < -0.05) return "down";
  return "flat";
}

// Stable, neutral palette for competitor series; the Zoetis brand always uses gold.
const ZOETIS_GOLD = "#e0a82e";
const PRIVATE_LABEL = "#94a3b8";
const PALETTE = ["#4f46e5", "#0ea5e9", "#14b8a6", "#6366f1", "#475569", "#0891b2"];

export function brandColor(opts: { is_zoetis?: boolean; is_private_label?: boolean; index: number }): string {
  if (opts.is_zoetis) return ZOETIS_GOLD;
  if (opts.is_private_label) return PRIVATE_LABEL;
  return PALETTE[opts.index % PALETTE.length];
}

export const CHANNEL_COLORS: Record<string, string> = {
  Veterinary: "#4f46e5",
  Retail: "#14b8a6",
  "E-commerce": "#e0a82e",
};

export function statusClass(status: string): string {
  return status.toLowerCase();
}
