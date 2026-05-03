import { useEffect, useState } from "react";
import { apiCircuits } from "../hooks/useApi";

interface CircuitViewerProps {
  taskId: string;
  initialFormat?: "source" | "compiled" | "executed";
}

const TABS = [
  { id: "source", label: "Source" },
  { id: "compiled", label: "Compiled" },
  { id: "executed", label: "Executed" },
] as const;

type Tab = (typeof TABS)[number]["id"];

export function CircuitViewer({ taskId, initialFormat = "source" }: CircuitViewerProps) {
  const [activeTab, setActiveTab] = useState<Tab>(initialFormat as Tab);
  const [markup, setMarkup] = useState<string | null>(null);
  const [isSvg, setIsSvg] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    setMarkup(null);
    setIsSvg(false);
    fetch(apiCircuits.svgUrl(taskId, activeTab))
      .then((r) => {
        if (!r.ok) throw new Error(r.status === 404 ? "Circuit not available for this format." : `HTTP ${r.status}`);
        return r.text();
      })
      .then((html) => {
        // Extract SVG from the HTML returned by draw_html
        const match = html.match(/<svg[\s\S]*?<\/svg>/i);
        setMarkup(match ? match[0] : html);
        setIsSvg(Boolean(match));
      })
      .catch((e) => setError(e.message))
      .finally(() => setLoading(false));
  }, [taskId, activeTab]);

  return (
    <div className="flex flex-col gap-3">
      {/* Tabs */}
      <div className="flex gap-1 border-b border-[#1f2937]" style={{ borderBottom: "1px solid var(--border)" }}>
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            style={{
              padding: "6px 16px",
              fontSize: "0.875rem",
              fontWeight: 500,
              color: activeTab === tab.id ? "var(--accent)" : "var(--text-muted)",
              background: "none",
              border: "none",
              borderBottom: activeTab === tab.id ? "2px solid var(--accent)" : "2px solid transparent",
              cursor: "pointer",
              marginBottom: "-1px",
            }}
          >
            {tab.label}
          </button>
        ))}
        <div style={{ flex: 1 }} />
        {markup && isSvg && (
          <a
            href={`data:image/svg+xml;charset=utf-8,${encodeURIComponent(markup)}`}
            download={`circuit-${taskId}-${activeTab}.svg`}
            className="btn btn-ghost btn-sm"
            style={{ alignSelf: "center", marginBottom: "4px" }}
          >
            Download SVG
          </a>
        )}
      </div>

      {/* Content */}
      {loading && (
        <div className="skeleton" style={{ height: 200, width: "100%" }} />
      )}
      {error && (
        <div style={{
          padding: "2rem",
          textAlign: "center",
          color: "var(--text-muted)",
          background: "#1f293788",
          borderRadius: 8,
        }}>
          {error}
        </div>
      )}
      {markup && !loading && (
        <div
          style={{ overflowX: "auto", background: "#fff", borderRadius: 8, padding: 16 }}
          dangerouslySetInnerHTML={{ __html: markup }}
        />
      )}
    </div>
  );
}
