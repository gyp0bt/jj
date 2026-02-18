/**
 * entity-repository.ts — ファサード（後方互換レイヤー）
 *
 * 既存のAPIルートが変更なしで動作するよう、
 * datasource/factory 経由でバックエンド実装に委譲する。
 *
 * 新規コードは datasource/ のインターフェースを直接使うことを推奨。
 */
import {
  getEntityRepository,
  getRelationRepository,
} from "./datasource/factory";
import type { Relation, StringEntity } from "./types";

// === 型の再エクスポート（relation-api.ts が参照） ===
export type {
  RelatedEntityWithDepth,
  RelationGraphResult,
} from "./datasource/types";

// ========== Entity CRUD ==========

export async function getAllEntities(): Promise<StringEntity[]> {
  return getEntityRepository().getAllEntities();
}

export async function getEntitiesByUser(
  userId: string,
): Promise<StringEntity[]> {
  return getEntityRepository().getEntitiesByUser(userId);
}

export async function getEntityById(id: string): Promise<StringEntity | null> {
  return getEntityRepository().getEntityById(id);
}

export async function getEntityByIdForUser(
  id: string,
  userId: string,
): Promise<StringEntity | null> {
  return getEntityRepository().getEntityByIdForUser(id, userId);
}

export async function createEntity(
  entity: StringEntity,
): Promise<StringEntity> {
  return getEntityRepository().createEntity(entity);
}

export async function updateEntity(
  entity: StringEntity,
): Promise<StringEntity> {
  return getEntityRepository().updateEntity(entity);
}

export async function upsertEntity(
  entity: StringEntity,
): Promise<StringEntity> {
  return getEntityRepository().upsertEntity(entity);
}

export async function deleteEntity(id: string): Promise<boolean> {
  return getEntityRepository().deleteEntity(id);
}

export async function deleteEntityForUser(
  id: string,
  userId: string,
): Promise<boolean> {
  return getEntityRepository().deleteEntityForUser(id, userId);
}

export async function searchEntities(query: string): Promise<StringEntity[]> {
  return getEntityRepository().searchEntities(query);
}

export async function searchEntitiesByUser(
  query: string,
  userId: string,
): Promise<StringEntity[]> {
  return getEntityRepository().searchEntitiesByUser(query, userId);
}

export async function getEntityCount(): Promise<number> {
  return getEntityRepository().getEntityCount();
}

export async function getEntityCountByUser(userId: string): Promise<number> {
  return getEntityRepository().getEntityCountByUser(userId);
}

// ========== Relation CRUD ==========

export async function getAllRelations(): Promise<Relation[]> {
  return getRelationRepository().getAllRelations();
}

export async function getRelationsByEntityIds(
  entityIds: string[],
): Promise<Relation[]> {
  return getRelationRepository().getRelationsByEntityIds(entityIds);
}

export async function getRelationsByEntityId(
  entityId: string,
): Promise<Relation[]> {
  return getRelationRepository().getRelationsByEntityId(entityId);
}

export async function getRelationsByLabel(label: string): Promise<Relation[]> {
  return getRelationRepository().getRelationsByLabel(label);
}

export async function getRelatedEntities(
  entityId: string,
  label?: string,
): Promise<StringEntity[]> {
  return getRelationRepository().getRelatedEntities(entityId, label);
}

export async function getRelatedEntitiesGrouped(
  entityId: string,
): Promise<Record<string, StringEntity[]>> {
  return getRelationRepository().getRelatedEntitiesGrouped(entityId);
}

export async function createRelation(relation: Relation): Promise<Relation> {
  return getRelationRepository().createRelation(relation);
}

export async function deleteRelation(id: string): Promise<boolean> {
  return getRelationRepository().deleteRelation(id);
}

export async function deleteRelationsBetween(
  entity1Id: string,
  entity2Id: string,
): Promise<number> {
  return getRelationRepository().deleteRelationsBetween(entity1Id, entity2Id);
}

// ========== N親等 関係取得 ==========

export async function getRelationGraph(entityId: string, maxDepth = 2) {
  return getRelationRepository().getRelationGraph(entityId, maxDepth);
}
