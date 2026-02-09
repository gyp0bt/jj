import type { EntityStats } from "./types";

const API_BASE = "/api/entities";
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

export async function fetchEntityStats(
  entityIds: string[],
): Promise<ApiResponse<EntityStats[]>> {
  if (entityIds.length === 0) {
    return { data: [], error: null };
  }
  try {
    const res = await fetch(
      `${API_BASE}/stats?ids=${encodeURIComponent(entityIds.join(","))}`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.stats, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchFavoriteUsers(
  entityIds: string[],
): Promise<
  ApiResponse<
    Record<string, { id: string; username: string; displayName: string }[]>
  >
> {
  if (entityIds.length === 0) {
    return { data: {}, error: null };
  }
  try {
    const res = await fetch(
      `${API_BASE}/favorite-users?ids=${encodeURIComponent(entityIds.join(","))}`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.usersByEntity ?? {}, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchFavoriteStates(
  entityIds: string[],
): Promise<ApiResponse<string[]>> {
  if (entityIds.length === 0) {
    return { data: [], error: null };
  }
  try {
    const res = await fetch(
      `${API_BASE}/favorite-states?ids=${encodeURIComponent(entityIds.join(","))}`,
      { headers: getAuthHeaders() },
    );
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.favoriteIds ?? [], error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchEntityStatsById(
  entityId: string,
): Promise<ApiResponse<EntityStats>> {
  try {
    const res = await fetch(`${API_BASE}/${entityId}/stats`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.stats, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function toggleEntityFavorite(
  entityId: string,
): Promise<ApiResponse<{ favorite: boolean; stats: EntityStats }>> {
  try {
    const res = await fetch(`${API_BASE}/${entityId}/favorite`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "更新に失敗しました" };
    }
    const json = await res.json();
    return {
      data: { favorite: json.favorite, stats: json.stats },
      error: null,
    };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function fetchFavoriteState(
  entityId: string,
): Promise<ApiResponse<{ favorite: boolean; stats: EntityStats }>> {
  try {
    const res = await fetch(`${API_BASE}/${entityId}/favorite`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return {
      data: { favorite: json.favorite, stats: json.stats },
      error: null,
    };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

export async function recordEntityDownload(
  entityId: string,
): Promise<ApiResponse<EntityStats>> {
  try {
    const res = await fetch(`${API_BASE}/${entityId}/download`, {
      method: "POST",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "更新に失敗しました" };
    }
    const json = await res.json();
    return { data: json.stats, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}
