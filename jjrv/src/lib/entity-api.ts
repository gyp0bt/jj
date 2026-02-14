import type { StringEntity } from "./types";

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

// 全エンティティ取得
export async function fetchEntities(): Promise<ApiResponse<StringEntity[]>> {
  try {
    const res = await fetch(API_BASE, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.entities, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 検索
export async function searchEntities(
  query: string,
): Promise<ApiResponse<StringEntity[]>> {
  try {
    const res = await fetch(`${API_BASE}?q=${encodeURIComponent(query)}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "検索に失敗しました" };
    }
    const json = await res.json();
    return { data: json.entities, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 単体取得
export async function fetchEntityById(
  id: string,
): Promise<ApiResponse<StringEntity>> {
  try {
    const res = await fetch(`${API_BASE}/${id}`, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    return { data: json.entity, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 作成
export async function createEntity(
  entity: StringEntity,
): Promise<ApiResponse<StringEntity>> {
  try {
    const res = await fetch(API_BASE, {
      method: "POST",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(entity),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "作成に失敗しました" };
    }
    const json = await res.json();
    return { data: json.entity, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 更新
export async function updateEntity(
  entity: StringEntity,
): Promise<ApiResponse<StringEntity>> {
  try {
    const res = await fetch(`${API_BASE}/${entity.id}`, {
      method: "PUT",
      headers: { "Content-Type": "application/json", ...getAuthHeaders() },
      body: JSON.stringify(entity),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "更新に失敗しました" };
    }
    const json = await res.json();
    return { data: json.entity, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 削除
export async function deleteEntity(id: string): Promise<ApiResponse<boolean>> {
  try {
    const res = await fetch(`${API_BASE}/${id}`, {
      method: "DELETE",
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "削除に失敗しました" };
    }
    return { data: true, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// レポジトリ一覧取得（sysTags に "repository" を含むエンティティ）
export async function fetchRepositories(): Promise<
  ApiResponse<StringEntity[]>
> {
  try {
    const res = await fetch(API_BASE, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    const repos = (json.entities as StringEntity[]).filter((e) =>
      e.sysTags.includes("repository"),
    );
    return { data: repos, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// レポジトリ＋ユーザー名前空間の一覧取得（インポート先選択用）
export async function fetchRepositoriesAndNamespaces(): Promise<
  ApiResponse<StringEntity[]>
> {
  try {
    const res = await fetch(API_BASE, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const err = await res.json();
      return { data: null, error: err.error || "取得に失敗しました" };
    }
    const json = await res.json();
    const items = (json.entities as StringEntity[]).filter(
      (e) =>
        e.sysTags.includes("repository") ||
        e.sysTags.includes("user_namespace"),
    );
    return { data: items, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// 現在のユーザーの名前空間を取得
export async function fetchMyNamespace(): Promise<
  ApiResponse<StringEntity | null>
> {
  try {
    // まずログインユーザー情報を取得
    const meRes = await fetch("/api/auth/me", {
      headers: getAuthHeaders(),
    });
    if (!meRes.ok) return { data: null, error: null };
    const meJson = await meRes.json();
    const username = meJson.user?.username;
    if (!username) return { data: null, error: null };

    // user:username のIDで名前空間エンティティを取得
    const nsId = `user:${username}`;
    const nsRes = await fetch(`${API_BASE}/${encodeURIComponent(nsId)}`, {
      headers: getAuthHeaders(),
    });
    if (!nsRes.ok) return { data: null, error: null };
    const nsJson = await nsRes.json();
    return { data: nsJson.entity ?? null, error: null };
  } catch (e) {
    return { data: null, error: String(e) };
  }
}

// upsert（作成または更新）
export async function upsertEntity(
  entity: StringEntity,
): Promise<ApiResponse<StringEntity>> {
  // まず存在確認してから作成または更新
  const existing = await fetchEntityById(entity.id);
  if (existing.data) {
    return updateEntity(entity);
  }
  return createEntity(entity);
}
