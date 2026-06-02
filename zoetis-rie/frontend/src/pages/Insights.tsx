import { FilterBar } from "../components/FilterBar";
import { Card, ConfidencePill, ErrorState, Loading } from "../components/ui";
import { api } from "../lib/api";
import { useAsync } from "../lib/useAsync";
import { useFilters } from "../state/filters";

export function Insights() {
  const { filters, catalog } = useFilters();
  const cat = filters.category;

  const res = useAsync(() => api.insights({
    category: cat, channel: filters.channel, geo_level: filters.geo_level, geo: filters.geo,
  }), [cat, filters.channel, filters.geo_level, filters.geo]);

  if (!cat || !catalog) return <Loading what="catalog" />;

  return (
    <>
      <div className="page-head">
        <h1>Insight Narratives</h1>
        <p>The narrative section of the monthly deliverable — conclusion first, evidence second. Generated deterministically from the computed estimates, with every claim citing its confidence band.</p>
      </div>
      <FilterBar show={["category", "channel", "geo"]} />
      {res.error && <ErrorState message={res.error} />}
      {res.loading && <Loading what="insights" />}

      {res.data && (
        <>
          <div className="row" style={{ justifyContent: "space-between", alignItems: "baseline", marginBottom: 12 }}>
            <div style={{ fontWeight: 700, fontSize: 15 }}>
              {res.data.category} · {res.data.channel} · {res.data.geo} · {res.data.period}
            </div>
            <div className="note">{res.data.insights.length} insights</div>
          </div>

          <div className="grid" style={{ gridTemplateColumns: "1fr", gap: 12 }}>
            {res.data.insights.map((ins, i) => (
              <Card key={i} className="insight-card">
                <div className="row" style={{ justifyContent: "space-between", alignItems: "flex-start", gap: 12 }}>
                  <div className="headline">{ins.headline}</div>
                  <ConfidencePill confidence={ins.confidence} />
                </div>
                <div className="body">{ins.body}</div>
                <div className="tags">
                  {ins.tags.map((t) => <span key={t} className="tag">{t}</span>)}
                </div>
              </Card>
            ))}
          </div>

          <div className="note" style={{ marginTop: 14, fontStyle: "italic" }}>{res.data.generated_note}</div>
        </>
      )}
    </>
  );
}
