import type { SearchHistory } from "./types";

const API_BASE = "/api/search-history";
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

export async function createSearchHistory(input: {
  query: string;
  filters: Record<string, unknown>;
  resultCount: number;
}): Promise<ApiResponse<SearchHistory>> {
  try {
    const res = await fetch(API_BASE, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(input),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "登録に失敗しました" };
    }
    const json = await res.json();
    return { data: json.history, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchSearchHistory(
  limit = 20,
): Promise<ApiResponse<SearchHistory[]>> {
  try {
    const res = await fetch(`${API_BASE}?limit=${limit}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.history, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}
