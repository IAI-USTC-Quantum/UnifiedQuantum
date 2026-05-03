import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { Cpu, Layers, CheckCircle, Clock } from "lucide-react";
import { apiBackends, apiTasks, apiArchive, TaskCounts, BackendSummary } from "../hooks/useApi";
import { StatusBadge } from "../components/StatusBadge";
import { ChipTopology } from "../components/ChipTopology";

interface Stats {
  counts: TaskCounts | null;
  backendCount: number;
  archivedCount: number;
}

export function Dashboard() {
  const [stats, setStats] = useState<Stats>({ counts: null, backendCount: 0, archivedCount: 0 });
  const [backends, setBackends] = useState<BackendSummary[]>([]);
  const [recentTasks, setRecentTasks] = useState<Awaited<ReturnType<typeof apiTasks.list>>["data"]["tasks"]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.all([
      apiTasks.counts().then((r) => r.data),
      apiBackends.listLive().then((r) => r.data),
      apiTasks.list({ limit: 8 }).then((r) => r.data.tasks),
      apiArchive.list({ limit: 1 }).then((r) => r.data.count ?? r.data.total),
    ])
      .then(([counts, liveBackends, tasks, archivedCount]) => {
        setStats({ counts, backendCount: liveBackends.length, archivedCount });
        setBackends([...liveBackends].sort((a, b) =>
          Number(Boolean(b.available)) - Number(Boolean(a.available))
          || Number(Boolean(b.is_hardware)) - Number(Boolean(a.is_hardware))
          || a.platform.localeCompare(b.platform)
          || a.name.localeCompare(b.name)
        ));
        setRecentTasks(tasks);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const cards = [
    {
      label: "Backends",
      value: stats.backendCount,
      icon: <Cpu size={20} />,
      color: "var(--accent)",
      to: "/backends",
    },
    {
      label: "Active Tasks",
      value: stats.counts?.total ?? "—",
      icon: <Layers size={20} />,
      color: "#7c3aed",
      to: "/tasks",
    },
    {
      label: "Succeeded",
      value: stats.counts?.success ?? "—",
      icon: <CheckCircle size={20} />,
      color: "var(--success)",
      to: "/tasks?status=success",
    },
    {
      label: "Archived",
      value: stats.archivedCount,
      icon: <Clock size={20} />,
      color: "var(--text-muted)",
      to: "/archive",
    },
  ];

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.5rem" }}>
      {/* Stats */}
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(180px, 1fr))", gap: 16 }}>
        {cards.map((c) => (
          <Link key={c.label} to={c.to} style={{ textDecoration: "none" }}>
            <div className="card" style={{ display: "flex", flexDirection: "column", gap: 8 }}>
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <span style={{ fontSize: "0.8125rem", color: "var(--text-muted)" }}>{c.label}</span>
                <span style={{ color: c.color }}>{c.icon}</span>
              </div>
              <div style={{ fontSize: "2rem", fontWeight: 700, color: "var(--text)" }}>
                {loading ? <span className="skeleton" style={{ display: "block", height: 40, width: 60 }} /> : c.value}
              </div>
            </div>
          </Link>
        ))}
      </div>

      {/* Chip topologies */}
      {backends.length > 0 && (
        <div>
          <h2 style={{ fontSize: "1rem", fontWeight: 600, marginBottom: 12, color: "var(--text-muted)" }}>
            Chip Topologies
          </h2>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill, minmax(280px, 1fr))", gap: 16 }}>
            {backends.slice(0, 6).map((b) => (
              <div key={b.id} className="card">
                <div style={{ display: "flex", justifyContent: "space-between", marginBottom: 8 }}>
                  <div>
                    <div style={{ fontWeight: 600, fontSize: "0.9rem" }}>{b.name}</div>
                    <div style={{ fontSize: "0.75rem", color: "var(--text-muted)" }}>{b.platform} · {b.num_qubits} qubits</div>
                  </div>
                  <StatusBadge status={b.available ? "available" : (b.status_kind ?? b.status)} />
                </div>
                <ChipTopology
                  nodes={b.topology.nodes}
                  edges={b.topology.edges}
                  fidelity={b.fidelity}
                  height={160}
                  compact
                />
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Recent tasks */}
      {recentTasks.length > 0 && (
        <div>
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 12 }}>
            <h2 style={{ fontSize: "1rem", fontWeight: 600, color: "var(--text-muted)", margin: 0 }}>Recent Tasks</h2>
            <Link to="/tasks" style={{ fontSize: "0.8125rem", color: "var(--accent)" }}>View all →</Link>
          </div>
          <div className="card" style={{ padding: 0, overflow: "hidden" }}>
            <table className="data-table">
              <thead>
                <tr>
                  <th>Task ID</th>
                  <th>Backend</th>
                  <th>Status</th>
                  <th>Shots</th>
                  <th>Submitted</th>
                </tr>
              </thead>
              <tbody>
                {recentTasks.map((t) => (
                  <tr key={t.task_id} onClick={() => {}} style={{ cursor: "default" }}>
                    <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--accent)" }}>
                      {t.task_id.slice(0, 16)}…
                    </td>
                    <td>{t.backend}</td>
                    <td><StatusBadge status={t.status} /></td>
                    <td>{t.shots.toLocaleString()}</td>
                    <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>
                      {new Date(t.submit_time).toLocaleString()}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {backends.length === 0 && !loading && (
        <div className="card" style={{ textAlign: "center", padding: "3rem", color: "var(--text-muted)" }}>
          <Cpu size={40} style={{ margin: "0 auto 1rem", opacity: 0.4 }} />
          <p>No backends found. Configure your platform tokens with <code style={{ color: "var(--accent)" }}>uniqc config set</code>.</p>
        </div>
      )}
    </div>
  );
}
