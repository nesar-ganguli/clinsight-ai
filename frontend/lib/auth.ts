import { AuthUser, UserRole } from "@/lib/types";

export const TOKEN_STORAGE_KEY = "clinsight_token";
export const USER_STORAGE_KEY = "clinsight_user";

export function saveSession(token: string, user: AuthUser) {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user));
  document.cookie = `${TOKEN_STORAGE_KEY}=${token}; path=/; max-age=28800; SameSite=Lax`;
}

export function clearSession() {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
  document.cookie = `${TOKEN_STORAGE_KEY}=; path=/; max-age=0; SameSite=Lax`;
}

export function getStoredUser(): AuthUser | null {
  if (typeof window === "undefined") {
    return null;
  }

  const rawUser = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!rawUser) {
    return null;
  }

  try {
    return JSON.parse(rawUser) as AuthUser;
  } catch {
    clearSession();
    return null;
  }
}

export function canUpload(role: UserRole) {
  return role === "admin" || role === "data_reviewer";
}

export function canViewInsights(role: UserRole) {
  return role === "admin" || role === "clinician";
}

export function canViewCareGaps(role: UserRole) {
  return role === "admin" || role === "care_coordinator";
}

export function canViewQuality(role: UserRole) {
  return role === "admin" || role === "data_reviewer";
}

export function canViewSourceMetadata(role: UserRole) {
  return role === "admin" || role === "data_reviewer";
}
