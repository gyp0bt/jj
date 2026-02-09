import type { User } from "./types";

const API_BASE = "/api/users";
const TOKEN_KEY = "mat-db-auth-token";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") {
    return {};
  }
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) {
    return {};
  }
  return { Authorization: `Bearer ${token}` };
}

export type ApiResponse<T> = {
  data: T | null;
  error: string | null;
};

export async function fetchUsersByIds(
  ids: string[],
): Promise<ApiResponse<Pick<User, "id" | "username" | "displayName">[]>> {
  if (ids.length === 0) {
    return { data: [], error: null };
  }
  try {
    const res = await fetch(
      `${API_BASE}/resolve?ids=${encodeURIComponent(ids.join(","))}`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.users ?? [], error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchUsers(): Promise<
  ApiResponse<Pick<User, "id" | "username" | "displayName" | "role">[]>
> {
  try {
    const res = await fetch(`${API_BASE}`, { headers: getAuthHeaders() });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.users ?? [], error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function updateProfile(updates: {
  displayName?: string;
  avatar?: string | null;
}): Promise<ApiResponse<User>> {
  try {
    const res = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(updates),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "更新に失敗しました" };
    }
    const json = await res.json();
    return { data: json.user, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function changePassword(
  currentPassword: string,
  newPassword: string,
): Promise<ApiResponse<{ message: string }>> {
  try {
    const res = await fetch("/api/auth/me", {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ currentPassword, newPassword }),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "更新に失敗しました" };
    }
    const json = await res.json();
    return { data: { message: json.message }, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}
