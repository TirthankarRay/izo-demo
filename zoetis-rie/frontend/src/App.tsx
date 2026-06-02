import { Route, BrowserRouter as Router, Routes } from "react-router-dom";
import { Layout } from "./components/Layout";
import { ErrorState, Loading } from "./components/ui";
import { Channels } from "./pages/Channels";
import { Dashboard } from "./pages/Dashboard";
import { Insights } from "./pages/Insights";
import { MarketShare } from "./pages/MarketShare";
import { Procurement } from "./pages/Procurement";
import { QC } from "./pages/QC";
import { FiltersProvider, useFilters } from "./state/filters";

function Boot({ children }: { children: React.ReactNode }) {
  // Block first paint on the catalog so filter-dependent pages never flash empty.
  const { loading, error } = useFilters();
  if (error) return <div style={{ padding: 28 }}><ErrorState message={error} /></div>;
  if (loading) return <Loading what="platform" />;
  return <>{children}</>;
}

export default function App() {
  return (
    <FiltersProvider>
      <Router>
        <Boot>
          <Routes>
            <Route element={<Layout />}>
              <Route path="/" element={<Dashboard />} />
              <Route path="/market-share" element={<MarketShare />} />
              <Route path="/channels" element={<Channels />} />
              <Route path="/qc" element={<QC />} />
              <Route path="/procurement" element={<Procurement />} />
              <Route path="/insights" element={<Insights />} />
            </Route>
          </Routes>
        </Boot>
      </Router>
    </FiltersProvider>
  );
}
