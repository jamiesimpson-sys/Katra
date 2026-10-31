export class ApiError extends Error {
  constructor(
    public status: number,
    message: string,
  ) {
    super(message);
  }
}

function csrfToken(): string {
  const match = document.cookie.match(/(?:^|;\s*)katra_csrf=([^;]+)/);
  return match ? decodeURIComponent(match[1]) : "";
}

export async function api<T>(path: string, init: { method?: string; body?: unknown } = {}): Promise<T> {
  const method = init.method ?? "GET";
  const headers: Record<string, string> = {};
  if (init.body !== undefined) headers["Content-Type"] = "application/json";
  if (method !== "GET") headers["X-CSRF-Token"] = csrfToken();

  const res = await fetch(path, {
    method,
    headers,
    credentials: "same-origin",
    body: init.body === undefined ? undefined : JSON.stringify(init.body),
  });
  if (res.status === 204) return undefined as T;
  const data = await res.json().catch(() => ({}));
  if (!res.ok) {
    const detail = typeof data.detail === "string" ? data.detail : "Something went wrong";
    throw new ApiError(res.status, detail);
  }
  return data as T;
}

export type Role = "admin" | "owner" | "viewer";

export interface User {
  id: string;
  email: string;
  display_name: string;
  is_staff: boolean;
}

export interface Me {
  user: User;
  csrf_token: string;
}

export interface Project {
  id: string;
  name: string;
  module_id: string;
  module_version: number;
  status: string;
  retention_days: number | null;
  created_at: string;
  role: Role;
}

export interface Member {
  user: User;
  role: Role;
  created_at: string;
}

export interface Invite {
  id: string;
  email: string;
  role: Role;
  expires_at: string;
  accepted_at: string | null;
  revoked_at: string | null;
  created_at: string;
  invite_url?: string;
}

export interface InvitePreview {
  project_name: string;
  email: string;
  role: Role;
  user_exists: boolean;
}

export interface AuditEntry {
  id: string;
  user_id: string | null;
  action: string;
  target_type: string | null;
  target_id: string | null;
  details: Record<string, unknown>;
  ip: string | null;
  created_at: string;
}
