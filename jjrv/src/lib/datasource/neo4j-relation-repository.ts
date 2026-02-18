import type { Relation, StringEntity } from "../types";
import { getSession } from "./neo4j-driver";
import type {
  IRelationRepository,
  RelatedEntityWithDepth,
  RelationGraphResult,
} from "./types";

/**
 * Neo4jリレーションシップタイプ → jjrv Relation.label のマッピング（逆変換）
 *
 * jj側の LABEL_TO_RELTYPE の逆引き。
 * Neo4j上は大文字（NEXT_VERSION）、jjrv側は小文字（next_version）。
 */
function relTypeToLabel(relType: string): string {
  return relType.toLowerCase();
}

function toStringEntity(props: Record<string, unknown>): StringEntity {
  const jjId = props.jj_id as number | string;
  const name = (props.name as string) || "";
  const nodeType = (props.type as string) || "";
  const format = (props.format as string) || "";
  const project = (props.project as string) || "";

  const sysProps: Record<string, string> = {};
  const skipKeys = new Set(["jj_id", "name", "type", "format", "project"]);
  for (const [key, value] of Object.entries(props)) {
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

export class Neo4jRelationRepository implements IRelationRepository {
  async getAllRelations(): Promise<Relation[]> {
    const session = getSession();
    try {
      const result = await session.run(
        `MATCH (a)-[r]->(b)
				 WHERE a.jj_id IS NOT NULL AND b.jj_id IS NOT NULL
				 RETURN toString(a.jj_id) AS src,
						toString(b.jj_id) AS dst,
						type(r) AS relType,
						id(r) AS relId
				 LIMIT 1000`,
      );
      return result.records.map((rec) => {
        const relId = rec.get("relId");
        return {
          id: String(
            typeof relId === "object" && relId !== null && "toNumber" in relId
              ? (relId as { toNumber: () => number }).toNumber()
              : relId,
          ),
          label: relTypeToLabel(rec.get("relType") as string),
          entity1Id: rec.get("src") as string,
          entity2Id: rec.get("dst") as string,
          createdAt: new Date().toISOString(),
        };
      });
    } finally {
      await session.close();
    }
  }

  async getRelationsByEntityIds(entityIds: string[]): Promise<Relation[]> {
    if (entityIds.length === 0) return [];
    const session = getSession();
    try {
      const numericIds = entityIds
        .map((id) => Number.parseInt(id, 10))
        .filter((n) => !Number.isNaN(n));
      const result = await session.run(
        `MATCH (a)-[r]->(b)
				 WHERE a.jj_id IN $ids AND b.jj_id IN $ids
				 RETURN toString(a.jj_id) AS src,
						toString(b.jj_id) AS dst,
						type(r) AS relType,
						id(r) AS relId`,
        { ids: numericIds },
      );
      return result.records.map((rec) => {
        const relId = rec.get("relId");
        return {
          id: String(
            typeof relId === "object" && relId !== null && "toNumber" in relId
              ? (relId as { toNumber: () => number }).toNumber()
              : relId,
          ),
          label: relTypeToLabel(rec.get("relType") as string),
          entity1Id: rec.get("src") as string,
          entity2Id: rec.get("dst") as string,
          createdAt: new Date().toISOString(),
        };
      });
    } finally {
      await session.close();
    }
  }

  async getRelationsByEntityId(entityId: string): Promise<Relation[]> {
    const session = getSession();
    try {
      const numId = Number.parseInt(entityId, 10);
      const result = await session.run(
        `MATCH (a)-[r]-(b)
				 WHERE a.jj_id = $id
				 RETURN toString(a.jj_id) AS src,
						toString(b.jj_id) AS dst,
						type(r) AS relType,
						id(r) AS relId`,
        { id: Number.isNaN(numId) ? entityId : numId },
      );
      return result.records.map((rec) => {
        const relId = rec.get("relId");
        return {
          id: String(
            typeof relId === "object" && relId !== null && "toNumber" in relId
              ? (relId as { toNumber: () => number }).toNumber()
              : relId,
          ),
          label: relTypeToLabel(rec.get("relType") as string),
          entity1Id: rec.get("src") as string,
          entity2Id: rec.get("dst") as string,
          createdAt: new Date().toISOString(),
        };
      });
    } finally {
      await session.close();
    }
  }

  async getRelationsByLabel(label: string): Promise<Relation[]> {
    const session = getSession();
    const relType = label.toUpperCase();
    try {
      const result = await session.run(
        `MATCH (a)-[r:\`${relType}\`]->(b)
				 WHERE a.jj_id IS NOT NULL AND b.jj_id IS NOT NULL
				 RETURN toString(a.jj_id) AS src,
						toString(b.jj_id) AS dst,
						type(r) AS relType,
						id(r) AS relId
				 LIMIT 1000`,
      );
      return result.records.map((rec) => {
        const relId = rec.get("relId");
        return {
          id: String(
            typeof relId === "object" && relId !== null && "toNumber" in relId
              ? (relId as { toNumber: () => number }).toNumber()
              : relId,
          ),
          label: relTypeToLabel(rec.get("relType") as string),
          entity1Id: rec.get("src") as string,
          entity2Id: rec.get("dst") as string,
          createdAt: new Date().toISOString(),
        };
      });
    } finally {
      await session.close();
    }
  }

  async getRelatedEntities(
    entityId: string,
    label?: string,
  ): Promise<StringEntity[]> {
    const session = getSession();
    try {
      const numId = Number.parseInt(entityId, 10);
      const id = Number.isNaN(numId) ? entityId : numId;
      let cypher: string;

      if (label) {
        const relType = label.toUpperCase();
        cypher = `
					MATCH (a)-[:\`${relType}\`]-(b)
					WHERE a.jj_id = $id AND b.jj_id IS NOT NULL
					RETURN properties(b) AS props
					ORDER BY b.name`;
      } else {
        cypher = `
					MATCH (a)-[]-(b)
					WHERE a.jj_id = $id AND b.jj_id IS NOT NULL
					RETURN properties(b) AS props
					ORDER BY b.name`;
      }

      const result = await session.run(cypher, { id });
      return result.records.map((r) =>
        toStringEntity(r.get("props") as Record<string, unknown>),
      );
    } finally {
      await session.close();
    }
  }

  async getRelatedEntitiesGrouped(
    entityId: string,
  ): Promise<Record<string, StringEntity[]>> {
    const session = getSession();
    try {
      const numId = Number.parseInt(entityId, 10);
      const id = Number.isNaN(numId) ? entityId : numId;
      const result = await session.run(
        `MATCH (a)-[r]-(b)
				 WHERE a.jj_id = $id AND b.jj_id IS NOT NULL
				 RETURN type(r) AS relType, properties(b) AS props`,
        { id },
      );

      const groups: Record<string, StringEntity[]> = {};
      for (const rec of result.records) {
        const label = relTypeToLabel(rec.get("relType") as string);
        const entity = toStringEntity(
          rec.get("props") as Record<string, unknown>,
        );
        if (!groups[label]) groups[label] = [];
        groups[label].push(entity);
      }
      return groups;
    } finally {
      await session.close();
    }
  }

  async createRelation(_relation: Relation): Promise<Relation> {
    throw new Error(
      "Neo4jRelationRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async deleteRelation(_id: string): Promise<boolean> {
    throw new Error(
      "Neo4jRelationRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async deleteRelationsBetween(
    _entity1Id: string,
    _entity2Id: string,
  ): Promise<number> {
    throw new Error(
      "Neo4jRelationRepository: 書き込みはjj CLI経由で行ってください",
    );
  }

  async getRelationGraph(
    entityId: string,
    maxDepth = 2,
  ): Promise<RelationGraphResult | null> {
    const session = getSession();
    try {
      const numId = Number.parseInt(entityId, 10);
      const id = Number.isNaN(numId) ? entityId : numId;

      // 中心ノード取得
      const centerResult = await session.run(
        `MATCH (n) WHERE n.jj_id = $id
				 RETURN properties(n) AS props LIMIT 1`,
        { id },
      );
      if (centerResult.records.length === 0) return null;
      const center = toStringEntity(
        centerResult.records[0].get("props") as Record<string, unknown>,
      );

      // BFS的にN親等までのパスを取得
      const pathResult = await session.run(
        `MATCH path = (start)-[*1..${maxDepth}]-(end)
				 WHERE start.jj_id = $id AND end.jj_id IS NOT NULL
				 UNWIND relationships(path) AS r
				 WITH r, startNode(r) AS a, endNode(r) AS b,
					  length(shortestPath((start)-[*]-(end))) AS depth
				 WHERE start.jj_id = $id
				 RETURN DISTINCT
					toString(a.jj_id) AS src,
					toString(b.jj_id) AS dst,
					type(r) AS relType,
					properties(b) AS bProps,
					depth
				 ORDER BY depth`,
        { id },
      );

      const visited = new Set<string>([String(id)]);
      const nodes: RelatedEntityWithDepth[] = [];
      const edges: RelationGraphResult["edges"] = [];

      for (const rec of pathResult.records) {
        const src = rec.get("src") as string;
        const dst = rec.get("dst") as string;
        const depthVal = rec.get("depth");
        const depth =
          typeof depthVal === "object" &&
          depthVal !== null &&
          "toNumber" in depthVal
            ? (depthVal as { toNumber: () => number }).toNumber()
            : Number(depthVal) || 1;

        edges.push({
          from: src,
          to: dst,
          label: relTypeToLabel(rec.get("relType") as string),
          depth,
        });

        if (!visited.has(dst)) {
          visited.add(dst);
          const entity = toStringEntity(
            rec.get("bProps") as Record<string, unknown>,
          );
          nodes.push({
            entity,
            depth,
            relationLabel: relTypeToLabel(rec.get("relType") as string),
            parentId: src,
          });
        }
      }

      return { center, nodes, edges };
    } finally {
      await session.close();
    }
  }
}
