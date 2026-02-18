import { getDb } from "../db";
import type { EntityType, StringEntity } from "../types";
import type { IEntityRepository } from "./types";

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

function entityToRow(entity: StringEntity): EntityRow {
  return {
    id: entity.id,
    name: entity.name,
    body: entity.body,
    entity_type: entity.entityType ?? null,
    sys_tags: JSON.stringify(entity.sysTags),
    user_tags: JSON.stringify(entity.userTags),
    sys_props: JSON.stringify(entity.sysProps),
    user_props: JSON.stringify(entity.userProps),
    remark: entity.remark ?? null,
    domain: entity.domain ?? null,
    domain_source: entity.domainSource ?? null,
    domain_confidence: entity.domainConfidence ?? null,
    created_by: entity.createdBy ?? null,
    created_at: entity.createdAt,
    updated_at: entity.updatedAt,
  };
}

export class SqliteEntityRepository implements IEntityRepository {
  async getAllEntities(): Promise<StringEntity[]> {
    const db = await getDb();
    const rows = await db.all<EntityRow>(
      "SELECT * FROM entities ORDER BY updated_at DESC",
    );
    return rows.map(rowToEntity);
  }

  async getEntitiesByUser(userId: string): Promise<StringEntity[]> {
    const db = await getDb();
    const rows = await db.all<EntityRow>(
      "SELECT * FROM entities WHERE created_by = ? ORDER BY updated_at DESC",
      userId,
    );
    return rows.map(rowToEntity);
  }

  async getEntityById(id: string): Promise<StringEntity | null> {
    const db = await getDb();
    const row = await db.get<EntityRow>(
      "SELECT * FROM entities WHERE id = ?",
      id,
    );
    return row ? rowToEntity(row) : null;
  }

  async getEntityByIdForUser(
    id: string,
    userId: string,
  ): Promise<StringEntity | null> {
    const db = await getDb();
    const row = await db.get<EntityRow>(
      "SELECT * FROM entities WHERE id = ? AND created_by = ?",
      id,
      userId,
    );
    return row ? rowToEntity(row) : null;
  }

  async createEntity(entity: StringEntity): Promise<StringEntity> {
    const db = await getDb();
    const row = entityToRow(entity);
    await db.run(
      `
			INSERT INTO entities (
				id, name, body, entity_type, sys_tags, user_tags, sys_props, user_props,
				remark, domain, domain_source, domain_confidence, created_by, created_at, updated_at
			) VALUES (
				@id, @name, @body, @entity_type, @sys_tags, @user_tags, @sys_props, @user_props,
				@remark, @domain, @domain_source, @domain_confidence, @created_by, @created_at, @updated_at
			)
		`,
      row,
    );
    return entity;
  }

  async updateEntity(entity: StringEntity): Promise<StringEntity> {
    const db = await getDb();
    const row = entityToRow(entity);
    await db.run(
      `
			UPDATE entities SET
				name = @name,
				body = @body,
				entity_type = @entity_type,
				sys_tags = @sys_tags,
				user_tags = @user_tags,
				sys_props = @sys_props,
				user_props = @user_props,
				remark = @remark,
				domain = @domain,
				domain_source = @domain_source,
				domain_confidence = @domain_confidence,
				created_by = @created_by,
				updated_at = @updated_at
			WHERE id = @id
		`,
      row,
    );
    return entity;
  }

  async upsertEntity(entity: StringEntity): Promise<StringEntity> {
    const existing = await this.getEntityById(entity.id);
    if (existing) {
      return this.updateEntity(entity);
    }
    return this.createEntity(entity);
  }

  async deleteEntity(id: string): Promise<boolean> {
    const db = await getDb();
    const result = await db.run("DELETE FROM entities WHERE id = ?", id);
    return result.changes > 0;
  }

  async deleteEntityForUser(id: string, userId: string): Promise<boolean> {
    const db = await getDb();
    const result = await db.run(
      "DELETE FROM entities WHERE id = ? AND created_by = ?",
      id,
      userId,
    );
    return result.changes > 0;
  }

  async searchEntities(query: string): Promise<StringEntity[]> {
    const db = await getDb();
    const pattern = `%${query}%`;
    const rows = await db.all<EntityRow>(
      `
			SELECT * FROM entities
			WHERE name LIKE ? OR body LIKE ? OR user_tags LIKE ?
			ORDER BY updated_at DESC
		`,
      pattern,
      pattern,
      pattern,
    );
    return rows.map(rowToEntity);
  }

  async searchEntitiesByUser(
    query: string,
    userId: string,
  ): Promise<StringEntity[]> {
    const db = await getDb();
    const pattern = `%${query}%`;
    const rows = await db.all<EntityRow>(
      `
			SELECT * FROM entities
			WHERE created_by = ?
				AND (name LIKE ? OR body LIKE ? OR user_tags LIKE ?)
			ORDER BY updated_at DESC
		`,
      userId,
      pattern,
      pattern,
      pattern,
    );
    return rows.map(rowToEntity);
  }

  async getEntityCount(): Promise<number> {
    const db = await getDb();
    const result = await db.get<{ count: number }>(
      "SELECT COUNT(*) as count FROM entities",
    );
    return result?.count ?? 0;
  }

  async getEntityCountByUser(userId: string): Promise<number> {
    const db = await getDb();
    const result = await db.get<{ count: number }>(
      "SELECT COUNT(*) as count FROM entities WHERE created_by = ?",
      userId,
    );
    return result?.count ?? 0;
  }
}
