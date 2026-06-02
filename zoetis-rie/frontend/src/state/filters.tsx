// Global filter state (category / channel / geography / period) shared across
// every page, plus the catalog used to populate the filter bar. Fetched once.
import { createContext, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { api } from "../lib/api";
import type { Catalog } from "../lib/types";

export interface Filters {
  category: string;
  channel: string; // "All" or a specific channel
  geo_level: string; // National | Region | Metro
  geo: string;
  period_type: "month" | "quarter";
  period: string; // id or "latest"
}

interface Ctx {
  catalog: Catalog | null;
  loading: boolean;
  error: string | null;
  filters: Filters;
  setFilter: (patch: Partial<Filters>) => void;
  geoOptions: string[];
  periodOptions: string[];
}

const FiltersContext = createContext<Ctx | null>(null);

const DEFAULT: Filters = {
  category: "",
  channel: "All",
  geo_level: "National",
  geo: "National",
  period_type: "quarter",
  period: "latest",
};

export function FiltersProvider({ children }: { children: ReactNode }) {
  const [catalog, setCatalog] = useState<Catalog | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT);

  useEffect(() => {
    let alive = true;
    api
      .catalog()
      .then((c) => {
        if (!alive) return;
        setCatalog(c);
        setFilters((f) => ({ ...f, category: f.category || c.categories[0] }));
        setLoading(false);
      })
      .catch((e) => {
        if (!alive) return;
        setError(String(e));
        setLoading(false);
      });
    return () => {
      alive = false;
    };
  }, []);

  const setFilter = (patch: Partial<Filters>) =>
    setFilters((f) => {
      const next = { ...f, ...patch };
      // keep geography coherent when the level changes -- pick a valid member
      // immediately so no empty-geo request is ever issued
      if (patch.geo_level && patch.geo_level !== f.geo_level) {
        if (patch.geo_level === "National") {
          next.geo = "National";
        } else {
          const first = catalog?.geographies.find((g) => g.geo_level === patch.geo_level);
          next.geo = first?.geo ?? "";
        }
      }
      return next;
    });

  const geoOptions = useMemo(() => {
    if (!catalog) return ["National"];
    if (filters.geo_level === "National") return ["National"];
    return catalog.geographies
      .filter((g) => g.geo_level === filters.geo_level)
      .map((g) => g.geo);
  }, [catalog, filters.geo_level]);

  // default a region/metro selection when switching level
  useEffect(() => {
    if (filters.geo_level !== "National" && !geoOptions.includes(filters.geo) && geoOptions.length) {
      setFilters((f) => ({ ...f, geo: geoOptions[0] }));
    }
  }, [filters.geo_level, geoOptions, filters.geo]);

  const periodOptions = useMemo(() => {
    if (!catalog) return ["latest"];
    const base = filters.period_type === "quarter"
      ? [...catalog.quarters]
      : catalog.months.map((m) => m.month);
    return ["latest", ...base.reverse()];
  }, [catalog, filters.period_type]);

  return (
    <FiltersContext.Provider
      value={{ catalog, loading, error, filters, setFilter, geoOptions, periodOptions }}
    >
      {children}
    </FiltersContext.Provider>
  );
}

export function useFilters(): Ctx {
  const ctx = useContext(FiltersContext);
  if (!ctx) throw new Error("useFilters must be used within FiltersProvider");
  return ctx;
}
