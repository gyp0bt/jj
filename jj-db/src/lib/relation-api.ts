import type { RelationGraphResult } from "./entity-repository";
import type { Relation, StringEntity } from "./types";

const TOKEN_KEY = "mat-db-auth-token";

function getAuthHeaders(): HeadersInit {
  if (typeof window === "undefined") return {};
  const token = localStorage.getItem(TOKEN_KEY);
  return token ? { Authorization: `Bearer ${token}` } : {};
}

type ApiResult<T> =
  | { data: T; error?: never }
  | { data?: never; error: string };

export async function fetchRelationsByEntityId(
  entityId: string,
): Promise<ApiResult<Relation[]>> {
  const res = await fetch(`/api/entities/${entityId}/relations`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return { error: `Failed to fetch relations: ${res.status}` };
  }
  const json = await res.json();
  return { data: json.data };
}

export async function fetchRelationsByEntityIds(
  entityIds: string[],
): Promise<ApiResult<Relation[]>> {
  if (entityIds.length === 0) return { data: [] };
  const res = await fetch(`/api/relations?entityIds=${entityIds.join(",")}`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return { error: `Failed to fetch relations: ${res.status}` };
  }
  const json = await res.json();
  return { data: json.data };
}

export async function fetchRelatedEntitiesGrouped(
  entityId: string,
): Promise<ApiResult<Record<string, StringEntity[]>>> {
  const res = await fetch(`/api/entities/${entityId}/relations?grouped=true`, {
    headers: getAuthHeaders(),
  });
  if (!res.ok) {
    return { error: `Failed to fetch related entities: ${res.status}` };
  }
  const json = await res.json();
  return { data: json.data };
}

export async function createRelation(params: {
  label: string;
  entity1Id: string;
  entity2Id: string;
}): Promise<ApiResult<Relation>> {
  const res = await fetch("/api/relations", {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      ...getAuthHeaders(),
    },
    body: JSON.stringify(params),
  });
  if (!res.ok) {
    return { error: `Failed to create relation: ${res.status}` };
  }
  const json = await res.json();
  return { data: json.data };
}

export async function fetchRelationGraph(
  entityId: string,
  maxDepth = 2,
): Promise<ApiResult<RelationGraphResult>> {
  const res = await fetch(
    `/api/entities/${entityId}/relations?graph=true&maxDepth=${maxDepth}`,
    { headers: getAuthHeaders() },
  );
  if (!res.ok) {
    return { error: `Failed to fetch relation graph: ${res.status}` };
  }
  const json = await res.json();
  return { data: json.data };
}
