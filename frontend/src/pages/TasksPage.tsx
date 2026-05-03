import { useCallback, useEffect, useMemo, useState } from "react";
import { Archive, ChevronLeft, ChevronRight, Filter, RefreshCw, Trash2 } from "lucide-react";
import { apiTasks, TaskInfo } from "../hooks/useApi";
import { TaskCard } from "../components/TaskCard";

const STATUS_OPTIONS = ["", "pending", "running", "success", "failed", "cancelled"];
const PAGE_SIZES = [25, 50, 100, 200];

export function TasksPage() {
  const [tasks, setTasks] = useState<TaskInfo[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [actionLoading, setActionLoading] = useState(false);
  const [filterStatus, setFilterStatus] = useState("");
  const [filterBackend, setFilterBackend] = useState("");
  const [page, setPage] = useState(0);
  const [pageSize, setPageSize] = useState(50);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  const pageCount = Math.max(1, Math.ceil(total / pageSize));
  const currentIds = useMemo(() => tasks.map((task) => task.task_id), [tasks]);
  const allCurrentSelected = currentIds.length > 0 && currentIds.every((id) => selectedIds.has(id));
  const selectedCount = selectedIds.size;

  const load = useCallback(() => {
    setLoading(true);
    const params: { status?: string; backend?: string; limit: number; offset: number } = {
      limit: pageSize,
      offset: page * pageSize,
    };
    if (filterStatus) params.status = filterStatus;
    if (filterBackend) params.backend = filterBackend;
    apiTasks.list(params)
      .then((r) => {
        setTasks(r.data.tasks);
        setTotal(r.data.total);
        setSelectedIds((previous) => {
          const visible = new Set(r.data.tasks.map((task) => task.task_id));
          return new Set([...previous].filter((id) => visible.has(id)));
        });
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [filterStatus, filterBackend, page, pageSize]);

  useEffect(() => { load(); }, [load]);

  useEffect(() => { setPage(0); }, [filterStatus, filterBackend, pageSize]);

  function removeFromPage(ids: string[]) {
    const removed = new Set(ids);
    setTasks((prev) => prev.filter((task) => !removed.has(task.task_id)));
    setSelectedIds((prev) => new Set([...prev].filter((id) => !removed.has(id))));
    setTotal((prev) => Math.max(0, prev - removed.size));
  }

  async function handleDelete(taskId: string) {
    await apiTasks.delete(taskId);
    removeFromPage([taskId]);
  }

  async function handleArchive(taskId: string) {
    await apiTasks.archive(taskId);
    removeFromPage([taskId]);
  }

  function toggleAllCurrent() {
    setSelectedIds((previous) => {
      const next = new Set(previous);
      if (allCurrentSelected) {
        for (const id of currentIds) next.delete(id);
      } else {
        for (const id of currentIds) next.add(id);
      }
      return next;
    });
  }

  async function bulkArchive() {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setActionLoading(true);
    try {
      const result = await apiTasks.bulkArchive(ids);
      removeFromPage(result.data.archived);
    } finally {
      setActionLoading(false);
    }
  }

  async function bulkDelete() {
    const ids = [...selectedIds];
    if (ids.length === 0) return;
    setActionLoading(true);
    try {
      const result = await apiTasks.bulkDelete(ids);
      removeFromPage(result.data.deleted);
    } finally {
      setActionLoading(false);
    }
  }

  async function archiveExpired() {
    setActionLoading(true);
    try {
      await apiTasks.archiveExpired({ hours: 72, terminal_only: true });
      setPage(0);
      load();
    } finally {
      setActionLoading(false);
    }
  }

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "1rem" }}>
      <div className="page-header">
        <div>
          <h1>Active Tasks</h1>
          <p>{total.toLocaleString()} matching tasks · page {page + 1} of {pageCount}</p>
        </div>
        <div style={{ display: "flex", gap: 8, flexWrap: "wrap" }}>
          <button className="btn btn-ghost btn-sm" onClick={archiveExpired} disabled={actionLoading || loading}>
            <Archive size={14} /> Archive 72h+
          </button>
          <button className="btn btn-ghost btn-sm" onClick={load} disabled={loading || actionLoading}>
            <RefreshCw size={14} className={loading ? "spin" : ""} /> Refresh
          </button>
        </div>
      </div>

      <div className="toolbar">
        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <Filter size={14} style={{ color: "var(--text-muted)" }} />
          <select
            value={filterStatus}
            onChange={(e) => setFilterStatus(e.target.value)}
            className="btn btn-ghost btn-sm"
            style={{ cursor: "pointer" }}
          >
            {STATUS_OPTIONS.map((s) => (
              <option key={s} value={s}>{s === "" ? "All statuses" : s}</option>
            ))}
          </select>
          <input
            value={filterBackend}
            onChange={(e) => setFilterBackend(e.target.value)}
            placeholder="Backend filter"
            className="btn btn-ghost btn-sm"
            style={{ cursor: "text", width: 150 }}
          />
          <select
            value={pageSize}
            onChange={(e) => setPageSize(Number(e.target.value))}
            className="btn btn-ghost btn-sm"
          >
            {PAGE_SIZES.map((size) => <option key={size} value={size}>{size} / page</option>)}
          </select>
        </div>

        <div style={{ display: "flex", gap: 8, alignItems: "center", flexWrap: "wrap" }}>
          <span style={{ color: "var(--text-muted)", fontSize: "0.82rem" }}>
            {selectedCount} selected
          </span>
          <button className="btn btn-ghost btn-sm" onClick={bulkArchive} disabled={selectedCount === 0 || actionLoading}>
            <Archive size={14} /> Archive
          </button>
          <button className="btn btn-danger btn-sm" onClick={bulkDelete} disabled={selectedCount === 0 || actionLoading}>
            <Trash2 size={14} /> Delete
          </button>
        </div>
      </div>

      <div className="card" style={{ padding: 0, overflow: "hidden" }}>
        {loading ? (
          <div style={{ padding: "1.5rem", display: "flex", flexDirection: "column", gap: 8 }}>
            {[1, 2, 3, 4, 5].map((i) => <div key={i} className="skeleton" style={{ height: 44, width: "100%" }} />)}
          </div>
        ) : tasks.length === 0 ? (
          <div style={{ padding: "3rem", textAlign: "center", color: "var(--text-muted)" }}>
            No active tasks found.
          </div>
        ) : (
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: 36 }}>
                  <input
                    type="checkbox"
                    checked={allCurrentSelected}
                    onChange={toggleAllCurrent}
                    aria-label="Select all tasks on this page"
                  />
                </th>
                <th>Task ID</th>
                <th>Backend</th>
                <th>Status</th>
                <th>Shots</th>
                <th>Submitted</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              {tasks.map((task) => (
                <TaskCard
                  key={task.task_id}
                  task={task}
                  onDelete={handleDelete}
                  onArchive={handleArchive}
                  leadingColumns={1}
                  leadingCell={(
                    <td onClick={(event) => event.stopPropagation()}>
                      <input
                        type="checkbox"
                        checked={selectedIds.has(task.task_id)}
                        onChange={(event) => {
                          setSelectedIds((previous) => {
                            const next = new Set(previous);
                            if (event.target.checked) next.add(task.task_id);
                            else next.delete(task.task_id);
                            return next;
                          });
                        }}
                        aria-label={`Select task ${task.task_id}`}
                      />
                    </td>
                  )}
                />
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="pagination-bar">
        <button className="btn btn-ghost btn-sm" onClick={() => setPage((p) => Math.max(0, p - 1))} disabled={page === 0 || loading}>
          <ChevronLeft size={14} /> Prev
        </button>
        <span>{page * pageSize + 1}-{Math.min(total, (page + 1) * pageSize)} of {total}</span>
        <button className="btn btn-ghost btn-sm" onClick={() => setPage((p) => Math.min(pageCount - 1, p + 1))} disabled={page >= pageCount - 1 || loading}>
          Next <ChevronRight size={14} />
        </button>
      </div>
    </div>
  );
}
