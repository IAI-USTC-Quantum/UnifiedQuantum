import { useEffect, useMemo, useState } from "react";
import { Activity, Cpu, RefreshCw, Search, Server, Timer } from "lucide-react";
import { apiBackends, BackendSummary } from "../hooks/useApi";
import { StatusBadge } from "../components/StatusBadge";
import { ChipTopology } from "../components/ChipTopology";

const AVAILABILITY_FILTERS = [
  { id: "available", label: "Available" },
  { id: "all", label: "All" },
] as const;

const TYPE_FILTERS = [
  { id: "hardware", label: "Hardware" },
  { id: "simulator", label: "Simulator" },
  { id: "all", label: "All" },
] as const;

const PLATFORM_FILTERS = [
  { id: "all", label: "All" },
  { id: "originq", label: "OriginQ" },
  { id: "ibm", label: "IBM" },
  { id: "quafu", label: "Quafu" },
] as const;

type AvailabilityFilter = (typeof AVAILABILITY_FILTERS)[number]["id"];
type TypeFilter = (typeof TYPE_FILTERS)[number]["id"];
type PlatformFilter = (typeof PLATFORM_FILTERS)[number]["id"];

function fmtPercent(value: number | null | undefined): string {
  return value == null ? "N/A" : `${(value * 100).toFixed(2)}%`;
}

function fmtTime(value: number | null | undefined): string {
  if (value == null) return "N/A";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} ms`;
  return `${value.toFixed(2)} us`;
}

function fmtAge(seconds: number | null | undefined): string {
  if (seconds == null) return "N/A";
  if (seconds < 3600) return `${Math.round(seconds / 60)} min`;
  if (seconds < 86400) return `${Math.round(seconds / 3600)} h`;
  return `${Math.round(seconds / 86400)} d`;
}

function statusForBackend(backend: BackendSummary): string {
  if (backend.available) return "available";
  if (backend.status_kind === "deprecated") return "deprecated";
  if (backend.status_kind === "busy") return "running";
  if (backend.status_kind === "unavailable") return "unavailable";
  return backend.status || "unknown";
}

function metric(label: string, value: string) {
  return (
    <div className="metric-tile">
      <div className="metric-label">{label}</div>
      <div className="metric-value">{value}</div>
    </div>
  );
}

export function BackendsPage() {
  const [backends, setBackends] = useState<BackendSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [availabilityFilter, setAvailabilityFilter] = useState<AvailabilityFilter>("available");
  const [typeFilter, setTypeFilter] = useState<TypeFilter>("hardware");
  const [platformFilter, setPlatformFilter] = useState<PlatformFilter>("all");
  const [query, setQuery] = useState("");
  const [refreshingBackends, setRefreshingBackends] = useState(false);

  function load() {
    setLoading(true);
    apiBackends.listLive()
      .then((r) => {
        const list = r.data.sort((a, b) => Number(Boolean(b.available)) - Number(Boolean(a.available)) || a.platform.localeCompare(b.platform) || a.name.localeCompare(b.name));
        setBackends(list);
        setSelectedId((current) => current ?? list.find((backend) => backend.available)?.id ?? list[0]?.id ?? null);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }

  useEffect(() => { load(); }, []);

  async function refreshBackendCache() {
    setRefreshingBackends(true);
    try {
      await apiBackends.refresh();
      load();
    } finally {
      setRefreshingBackends(false);
    }
  }

  const summary = useMemo(() => ({
    total: backends.length,
    available: backends.filter((backend) => backend.available).length,
    hardware: backends.filter((backend) => backend.is_hardware).length,
    simulators: backends.filter((backend) => backend.is_simulator).length,
    stale: backends.filter((backend) => backend.cache_stale || backend.calibration?.cache_stale).length,
  }), [backends]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return backends.filter((backend) => {
      if (availabilityFilter === "available" && !backend.available) return false;
      if (typeFilter === "hardware" && !backend.is_hardware) return false;
      if (typeFilter === "simulator" && !backend.is_simulator) return false;
      if (platformFilter !== "all" && backend.platform !== platformFilter) return false;
      if (!normalizedQuery) return true;
      return `${backend.platform} ${backend.name} ${backend.id}`.toLowerCase().includes(normalizedQuery);
    });
  }, [backends, availabilityFilter, typeFilter, platformFilter, query]);

  const selected = filtered.find((backend) => backend.id === selectedId) ?? filtered[0] ?? null;

  return (
    <div className="backend-page">
      <div className="page-header">
        <div>
          <h1>Backends</h1>
          <p>{summary.available} available of {summary.total} cached backends</p>
        </div>
        <div style={{ display: "flex", gap: 8 }}>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading || refreshingBackends}>
            <RefreshCw size={14} className={loading ? "spin" : ""} /> Reload
          </button>
          <button className="btn btn-primary btn-sm" onClick={refreshBackendCache} disabled={loading || refreshingBackends}>
            <RefreshCw size={14} className={refreshingBackends ? "spin" : ""} /> Update Backends
          </button>
        </div>
      </div>

      <div className="summary-strip">
        <div><Cpu size={16} /><span>{summary.available}</span><small>available</small></div>
        <div><Server size={16} /><span>{summary.hardware}</span><small>hardware</small></div>
        <div><Activity size={16} /><span>{summary.simulators}</span><small>simulators</small></div>
        <div><Timer size={16} /><span>{summary.stale}</span><small>stale caches</small></div>
      </div>

      <div className="toolbar">
        <div className="filter-stack">
          <div className="segmented" aria-label="Availability filter">
            {AVAILABILITY_FILTERS.map((item) => (
              <button
                key={item.id}
                className={availabilityFilter === item.id ? "active" : ""}
                onClick={() => setAvailabilityFilter(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="segmented" aria-label="Backend type filter">
            {TYPE_FILTERS.map((item) => (
              <button
                key={item.id}
                className={typeFilter === item.id ? "active" : ""}
                onClick={() => setTypeFilter(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
          <div className="segmented" aria-label="Platform filter">
            {PLATFORM_FILTERS.map((item) => (
              <button
                key={item.id}
                className={platformFilter === item.id ? "active" : ""}
                onClick={() => setPlatformFilter(item.id)}
              >
                {item.label}
              </button>
            ))}
          </div>
        </div>
        <label className="search-box">
          <Search size={14} />
          <input
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search backend"
          />
        </label>
      </div>

      <div className="backend-layout">
        <div className="backend-list">
          {loading && [1, 2, 3, 4].map((item) => (
            <div key={item} className="card">
              <div className="skeleton" style={{ height: 18, width: "50%", marginBottom: 12 }} />
              <div className="skeleton" style={{ height: 150, width: "100%" }} />
            </div>
          ))}

          {!loading && filtered.length === 0 && (
            <div className="empty-state">
              No backends match the current filter.
            </div>
          )}

          {!loading && filtered.map((backend) => (
            <button
              key={backend.id}
              className={`backend-card ${selected?.id === backend.id ? "selected" : ""}`}
              onClick={() => setSelectedId(backend.id)}
            >
              <div className="backend-card-header">
                <div>
                  <strong>{backend.name}</strong>
                  <span>{backend.platform} · {backend.num_qubits} qubits · {backend.is_simulator ? "simulator" : "hardware"}</span>
                </div>
                <StatusBadge status={statusForBackend(backend)} />
              </div>
              <ChipTopology
                nodes={backend.topology.nodes}
                edges={backend.topology.edges}
                fidelity={backend.fidelity}
                height={154}
                compact
              />
              <div className="backend-card-metrics">
                {metric("1Q", fmtPercent(backend.fidelity.avg_1q))}
                {metric("2Q", fmtPercent(backend.fidelity.avg_2q))}
                {metric("Readout", fmtPercent(backend.fidelity.avg_readout))}
              </div>
            </button>
          ))}
        </div>

        {selected && (
          <aside className="backend-inspector">
            <div className="inspector-title">
              <div>
                <h2>{selected.name}</h2>
                <p>{selected.id}</p>
              </div>
              <StatusBadge status={statusForBackend(selected)} />
            </div>

            <ChipTopology
              nodes={selected.topology.nodes}
              edges={selected.topology.edges}
              fidelity={selected.fidelity}
              height={320}
            />

            <div className="metric-grid">
              {metric("Qubits", selected.num_qubits.toLocaleString())}
              {metric("Connectivity", selected.topology.has_connectivity ? `${selected.topology.edges.length} edges` : "No graph")}
              {metric("Queue", selected.queue_size == null ? "N/A" : String(selected.queue_size))}
              {metric("Cal age", fmtAge(selected.calibration?.cache_age_seconds))}
              {metric("Avg T1", fmtTime(selected.coherence.t1))}
              {metric("Avg T2", fmtTime(selected.coherence.t2))}
            </div>

            <div className="inspector-section">
              <h3>Calibration</h3>
              <dl>
                <div><dt>Source</dt><dd>{selected.calibration?.source ?? "backend-cache"}</dd></div>
                <div><dt>Calibrated</dt><dd>{selected.calibration?.calibrated_at ? new Date(selected.calibration.calibrated_at).toLocaleString() : "N/A"}</dd></div>
                <div><dt>Cache stale</dt><dd>{selected.calibration?.cache_stale || selected.cache_stale ? "Yes" : "No"}</dd></div>
              </dl>
            </div>

            <div className="inspector-section">
              <h3>Supported Gates</h3>
              {selected.supported_gates && selected.supported_gates.length > 0 ? (
                <div className="gate-list">
                  {selected.supported_gates.slice(0, 40).map((gate) => <span key={gate}>{gate}</span>)}
                </div>
              ) : (
                <p className="muted">No gate list in cache.</p>
              )}
            </div>

            {selected.description && (
              <div className="inspector-section">
                <h3>Description</h3>
                <p className="muted">{selected.description}</p>
              </div>
            )}
          </aside>
        )}
      </div>
    </div>
  );
}
