// App shell: top bar with brand + capability nav, routed content, synthetic footer.
import { NavLink, Outlet } from "react-router-dom";
import { Synthetic } from "./ui";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/market-share", label: "Market Share" },
  { to: "/channels", label: "Channels" },
  { to: "/qc", label: "QC Scorecard" },
  { to: "/procurement", label: "Procurement" },
  { to: "/insights", label: "Insights" },
];

export function Layout() {
  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span>Zoetis</span> <span className="mark">RIE</span>
          <span className="sub">Retail Intelligence Engine</span>
        </div>
        <nav className="nav">
          {NAV.map((n) => (
            <NavLink key={n.to} to={n.to} end={n.end}
              className={({ isActive }) => (isActive ? "active" : "")}>
              {n.label}
            </NavLink>
          ))}
        </nav>
      </header>
      <main className="content">
        <Outlet />
      </main>
      <Synthetic />
    </div>
  );
}
