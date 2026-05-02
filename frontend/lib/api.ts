import {
  AuthUser,
  DemoUsersResponse,
  LoginResponse,
  Patient,
  PatientAiInsightsResponse,
  PatientListResponse,
  QualityAlertsResponse,
  UploadResponse,
} from "@/lib/types";

const API_BASE_URL =
  typeof window === "undefined"
    ? process.env.INTERNAL_API_BASE_URL ?? process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000"
    : process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8000";

type RequestOptions = RequestInit & {
  token?: string | null;
};

function getBrowserToken() {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage.getItem("clinsight_token");
}

async function request<T>(path: string, init?: RequestOptions): Promise<T> {
  const token = init?.token ?? getBrowserToken();
  const headers = new Headers(init?.headers);
  if (token) {
    headers.set("Authorization", `Bearer ${token}`);
  }

  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
    headers,
    cache: "no-store",
  });

  if (!response.ok) {
    let detail = "Request failed";
    try {
      const payload = await response.json();
      detail = payload.detail ?? detail;
    } catch {
      detail = response.statusText || detail;
    }
    throw new Error(detail);
  }

  return response.json() as Promise<T>;
}

export function login(username: string, password: string) {
  return request<LoginResponse>("/api/auth/login", {
    method: "POST",
    headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username, password}),
  });
}

export function getCurrentUser(token?: string | null) {
  return request<AuthUser>("/api/auth/me", {token});
}

export function listPatients(search?: string, token?: string | null) {
  const params = new URLSearchParams();
  if (search) {
    params.set("search", search);
  }
  params.set("limit", "20");
  params.set("offset", "0");
  return request<PatientListResponse>(`/api/patients?${params.toString()}`, {token});
}

export function getPatient(patientId: number | string, token?: string | null) {
  return request<Patient>(`/api/patients/${patientId}`, {token});
}

export function getQualityAlerts(patientId: number | string, token?: string | null) {
  return request<QualityAlertsResponse>(`/api/patients/${patientId}/quality-alerts`, {token});
}

export function getPatientAiInsights(patientId: number | string, token?: string | null) {
  return request<PatientAiInsightsResponse>(`/api/patients/${patientId}/ai-insights`, {token});
}

export function getDemoUsers() {
  return request<DemoUsersResponse>("/api/demo-users");
}

export async function uploadBundle(file: File) {
  const formData = new FormData();
  formData.append("file", file);

  return request<UploadResponse>("/api/upload", {
    method: "POST",
    body: formData,
  });
}
