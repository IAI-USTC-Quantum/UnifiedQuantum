import { useState, type ReactNode } from "react";
import { Eye, Archive, Trash2, RotateCcw } from "lucide-react";
import { apiArchive, apiTasks, TaskInfo } from "../hooks/useApi";
import { StatusBadge } from "./StatusBadge";
import { CircuitViewer } from "./CircuitViewer";

interface TaskCardProps {
  task: TaskInfo;
  onDelete: (id: string) => void | Promise<void>;
  onArchive?: (id: string) => Promise<void>;
  onRestore?: (id: string) => Promise<void>;
  showRestore?: boolean;
  leadingCell?: ReactNode;
  leadingColumns?: number;
}

export function TaskCard({ task, onDelete, onArchive, onRestore, showRestore = false, leadingCell, leadingColumns = 0 }: TaskCardProps) {
  const [expanded, setExpanded] = useState(false);
  const [confirmDelete, setConfirmDelete] = useState(false);
  const [actionLoading, setActionLoading] = useState(false);
  const [detail, setDetail] = useState<TaskInfo | null>(null);
  const [detailLoading, setDetailLoading] = useState(false);
  const [detailError, setDetailError] = useState<string | null>(null);

  async function handleArchive() {
    if (!onArchive) return;
    setActionLoading(true);
    try { await onArchive(task.task_id); } finally { setActionLoading(false); }
  }

  async function handleDelete() {
    if (!confirmDelete) { setConfirmDelete(true); return; }
    setActionLoading(true);
    try { await onDelete(task.task_id); } finally { setActionLoading(false); setConfirmDelete(false); }
  }

  function openDetails() {
    setExpanded(true);
    if (detail || detailLoading) return;
    setDetailLoading(true);
    setDetailError(null);
    const request = showRestore ? apiArchive.get(task.task_id) : apiTasks.get(task.task_id);
    request
      .then((r) => setDetail(r.data))
      .catch((e) => setDetailError(e?.message ?? "Failed to load task details."))
      .finally(() => setDetailLoading(false));
  }

  const displayTask = detail ?? task;
  const ts = task.submit_time ? new Date(task.submit_time).toLocaleString() : "N/A";
  const archivedTs = task.archived_at ? new Date(task.archived_at).toLocaleString() : "N/A";
  const colSpan = (showRestore ? 7 : 6) + leadingColumns;

  return (
    <>
      <tr onClick={() => expanded ? setExpanded(false) : openDetails()}>
        {leadingCell}
        <td style={{ fontFamily: "monospace", fontSize: "0.8rem", color: "var(--accent)" }}>
          {task.task_id.slice(0, 16)}…
        </td>
        <td>{task.backend}</td>
        <td><StatusBadge status={task.status} /></td>
        <td>{task.shots.toLocaleString()}</td>
        <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>{ts}</td>
        {showRestore && (
          <td style={{ color: "var(--text-muted)", fontSize: "0.8125rem" }}>{archivedTs}</td>
        )}
        <td onClick={(e) => e.stopPropagation()}>
          <div style={{ display: "flex", gap: 6 }}>
            <button
              className="btn btn-ghost btn-sm"
              onClick={openDetails}
              title="View circuit"
            >
              <Eye size={14} />
            </button>
            {showRestore && onRestore && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={() => { setActionLoading(true); onRestore(task.task_id).finally(() => setActionLoading(false)); }}
                disabled={actionLoading}
                title="Restore"
              >
                <RotateCcw size={14} />
              </button>
            )}
            {!showRestore && (
              <button
                className="btn btn-ghost btn-sm"
                onClick={handleArchive}
                disabled={actionLoading}
                title="Archive"
              >
                <Archive size={14} />
              </button>
            )}
            <button
              className={`btn btn-sm ${confirmDelete ? "btn-danger" : "btn-ghost"}`}
              onClick={handleDelete}
              disabled={actionLoading}
              title={confirmDelete ? "Click again to confirm" : "Delete"}
            >
              <Trash2 size={14} />
            </button>
          </div>
        </td>
      </tr>

      {/* Expanded drawer */}
      {expanded && (
        <tr>
          <td colSpan={colSpan} style={{ padding: 0 }}>
            <div
              style={{
                background: "#0d1320",
                borderBottom: "1px solid var(--border)",
                padding: "1rem 1.5rem",
              }}
            >
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
                <strong>Circuit — {task.task_id}</strong>
                <button className="btn btn-ghost btn-sm" onClick={() => setExpanded(false)}>X</button>
              </div>
              {detailLoading && <div className="skeleton" style={{ height: 46, width: "100%", marginBottom: 12 }} />}
              {detailError && (
                <div style={{ color: "var(--error)", marginBottom: 12, fontSize: "0.875rem" }}>
                  {detailError}
                </div>
              )}
              <CircuitViewer taskId={task.task_id} />
              {displayTask.result && (
                <div className="card" style={{ marginTop: "1rem" }}>
                  <strong style={{ fontSize: "0.875rem", marginBottom: "0.5rem", display: "block" }}>
                    Results
                  </strong>
                  <pre style={{ fontSize: "0.8rem", color: "var(--text-muted)", overflowX: "auto" }}>
                    {JSON.stringify(displayTask.result, null, 2)}
                  </pre>
                </div>
              )}
              {displayTask.metadata && Object.keys(displayTask.metadata).length > 0 && (
                <details style={{ marginTop: "1rem" }}>
                  <summary style={{ cursor: "pointer", color: "var(--text-muted)", fontSize: "0.875rem" }}>
                    Metadata
                  </summary>
                  <pre style={{ fontSize: "0.8rem", color: "var(--text-muted)", overflowX: "auto" }}>
                    {JSON.stringify(displayTask.metadata, null, 2)}
                  </pre>
                </details>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
