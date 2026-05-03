import axios from "axios";

const api = axios.create({
  baseURL: "/api",
  headers: { "Content-Type": "application/json" },
});

export default api;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface BackendSummary {
  id: string;
  name: string;
  platform: string;
  num_qubits: number;
  status: string;
  status_kind?: "available" | "busy" | "deprecated" | "unavailable" | "unknown";
  available?: boolean;
  cache_stale?: boolean;
  is_simulator: boolean;
  is_hardware: boolean;
  topology: {
    nodes: {
      id: number | string;
      available?: boolean;
      t1?: number | null;
      t2?: number | null;
      freq?: number | null;
      single_gate_fidelity?: number | null;
      avg_readout_fidelity?: number | null;
      readout_fidelity_0?: number | null;
      readout_fidelity_1?: number | null;
    }[];
    edges: {
      u: number;
      v: number;
      fidelity?: number | null;
      gates?: { gate: string; fidelity?: number | null }[];
    }[];
    has_connectivity?: boolean;
  };
  fidelity: { avg_1q: number | null; avg_2q: number | null; avg_readout: number | null };
  coherence: { t1: number | null; t2: number | null };
  queue_size?: number | null;
  supported_gates?: string[];
  calibration?: {
    available: boolean;
    calibrated_at?: string | null;
    cache_age_seconds?: number | null;
    cache_stale?: boolean | null;
    source?: string;
  };
  description: string;
  extra: Record<string, unknown>;
}

export interface TaskInfo {
  task_id: string;
  backend: string;
  status: string;
  shots: number;
  submit_time: string;
  update_time: string;
  has_result: boolean;
  metadata: Record<string, unknown>;
  archived_at?: string | null;
  result?: Record<string, unknown> | null;
}

export interface TaskListResponse {
  tasks: TaskInfo[];
  total: number;
  count?: number;  // present in archive list responses
  limit?: number | null;
  offset?: number;
}

export interface TaskCounts {
  pending: number;
  running: number;
  success: number;
  failed: number;
  cancelled: number;
  total: number;
}

export interface GatewayVersion {
  version: string;
  github_url: string;
  docs_url: string;
}

// ---------------------------------------------------------------------------
// API functions
// ---------------------------------------------------------------------------

export const apiBackends = {
  list: () => api.get<Record<string, BackendSummary[]>>("/backends"),
  listLive: () => api.get<BackendSummary[]>("/backends/live"),
  get: (id: string) => api.get<BackendSummary>(`/backends/${id}`),
  refresh: (params?: { platform?: string }) =>
    api.post<{ updated: Record<string, number>; warnings: string[]; total: number }>("/backends/refresh", null, { params }),
};

export const apiGateway = {
  version: () => api.get<GatewayVersion>("/version"),
};

export const apiTasks = {
  list: (params?: { status?: string; backend?: string; limit?: number; offset?: number }) =>
    api.get<TaskListResponse>("/tasks", { params }),
  counts: () => api.get<TaskCounts>("/tasks/counts"),
  get: (taskId: string) => api.get<TaskInfo>(`/tasks/${taskId}`),
  delete: (taskId: string) => api.delete<void>(`/tasks/${taskId}`),
  archive: (taskId: string) =>
    api.post<void>(`/tasks/${taskId}/archive`),
  bulkDelete: (taskIds: string[]) =>
    api.post<{ deleted: string[]; missing: string[]; count: number }>("/tasks/bulk-delete", { task_ids: taskIds }),
  bulkArchive: (taskIds: string[]) =>
    api.post<{ archived: string[]; missing: string[]; count: number }>("/tasks/bulk-archive", { task_ids: taskIds }),
  archiveExpired: (params?: { hours?: number; terminal_only?: boolean }) =>
    api.post<{ archived: string[]; count: number; hours: number; terminal_only: boolean }>("/tasks/archive-expired", null, { params }),
};

export const apiArchive = {
  list: (params?: { status?: string; backend?: string; limit?: number; offset?: number }) =>
    api.get<TaskListResponse>("/archive", { params }),
  get: (taskId: string) => api.get<TaskInfo>(`/archive/${taskId}`),
  delete: (taskId: string) => api.delete<void>(`/archive/${taskId}`),
  restore: (taskId: string) =>
    api.post<void>(`/archive/restore/${taskId}`),
};

export const apiCircuits = {
  svgUrl: (taskId: string, format: "source" | "compiled" | "executed" = "source") =>
    `/api/circuits/${taskId}/svg?format=${format}`,
};
