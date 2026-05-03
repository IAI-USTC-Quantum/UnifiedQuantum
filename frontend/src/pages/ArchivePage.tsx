import { useCallback, useEffect, useState } from "react";
import { RefreshCw } from "lucide-react";
import { apiArchive, TaskInfo } from "../hooks/useApi";
import { TaskCard } from "../components/TaskCard";

export function ArchivePage() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [loading, setLoading] = useState(true);

  const load = useCallback(() => {
    setLoading(true);
    apiArchive.list({ limit: 200 })
      .then((r) => setTasks(r.data.tasks))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => { load(); }, [load]);

  async function handleDelete(taskId: string) {
    await apiArchive.delete(taskId);
    setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
  }

  async function handleRestore(taskId: string) {
    await apiArchive.restore(taskId);
    setTasks((prev) => prev.filter((t) => t.task_id !== taskId));
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1.25rem" }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <div>
          <h1 style={{ fontSize: "1.25rem", fontWeight: 700, margin: 0 }}>Archived Tasks</h1>
          <p style={{ fontSize: "0.8125rem", color: "var(--text-muted)", margin: "4px 0 0" }}>
            Archived tasks are moved to a separate storage layer for performance.
          </p>
        </div>
        <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading}>
          <RefreshCw size={14} /> Refresh
        </button>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: 8 }}>
            {[1,2,3].map(i => <div key={i} className="skeleton" style={{ height: 44, width: "100%" }} />)}
          </div>
        ) : tasks.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            No archived tasks.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th>Task ID</th>
                <th>Backend</th>
                <th>Status</th>
                <th>Shots</th>
                <th>Submitted</th>
                <th>Archived At</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((t) => (
                <TaskCard
                  key={t.task_id}
                  task={t}
                  onDelete={handleDelete}
                  onArchive={async () => {}}
                  onRestore={handleRestore}
                  showRestore
                />
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
