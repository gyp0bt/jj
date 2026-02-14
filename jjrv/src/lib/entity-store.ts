import { MOCK_ENTITIES } from "./mock-data";
import type { StringEntity } from "./types";

export const ENTITY_STORAGE_KEY = "mat-db.entities";

function readStoredEntities(): StringEntity[] | null {
  if (typeof window === "undefined") return null;
  const raw = window.localStorage.getItem(ENTITY_STORAGE_KEY);
  if (!raw) return null;
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? (parsed as StringEntity[]) : null;
  } catch {
    return null;
  }
}

export function loadEntities(): StringEntity[] {
  const stored = readStoredEntities();
  if (stored) return stored;
  return [...MOCK_ENTITIES];
}

export function saveEntities(entities: StringEntity[]): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(ENTITY_STORAGE_KEY, JSON.stringify(entities));
}

export function upsertEntity(entity: StringEntity): StringEntity[] {
  const base = loadEntities();
  const index = base.findIndex((e) => e.id === entity.id);
  const next =
    index >= 0
      ? base.map((e, i) => (i === index ? entity : e))
      : [entity, ...base];
  saveEntities(next);
  return next;
}

export function findEntityById(
  entities: StringEntity[],
  id: string | null,
): StringEntity | undefined {
  if (!id) return undefined;
  return entities.find((e) => e.id === id);
}
