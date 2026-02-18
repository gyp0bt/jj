import { getDb } from "../db";
import type { EntityType, Relation, StringEntity } from "../types";
import type {
  IRelationRepository,
  RelatedEntityWithDepth,
  RelationGraphResult,
} from "./types";

type EntityRow = {
  id: string;
  name: string;
  body: string;
  entity_type: string | null;
  sys_tags: string;
  user_tags: string;
  sys_props: string;
  user_props: string;
  remark: string | null;
  domain: string | null;
  domain_source: string | null;
  domain_confidence: number | null;
  created_by: string | null;
  created_at: string;
  updated_at: string;
};

type RelationRow = {
  id: string;
  label: string;
  entity1_id: string;
  entity2_id: string;
  created_at: string;
};

function rowToEntity(row: EntityRow): StringEntity {
  return {
    id: row.id,
    name: row.name,
    body: row.body,
    entityType: row.entity_type as EntityType,
    sysTags: JSON.parse(row.sys_tags),
    userTags: JSON.parse(row.user_tags),
    sysProps: JSON.parse(row.sys_props),
    userProps: JSON.parse(row.user_props),
    remark: row.remark,
    domain: row.domain,
    domainSource: row.domain_source as StringEntity["domainSource"],
    domainConfidence: row.domain_confidence,
    createdBy: row.created_by,
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function rowToRelation(row: RelationRow): Relation {
  return {
    id: row.id,
    label: row.label,
    entity1Id: row.entity1_id,
    entity2Id: row.entity2_id,
    createdAt: row.created_at,
  };
}

export class SqliteRelationRepository implements IRelationRepository {
  async getAllRelations(): Promise<Relation[]> {
    const db = await getDb();
    const rows = await db.all<RelationRow>(
      "SELECT * FROM relations ORDER BY created_at DESC",
    );
    return rows.map(rowToRelation);
  }

  async getRelationsByEntityIds(entityIds: string[]): Promise<Relation[]> {
    if (entityIds.length === 0) return [];
    const db = await getDb();
    const placeholders = entityIds.map(() => "?").join(",");
    const rows = await db.all<RelationRow>(
      `SELECT * FROM relations
			 WHERE entity1_id IN (${placeholders}) AND entity2_id IN (${placeholders})
			 ORDER BY created_at DESC`,
      ...entityIds,
      ...entityIds,
    );
    return rows.map(rowToRelation);
  }

  async getRelationsByEntityId(entityId: string): Promise<Relation[]> {
    const db = await getDb();
    const rows = await db.all<RelationRow>(
      `SELECT * FROM relations
			 WHERE entity1_id = ? OR entity2_id = ?
			 ORDER BY created_at DESC`,
      entityId,
      entityId,
    );
    return rows.map(rowToRelation);
  }

  async getRelationsByLabel(label: string): Promise<Relation[]> {
    const db = await getDb();
    const rows = await db.all<RelationRow>(
      "SELECT * FROM relations WHERE label = ? ORDER BY created_at DESC",
      label,
    );
    return rows.map(rowToRelation);
  }

  async getRelatedEntities(
    entityId: string,
    label?: string,
  ): Promise<StringEntity[]> {
    const db = await getDb();
    let sql: string;
    let params: string[];

    if (label) {
      sql = `
				SELECT e.* FROM entities e
				JOIN relations r ON (r.entity1_id = e.id OR r.entity2_id = e.id)
				WHERE (r.entity1_id = ? OR r.entity2_id = ?)
					AND r.label = ?
					AND e.id != ?
				ORDER BY e.updated_at DESC
			`;
      params = [entityId, entityId, label, entityId];
    } else {
      sql = `
				SELECT e.* FROM entities e
				JOIN relations r ON (r.entity1_id = e.id OR r.entity2_id = e.id)
				WHERE (r.entity1_id = ? OR r.entity2_id = ?)
					AND e.id != ?
				ORDER BY e.updated_at DESC
			`;
      params = [entityId, entityId, entityId];
    }

    const rows = await db.all<EntityRow>(sql, ...params);
    return rows.map(rowToEntity);
  }

  async getRelatedEntitiesGrouped(
    entityId: string,
  ): Promise<Record<string, StringEntity[]>> {
    const db = await getDb();
    const relations = await this.getRelationsByEntityId(entityId);
    const result: Record<string, StringEntity[]> = {};

    for (const relation of relations) {
      const relatedId =
        relation.entity1Id === entityId
          ? relation.entity2Id
          : relation.entity1Id;
      const row = await db.get<EntityRow>(
        "SELECT * FROM entities WHERE id = ?",
        relatedId,
      );
      if (row) {
        const entity = rowToEntity(row);
        if (!result[relation.label]) {
          result[relation.label] = [];
        }
        result[relation.label].push(entity);
      }
    }

    return result;
  }

  async createRelation(relation: Relation): Promise<Relation> {
    const db = await getDb();
    await db.run(
      `INSERT INTO relations (id, label, entity1_id, entity2_id, created_at)
			 VALUES (@id, @label, @entity1_id, @entity2_id, @created_at)`,
      {
        id: relation.id,
        label: relation.label,
        entity1_id: relation.entity1Id,
        entity2_id: relation.entity2Id,
        created_at: relation.createdAt,
      },
    );
    return relation;
  }

  async deleteRelation(id: string): Promise<boolean> {
    const db = await getDb();
    const result = await db.run("DELETE FROM relations WHERE id = ?", id);
    return result.changes > 0;
  }

  async deleteRelationsBetween(
    entity1Id: string,
    entity2Id: string,
  ): Promise<number> {
    const db = await getDb();
    const result = await db.run(
      `DELETE FROM relations
			 WHERE (entity1_id = ? AND entity2_id = ?)
					OR (entity1_id = ? AND entity2_id = ?)`,
      entity1Id,
      entity2Id,
      entity2Id,
      entity1Id,
    );
    return result.changes ?? 0;
  }

  async getRelationGraph(
    entityId: string,
    maxDepth = 2,
  ): Promise<RelationGraphResult | null> {
    const db = await getDb();
    const centerRow = await db.get<EntityRow>(
      "SELECT * FROM entities WHERE id = ?",
      entityId,
    );
    if (!centerRow) return null;

    const center = rowToEntity(centerRow);
    const visited = new Set<string>([entityId]);
    const nodes: RelatedEntityWithDepth[] = [];
    const edges: RelationGraphResult["edges"] = [];
    const queue: Array<{ id: string; depth: number }> = [
      { id: entityId, depth: 0 },
    ];

    while (queue.length > 0) {
      const current = queue.shift();
      if (!current || current.depth >= maxDepth) continue;

      const relations = await db.all<RelationRow>(
        "SELECT * FROM relations WHERE entity1_id = ? OR entity2_id = ?",
        current.id,
        current.id,
      );

      for (const rel of relations) {
        const relatedId =
          rel.entity1_id === current.id ? rel.entity2_id : rel.entity1_id;

        edges.push({
          from: current.id,
          to: relatedId,
          label: rel.label,
          depth: current.depth + 1,
        });

        if (!visited.has(relatedId)) {
          visited.add(relatedId);
          const relatedRow = await db.get<EntityRow>(
            "SELECT * FROM entities WHERE id = ?",
            relatedId,
          );
          if (relatedRow) {
            nodes.push({
              entity: rowToEntity(relatedRow),
              depth: current.depth + 1,
              relationLabel: rel.label,
              parentId: current.id,
            });
            queue.push({ id: relatedId, depth: current.depth + 1 });
          }
        }
      }
    }

    return { center, nodes, edges };
  }
}
