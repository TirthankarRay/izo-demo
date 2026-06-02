// Global filter bar -- category / channel / geography / period. Pages pass
// `show` to render only the dimensions they slice by.
import { useFilters } from "../state/filters";

type Field = "category" | "channel" | "geo" | "period";

export function FilterBar({ show = ["category", "channel", "geo", "period"] }: { show?: Field[] }) {
  const { catalog, filters, setFilter, geoOptions, periodOptions } = useFilters();
  if (!catalog) return null;
  const want = new Set(show);

  return (
    <div className="filterbar">
      {want.has("category") && (
        <div className="field">
          <label>Category</label>
          <select value={filters.category} onChange={(e) => setFilter({ category: e.target.value })}>
            {catalog.categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {want.has("channel") && (
        <div className="field">
          <label>Channel</label>
          <select value={filters.channel} onChange={(e) => setFilter({ channel: e.target.value })}>
            <option value="All">All channels</option>
            {catalog.channels.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
      )}

      {want.has("geo") && (
        <>
          <div className="field">
            <label>Geography</label>
            <select value={filters.geo_level} onChange={(e) => setFilter({ geo_level: e.target.value })}>
              {catalog.geo_levels.map((g) => <option key={g} value={g}>{g}</option>)}
            </select>
          </div>
          {filters.geo_level !== "National" && (
            <div className="field">
              <label>{filters.geo_level}</label>
              <select value={filters.geo} onChange={(e) => setFilter({ geo: e.target.value })}>
                {geoOptions.map((g) => <option key={g} value={g}>{g}</option>)}
              </select>
            </div>
          )}
        </>
      )}

      {want.has("period") && (
        <>
          <div className="field">
            <label>Period type</label>
            <select value={filters.period_type}
              onChange={(e) => setFilter({ period_type: e.target.value as "month" | "quarter", period: "latest" })}>
              <option value="quarter">Quarterly</option>
              <option value="month">Monthly</option>
            </select>
          </div>
          <div className="field">
            <label>Period</label>
            <select value={filters.period} onChange={(e) => setFilter({ period: e.target.value })}>
              {periodOptions.map((p) => <option key={p} value={p}>{p === "latest" ? "Latest" : p}</option>)}
            </select>
          </div>
        </>
      )}

      <div className="filter-spacer">Window {catalog.window.start} → {catalog.window.end}</div>
    </div>
  );
}
