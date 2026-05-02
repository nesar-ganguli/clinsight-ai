import {
  DemoUsersResponse,
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

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...init,
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

export function listPatients(search?: string) {
  const params = new URLSearchParams();
  if (search) {
    params.set("search", search);
  }
  params.set("limit", "20");
  params.set("offset", "0");
  return request<PatientListResponse>(`/api/patients?${params.toString()}`);
}

export function getPatient(patientId: number | string) {
  return request<Patient>(`/api/patients/${patientId}`);
}

export function getQualityAlerts(patientId: number | string) {
  return request<QualityAlertsResponse>(`/api/patients/${patientId}/quality-alerts`);
}

export function getPatientAiInsights(patientId: number | string) {
  return request<PatientAiInsightsResponse>(`/api/patients/${patientId}/ai-insights`);
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
