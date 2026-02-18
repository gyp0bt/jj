import { Neo4jEntityRepository } from "./neo4j-entity-repository";
import { Neo4jRelationRepository } from "./neo4j-relation-repository";
import { SqliteEntityRepository } from "./sqlite-entity-repository";
import { SqliteRelationRepository } from "./sqlite-relation-repository";
import type {
  DataSourceType,
  IEntityRepository,
  IRelationRepository,
} from "./types";

let entityRepo: IEntityRepository | null = null;
let relationRepo: IRelationRepository | null = null;

function getDataSourceType(): DataSourceType {
  const ds = process.env.DATA_SOURCE?.toLowerCase();
  if (ds === "neo4j") return "neo4j";
  return "sqlite";
}

export function getEntityRepository(): IEntityRepository {
  if (entityRepo) return entityRepo;

  const dsType = getDataSourceType();
  if (dsType === "neo4j") {
    entityRepo = new Neo4jEntityRepository();
  } else {
    entityRepo = new SqliteEntityRepository();
  }

  return entityRepo;
}

export function getRelationRepository(): IRelationRepository {
  if (relationRepo) return relationRepo;

  const dsType = getDataSourceType();
  if (dsType === "neo4j") {
    relationRepo = new Neo4jRelationRepository();
  } else {
    relationRepo = new SqliteRelationRepository();
  }

  return relationRepo;
}

/** テスト用: シングルトンをリセット */
export function resetRepositories(): void {
  entityRepo = null;
  relationRepo = null;
}
