/**
 * データソース設定 クライアントAPI
 */

const API_BASE = "/api/datasource";
const TOKEN_KEY = "mat-db-auth-token";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem(TOKEN_KEY);
  if (!token) return {};
  return { Authorization: `Bearer ${token}` };
}

export type DataSourceStatus = {
  dataSourceType: "sqlite" | "neo4j";
  neo4j: {
    uri: string;
    user: string;
    connected: boolean;
  };
};

export type TestConnectionResult = {
  ok: boolean;
  error?: string;
  serverInfo?: string;
};

export type SwitchResult = {
  dataSourceType: "sqlite" | "neo4j";
  message: string;
};

/** 現在のデータソース状態を取得 */
export async function getDataSourceStatus(): Promise<{
  data: DataSourceStatus | null;
  error: string | null;
}> {
  try {
    const res = await fetch(API_BASE, {
      headers: getAuthHeaders(),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { data: null, error: body.error || `HTTP ${res.status}` };
    }
    const data = await res.json();
    return { data, error: null };
  } catch (err) {
    return {
      data: null,
      error: err instanceof Error ? err.message : "通信エラー",
    };
  }
}

/** Neo4j接続テスト */
export async function testNeo4jConnection(config: {
  uri: string;
  user: string;
  password: string;
}): Promise<{
  data: TestConnectionResult | null;
  error: string | null;
}> {
  try {
    const res = await fetch(`${API_BASE}/test`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify(config),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { data: null, error: body.error || `HTTP ${res.status}` };
    }
    const data = await res.json();
    return { data, error: null };
  } catch (err) {
    return {
      data: null,
      error: err instanceof Error ? err.message : "通信エラー",
    };
  }
}

/** データソース切替 */
export async function switchDataSource(
  dataSourceType: "sqlite" | "neo4j",
  neo4jConfig?: { uri: string; user: string; password: string },
): Promise<{
  data: SwitchResult | null;
  error: string | null;
}> {
  try {
    const res = await fetch(`${API_BASE}/switch`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        ...getAuthHeaders(),
      },
      body: JSON.stringify({ dataSourceType, neo4jConfig }),
    });
    if (!res.ok) {
      const body = await res.json().catch(() => ({}));
      return { data: null, error: body.error || `HTTP ${res.status}` };
    }
    const data = await res.json();
    return { data, error: null };
  } catch (err) {
    return {
      data: null,
      error: err instanceof Error ? err.message : "通信エラー",
    };
  }
}
