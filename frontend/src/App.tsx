import { Link, NavLink, Outlet } from "react-router-dom";
import { LayoutDashboard, Cpu, Layers, Archive, Wifi, WifiOff, Github, BookOpen } from "lucide-react";
import { useWebSocket } from "./hooks/useWebSocket";
import { useEffect, useState } from "react";
import { apiGateway, type GatewayVersion } from "./hooks/useApi";

const NAV = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/backends", label: "Backends", icon: Cpu },
  { to: "/tasks", label: "Tasks", icon: Layers },
  { to: "/archive", label: "Archive", icon: Archive },
];

export default function App() {
  const { lastEvent, connected } = useWebSocket();
  const [notif, setNotif] = useState<string | null>(null);
  const [gatewayInfo, setGatewayInfo] = useState<GatewayVersion | null>(null);

  useEffect(() => {
    apiGateway.version()
      .then((res) => setGatewayInfo(res.data))
      .catch(() => setGatewayInfo(null));
  }, []);

  useEffect(() => {
    if (!lastEvent) return;
    const { type, payload } = lastEvent;
    if (type === "task:updated") {
      setNotif(`Task ${String(payload.task_id).slice(0, 12)}… → ${String(payload.status)}`);
      setTimeout(() => setNotif(null), 4000);
    }
  }, [lastEvent]);

  const githubUrl = gatewayInfo?.github_url ?? "https://github.com/IAI-USTC-Quantum/UnifiedQuantum";
  const docsUrl = gatewayInfo?.docs_url ?? "https://iai-ustc-quantum.github.io/UnifiedQuantum/";
  const version = gatewayInfo?.version ?? "unknown";

  return (
    <div style={{ display: "flex", minHeight: "100vh" }}>
      {/* Sidebar */}
      <nav style={{
        width: 220,
        minHeight: "100vh",
        background: "#0d1320",
        borderRight: "1px solid var(--border)",
        display: "flex",
        flexDirection: "column",
        padding: "1rem 0.75rem",
        position: "sticky",
        top: 0,
        height: "100vh",
        overflowY: "auto",
      }}>
        {/* Logo */}
        <div style={{ padding: "0.5rem 0.75rem", marginBottom: "1rem" }}>
          <Link to="/" style={{ textDecoration: "none" }}>
            <div style={{ fontSize: "1.1rem", fontWeight: 800, color: "var(--accent)", letterSpacing: "-0.02em" }}>
              uniqc
            </div>
            <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>Gateway</div>
          </Link>
        </div>

        {/* WS status */}
        <div style={{ padding: "0 0.75rem", marginBottom: "0.75rem" }}>
          <div style={{
            display: "flex", alignItems: "center", gap: 6,
            fontSize: "0.75rem", color: "var(--text-muted)",
          }}>
            {connected
              ? <><Wifi size={11} style={{ color: "var(--success)" }} /> Live</>
              : <><WifiOff size={11} style={{ color: "var(--warning)" }} /> Polling</>
            }
          </div>
        </div>

        {/* Nav links */}
        {NAV.map(({ to, label, icon: Icon }) => (
          <NavLink
            key={to}
            to={to}
            end={to === "/"}
            className={({ isActive }) => `nav-link ${isActive ? "active" : ""}`}
          >
            <Icon size={16} /> {label}
          </NavLink>
        ))}

        {/* Footer */}
        <div className="sidebar-footer">
          <div className="sidebar-footer-links">
            <a href={githubUrl} target="_blank" rel="noreferrer" title="Open GitHub repository">
              <Github size={13} /> GitHub
            </a>
            <a href={docsUrl} target="_blank" rel="noreferrer" title="Open GitHub Pages documentation">
              <BookOpen size={13} /> GitHub.io
            </a>
          </div>
          <div className="sidebar-version">uniqc v{version}</div>
        </div>
      </nav>

      {/* Main content */}
      <main style={{ flex: 1, padding: "1.5rem 2rem", minWidth: 0 }}>
        {/* Notification banner */}
        {notif && (
          <div style={{
            position: "fixed",
            bottom: 20,
            right: 20,
            background: "#1a2035",
            border: "1px solid var(--accent)",
            borderRadius: 10,
            padding: "10px 16px",
            fontSize: "0.875rem",
            color: "var(--accent)",
            boxShadow: "0 4px 20px #00d4ff22",
            zIndex: 200,
          }}>
            {notif}
          </div>
        )}
        <Outlet />
      </main>
    </div>
  );
}
