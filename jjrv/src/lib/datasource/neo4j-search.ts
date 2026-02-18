/**
 * Neo4j検索アダプター (6-N-07)
 *
 * Cypher全文検索・プロパティフィルタリングの拡張検索機能。
 * 全文検索インデックス（jjfile_fulltext等）が存在する場合はそれを使用し、
 * 存在しない場合はCONTAINSフォールバックを行う。
 */

import type { StringEntity } from "../types";
import { getSession } from "./neo4j-driver";

/** 検索オプション */
export type Neo4jSearchOptions = {
  query?: string;
  nodeType?: string;
  format?: string;
  project?: string;
  propertyKey?: string;
  propertyValue?: string;
  limit?: number;
  offset?: number;
};

/** 検索結果 */
export type Neo4jSearchResult = {
  entities: StringEntity[];
  totalCount: number;
  usedFulltext: boolean;
};

/** Neo4jレコード → StringEntity 変換（neo4j-entity-repositoryと同一ロジック） */
function recordToEntity(record: Record<string, unknown>): StringEntity {
  const jjId = record.jj_id as number | string;
  const project = (record.project as string) || "";
  const name = (record.name as string) || "";
  const nodeType = (record.type as string) || "";
  const format = (record.format as string) || "";

  const sysProps: Record<string, string> = {};
  const skipKeys = new Set(["jj_id", "name", "type", "format", "project"]);

  for (const [key, value] of Object.entries(record)) {
    if (skipKeys.has(key) || value == null) continue;
    sysProps[key] = typeof value === "string" ? value : JSON.stringify(value);
  }

  if (format) sysProps.format = format;
  if (project) sysProps.project = project;

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

/** 全文検索インデックスが存在するか確認 */
async function hasFulltextIndex(indexName: string): Promise<boolean> {
  const session = getSession();
  try {
    const result = await session.run(
      "SHOW FULLTEXT INDEXES WHERE name = $name",
      { name: indexName },
    );
    return result.records.length > 0;
  } catch {
    // SHOW FULLTEXT INDEXES が未サポートの場合
    return false;
  } finally {
    await session.close();
  }
}

/**
 * Lucene全文検索クエリ文字列のエスケープ
 * 特殊文字をエスケープし、ワイルドカード検索に変換
 */
function buildFulltextQuery(query: string): string {
  // Lucene特殊文字をエスケープ
  const escaped = query.replace(/[+\-&|!(){}[\]^"~*?:\\/]/g, "\\$&");
  // 各単語に前方一致ワイルドカードを付加
  const terms = escaped
    .split(/\s+/)
    .filter(Boolean)
    .map((t) => `${t}*`);
  return terms.join(" AND ");
}

/** WHERE条件のフラグメントとパラメータを構築 */
function buildFilterFragments(
  options: Neo4jSearchOptions,
  params: Record<string, unknown>,
): string[] {
  const conditions: string[] = [];
  if (options.nodeType) {
    conditions.push("n.type = $nodeType");
    params.nodeType = options.nodeType;
  }
  if (options.format) {
    conditions.push("n.format CONTAINS $format");
    params.format = options.format;
  }
  if (options.project) {
    conditions.push("n.project = $project");
    params.project = options.project;
  }
  if (options.propertyKey && options.propertyValue !== undefined) {
    // 動的プロパティキーはパラメータ化できないため、安全な名前のみ許可
    const safeKey = options.propertyKey.replace(/[^a-zA-Z0-9_]/g, "");
    if (safeKey) {
      conditions.push(`toString(n.\`${safeKey}\`) CONTAINS $propValue`);
      params.propValue = options.propertyValue;
    }
  }
  return conditions;
}

/**
 * Neo4j全文検索（全文検索インデックス使用 → CONTAINSフォールバック）
 */
export async function searchNeo4j(
  options: Neo4jSearchOptions,
): Promise<Neo4jSearchResult> {
  const limit = options.limit ?? 100;
  const offset = options.offset ?? 0;
  const query = options.query?.trim() || "";

  // 全文検索インデックスを試行
  if (query) {
    const hasIndex = await hasFulltextIndex("jjfile_fulltext");
    if (hasIndex) {
      return fulltextSearch(query, options, limit, offset);
    }
  }

  // フォールバック: CONTAINS検索
  return containsSearch(query, options, limit, offset);
}

/** 全文検索インデックスを使用した検索 */
async function fulltextSearch(
  query: string,
  options: Neo4jSearchOptions,
  limit: number,
  offset: number,
): Promise<Neo4jSearchResult> {
  const session = getSession();
  try {
    const ftQuery = buildFulltextQuery(query);
    const params: Record<string, unknown> = {
      ftQuery,
      limit: offset + limit,
    };

    const filterConditions = buildFilterFragments(options, params);
    const whereClause =
      filterConditions.length > 0
        ? `WHERE ${filterConditions.join(" AND ")}`
        : "";

    // 全文検索（JJFile + JJMaterial の両インデックスをUNION）
    const cypher = `
      CALL db.index.fulltext.queryNodes('jjfile_fulltext', $ftQuery)
      YIELD node AS n, score
      ${whereClause}
      RETURN properties(n) AS props, score
      ORDER BY score DESC
      LIMIT toInteger($limit)
    `;

    const result = await session.run(cypher, params);
    const allEntities = result.records.map((r) =>
      recordToEntity(r.get("props") as Record<string, unknown>),
    );

    return {
      entities: allEntities.slice(offset, offset + limit),
      totalCount: allEntities.length,
      usedFulltext: true,
    };
  } finally {
    await session.close();
  }
}

/** CONTAINS検索（フォールバック） */
async function containsSearch(
  query: string,
  options: Neo4jSearchOptions,
  limit: number,
  offset: number,
): Promise<Neo4jSearchResult> {
  const session = getSession();
  try {
    const params: Record<string, unknown> = {
      limit: offset + limit,
    };

    const conditions: string[] = ["n.jj_id IS NOT NULL"];

    if (query) {
      conditions.push(
        "(n.name CONTAINS $query OR n.type CONTAINS $query OR n.format CONTAINS $query)",
      );
      params.query = query;
    }

    const extraConditions = buildFilterFragments(options, params);
    conditions.push(...extraConditions);

    // カウントクエリ
    const countCypher = `
      MATCH (n)
      WHERE ${conditions.join(" AND ")}
      RETURN count(n) AS cnt
    `;

    // データクエリ
    const dataCypher = `
      MATCH (n)
      WHERE ${conditions.join(" AND ")}
      RETURN properties(n) AS props
      ORDER BY n.name
      LIMIT toInteger($limit)
    `;

    const [countResult, dataResult] = await Promise.all([
      session.run(countCypher, params),
      session.run(dataCypher, params),
    ]);

    const cnt = countResult.records[0]?.get("cnt");
    const totalCount =
      typeof cnt === "object" && cnt !== null && "toNumber" in cnt
        ? (cnt as { toNumber: () => number }).toNumber()
        : Number(cnt) || 0;

    const allEntities = dataResult.records.map((r) =>
      recordToEntity(r.get("props") as Record<string, unknown>),
    );

    return {
      entities: allEntities.slice(offset),
      totalCount,
      usedFulltext: false,
    };
  } finally {
    await session.close();
  }
}

/**
 * プロジェクト一覧を取得（Neo4j上の全プロジェクト名）
 */
export async function getProjects(): Promise<string[]> {
  const session = getSession();
  try {
    const result = await session.run(
      "MATCH (n) WHERE n.project IS NOT NULL RETURN DISTINCT n.project AS project ORDER BY project",
    );
    return result.records.map((r) => r.get("project") as string);
  } finally {
    await session.close();
  }
}

/**
 * ノードタイプ一覧を取得
 */
export async function getNodeTypes(): Promise<string[]> {
  const session = getSession();
  try {
    const result = await session.run(
      "MATCH (n) WHERE n.type IS NOT NULL RETURN DISTINCT n.type AS nodeType ORDER BY nodeType",
    );
    return result.records.map((r) => r.get("nodeType") as string);
  } finally {
    await session.close();
  }
}
