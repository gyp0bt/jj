import type { Relation, StringEntity } from "../types";

/**
 * エンティティリポジトリ抽象インターフェース
 * SQLite / Neo4j 両バックエンドで実装する
 */
export interface IEntityRepository {
  // === Entity CRUD ===
  getAllEntities(): Promise<StringEntity[]>;
  getEntitiesByUser(userId: string): Promise<StringEntity[]>;
  getEntityById(id: string): Promise<StringEntity | null>;
  getEntityByIdForUser(
    id: string,
    userId: string,
  ): Promise<StringEntity | null>;
  createEntity(entity: StringEntity): Promise<StringEntity>;
  updateEntity(entity: StringEntity): Promise<StringEntity>;
  upsertEntity(entity: StringEntity): Promise<StringEntity>;
  deleteEntity(id: string): Promise<boolean>;
  deleteEntityForUser(id: string, userId: string): Promise<boolean>;

  // === Search ===
  searchEntities(query: string): Promise<StringEntity[]>;
  searchEntitiesByUser(query: string, userId: string): Promise<StringEntity[]>;
  getEntityCount(): Promise<number>;
  getEntityCountByUser(userId: string): Promise<number>;
}

/**
 * リレーションリポジトリ抽象インターフェース
 */
export interface IRelationRepository {
  getAllRelations(): Promise<Relation[]>;
  getRelationsByEntityIds(entityIds: string[]): Promise<Relation[]>;
  getRelationsByEntityId(entityId: string): Promise<Relation[]>;
  getRelationsByLabel(label: string): Promise<Relation[]>;
  getRelatedEntities(entityId: string, label?: string): Promise<StringEntity[]>;
  getRelatedEntitiesGrouped(
    entityId: string,
  ): Promise<Record<string, StringEntity[]>>;
  createRelation(relation: Relation): Promise<Relation>;
  deleteRelation(id: string): Promise<boolean>;
  deleteRelationsBetween(entity1Id: string, entity2Id: string): Promise<number>;
  getRelationGraph(
    entityId: string,
    maxDepth?: number,
  ): Promise<RelationGraphResult | null>;
}

/**
 * N親等探索のノード情報
 */
export type RelatedEntityWithDepth = {
  entity: StringEntity;
  depth: number;
  relationLabel: string;
  parentId: string;
};

/**
 * N親等グラフ探索結果
 */
export type RelationGraphResult = {
  center: StringEntity;
  nodes: RelatedEntityWithDepth[];
  edges: Array<{
    from: string;
    to: string;
    label: string;
    depth: number;
  }>;
};

/**
 * データソース種別
 */
export type DataSourceType = "sqlite" | "neo4j";
