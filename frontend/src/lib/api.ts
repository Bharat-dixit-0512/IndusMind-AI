const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000/api/v1";

function getHeaders(contentType = "application/json"): HeadersInit {
  const token = typeof window !== "undefined" ? localStorage.getItem("token") : null;
  const headers: Record<string, string> = {};
  if (contentType !== "multipart/form-data") headers["Content-Type"] = contentType;
  if (token) headers["Authorization"] = `Bearer ${token}`;
  return headers;
}

async function handleResponse<T>(res: Response): Promise<T> {
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || "API error");
  }
  return res.json() as Promise<T>;
}

// ─── Auth ──────────────────────────────────────────────────────────────────
export interface LoginPayload { email: string; password: string; }
export interface AuthToken { access_token: string; token_type: string; role: string; email: string; name: string; }

export async function loginApi(payload: LoginPayload): Promise<AuthToken> {
  const res = await fetch(`${API_BASE}/auth/login-json`, {
    method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
  });
  return handleResponse<AuthToken>(res);
}

export interface RegisterPayload { email: string; full_name: string; password: string; role?: string; }
export async function registerApi(payload: RegisterPayload): Promise<AuthToken> {
  const res = await fetch(`${API_BASE}/auth/register`, {
    method: "POST", headers: getHeaders(), body: JSON.stringify(payload),
  });
  return handleResponse<AuthToken>(res);
}

// ─── Documents ─────────────────────────────────────────────────────────────
export interface DocumentRecord {
  id: string; filename: string; file_type: string; file_size: number;
  status: "PENDING" | "PROCESSING" | "COMPLETED" | "FAILED";
  error_message?: string; uploaded_by: string; created_at: string;
}

export async function uploadDocument(file: File): Promise<DocumentRecord> {
  const form = new FormData();
  form.append("file", file);
  const res = await fetch(`${API_BASE}/documents/upload`, {
    method: "POST", headers: getHeaders("multipart/form-data"), body: form,
  });
  return handleResponse<DocumentRecord>(res);
}

export async function listDocuments(): Promise<DocumentRecord[]> {
  const res = await fetch(`${API_BASE}/documents/list`, { headers: getHeaders() });
  return handleResponse<DocumentRecord[]>(res);
}

export async function deleteDocument(id: string): Promise<void> {
  await fetch(`${API_BASE}/documents/delete/${id}`, { method: "DELETE", headers: getHeaders() });
}

// ─── Chat ──────────────────────────────────────────────────────────────────
export interface Citation { document_name: string; page_number?: number; text: string; }

export interface AgentLogStep {
  agent_name: string;
  status: string; // "COMPLETED" | "IN_PROGRESS" | "SKIPPED"
  log_message: string;
}

export interface TimelineEvent {
  time: string;
  event: string;
  status: string; // "normal" | "warning" | "ignored" | "failure" | "repair"
  detail: string;
}

export interface ChatResponse {
  response: string;
  citations: Citation[];
  graph_context: unknown[];
  confidence_score: number;
  reasoning_steps: string[];
  evidence_base: string[];
  timeline: TimelineEvent[];
  agent_logs: AgentLogStep[];
}

export async function sendChatMessage(message: string): Promise<ChatResponse> {
  const res = await fetch(`${API_BASE}/chat/`, {
    method: "POST", headers: getHeaders(),
    body: JSON.stringify({ message, history: [] }),
  });
  return handleResponse<ChatResponse>(res);
}

// ─── Graph ─────────────────────────────────────────────────────────────────
export interface GraphNode {
  id: string; type: string;
  data: Record<string, unknown> & { label: string };
}
export interface GraphEdge { id: string; source: string; target: string; label: string; }
export interface GraphData { nodes: GraphNode[]; relationships: GraphEdge[]; }

export async function fetchGraph(): Promise<GraphData> {
  const res = await fetch(`${API_BASE}/graph/`, { headers: getHeaders() });
  return handleResponse<GraphData>(res);
}

// ─── Reports ───────────────────────────────────────────────────────────────
export interface ReportRecord {
  id: string; title: string; report_type: string;
  file_path: string; generated_by: string; created_at: string;
}
export async function generateReport(title: string, report_type: string): Promise<ReportRecord> {
  const res = await fetch(`${API_BASE}/reports/generate`, {
    method: "POST", headers: getHeaders(),
    body: JSON.stringify({ title, report_type }),
  });
  return handleResponse<ReportRecord>(res);
}
export async function listReports(): Promise<ReportRecord[]> {
  const res = await fetch(`${API_BASE}/reports/list`, { headers: getHeaders() });
  return handleResponse<ReportRecord[]>(res);
}
export function getReportDownloadUrl(id: string) {
  return `${API_BASE}/reports/download/${id}`;
}

// ─── Compliance ────────────────────────────────────────────────────────────
export async function runComplianceCheck(query: string): Promise<unknown> {
  const res = await fetch(`${API_BASE}/compliance/check?query=${encodeURIComponent(query)}`, {
    method: "POST", headers: getHeaders(),
  });
  return handleResponse<unknown>(res);
}
