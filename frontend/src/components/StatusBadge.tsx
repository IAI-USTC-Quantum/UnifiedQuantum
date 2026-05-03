interface StatusBadgeProps {
  status: string;
}

const STATUS_CLASS: Record<string, string> = {
  available: "badge-success",
  online: "badge-success",
  success: "badge-success",
  pending: "badge-pending",
  deprecated: "badge-pending",
  unavailable: "badge-failed",
  offline: "badge-failed",
  unknown: "badge-cancelled",
  running: "badge-running",
  busy: "badge-running",
  failed: "badge-failed",
  cancelled: "badge-cancelled",
};

export function StatusBadge({ status }: StatusBadgeProps) {
  const cls = STATUS_CLASS[status.toLowerCase()] ?? "badge-cancelled";
  return <span className={`badge ${cls}`}>{status}</span>;
}
