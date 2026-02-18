import type { StringEntity } from "../types";
import { getSession } from "./neo4j-driver";
import type { IEntityRepository } from "./types";

/**
 * Neo4jノードのレコード → StringEntity への変換
 *
 * jj export で格納されたノードプロパティを jjrv の StringEntity にマップする。
 * - jj_id → id (string化)
 * - type → sysTags に格納
 * - format → sysProps.format
 * - name → name
 * - その他プロパティ → sysProps
 */
function recordToEntity(record: Record<string, unknown>): StringEntity {
  const jjId = record.jj_id as number | string;
  const project = (record.project as string) || "";
  const name = (record.name as string) || "";
  const nodeType = (record.type as string) || "";
  const format = (record.format as string) || "";

  // jj由来のプロパティを sysProps に格納
  const sysProps: Record<string, string> = {};
  const skipKeys = new Set(["jj_id", "name", "type", "format", "project"]);

  for (const [key, value] of Object.entries(record)) {
    if (skipKeys.has(key) || value == null) continue;
    sysProps[key] = typeof value === "string" ? value : JSON.stringify(value);
  }

  if (format) {
    sysProps.format = format;
  }
  if (project) {
    sysProps.project = project;
  }

  // sysTags: ノードタイプをタグとして設定
  const sysTags: string[] = [];
  if (nodeType) sysTags.push(nodeType);

  return {
    id: String(jjId),
    name,
    body: "",
    entityType: null,
    sysTags,
    userTags: [],
    sysProps,
    userProps: {},
    remark: null,
    domain: format || null,
    domainSource: "auto",
    domainConfidence: null,
    createdBy: null,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  };
}

export class Neo4jEntityRepository implements IEntityRepository {
  async getAllEntities(): Promise<StringEntity[]> {
    const session = getSession();
    try {
      const result = await session.run(
        `MATCH (n)
				 WHERE n.jj_id IS NOT NULL
				 RETURN properties(n) AS props
				 ORDER BY n.name`,
      );
      return result.records.map((r) =>
        recordToEntity(r.get("props") as Record<string, unknown>),
      );
    } finally {
      await session.close();
    }
  }

  async getEntitiesByUser(_userId: string): Promise<StringEntity[]> {
    // Neo4j上のjjデータにはcreatedByの概念がないため全件返す
    return this.getAllEntities();
  }

  async getEntityById(id: string): Promise<StringEntity | null> {
    const session = getSession();
    try {
      const result = await session.run(
        `MATCH (n)
				 WHERE n.jj_id = $jjId OR toString(n.jj_id) = $id
				 RETURN properties(n) AS props
				 LIMIT 1`,
        { jjId: Number.parseInt(id, 10) || 0, id },
      );
      if (result.records.length === 0) return null;
      return recordToEntity(
        result.records[0].get("props") as Record<string, unknown>,
      );
    } finally {
      await session.close();
    }
  }

  async getEntityByIdForUser(
    id: string,
    _userId: string,
  ): Promise<StringEntity | null> {
    return this.getEntityById(id);
  }

  async createEntity(_entity: StringEntity): Promise<StringEntity> {
    throw new Error(
      "Neo4jEntityRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async updateEntity(_entity: StringEntity): Promise<StringEntity> {
    throw new Error(
      "Neo4jEntityRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async upsertEntity(_entity: StringEntity): Promise<StringEntity> {
    throw new Error(
      "Neo4jEntityRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async deleteEntity(_id: string): Promise<boolean> {
    throw new Error(
      "Neo4jEntityRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async deleteEntityForUser(_id: string, _userId: string): Promise<boolean> {
    throw new Error(
      "Neo4jEntityRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async searchEntities(query: string): Promise<StringEntity[]> {
    const session = getSession();
    try {
      const result = await session.run(
        `MATCH (n)
				 WHERE n.jj_id IS NOT NULL
					 AND (n.name CONTAINS $query
						 OR n.type CONTAINS $query
						 OR n.format CONTAINS $query)
				 RETURN properties(n) AS props
				 ORDER BY n.name
				 LIMIT 100`,
        { query },
      );
      return result.records.map((r) =>
        recordToEntity(r.get("props") as Record<string, unknown>),
      );
    } finally {
      await session.close();
    }
  }

  async searchEntitiesByUser(
    query: string,
    _userId: string,
  ): Promise<StringEntity[]> {
    return this.searchEntities(query);
  }

  async getEntityCount(): Promise<number> {
    const session = getSession();
    try {
      const result = await session.run(
        "MATCH (n) WHERE n.jj_id IS NOT NULL RETURN count(n) AS cnt",
      );
      const cnt = result.records[0]?.get("cnt");
      return typeof cnt === "object" && cnt !== null && "toNumber" in cnt
        ? (cnt as { toNumber: () => number }).toNumber()
        : Number(cnt) || 0;
    } finally {
      await session.close();
    }
  }

  async getEntityCountByUser(_userId: string): Promise<number> {
    return this.getEntityCount();
  }
}
