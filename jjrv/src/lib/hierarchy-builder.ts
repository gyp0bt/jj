/**
 * 動的階層構築ロジック
 *
 * エンティティを指定された階層レベルに基づいてグループ化し、
 * ダイアグラム用のノードとエッジを構築する
 */

import type {
  DynamicHierarchyConfig,
  HierarchyFieldPath,
  HierarchyLevel,
  HierarchyPreset,
  Relation,
  RelationContext,
  StringEntity,
} from "./types";

// ========================================
// プロパティキー名の日本語ラベルマッピング
// ========================================

/**
 * プロパティキー名の日本語ラベルマッピング
 * ダイアグラムビュー用の定義
 */
export const PROPERTY_KEY_LABELS: Record<string, string> = {
  // 特殊フィールド
  entityType: "タイプ",
  domain: "ドメイン",
  createdBy: "登録ユーザー",
  "sysTags.0": "プライマリタグ",
  "sysTags.1": "セカンダリタグ",
  // よく使われるプロパティ
  category: "カテゴリ",
  subcategory: "サブカテゴリ",
  grade: "グレード",
  material: "材料",
  type: "タイプ",
  class: "クラス",
  group: "グループ",
  manufacturer: "メーカー",
  standard: "規格",
  density: "密度",
  temperature: "温度",
  product: "製品",
  supplier: "サプライヤー",
  version: "バージョン",
};

/**
 * プロパティキー名を表示用ラベルに変換
 */
export function getPropertyKeyLabel(key: string): string {
  // sysProps.xxx や userProps.xxx の形式を処理
  if (key.startsWith("sysProps.")) {
    const propKey = key.slice("sysProps.".length);
    return PROPERTY_KEY_LABELS[propKey] ?? `sys: ${propKey}`;
  }
  if (key.startsWith("userProps.")) {
    const propKey = key.slice("userProps.".length);
    return PROPERTY_KEY_LABELS[propKey] ?? `user: ${propKey}`;
  }
  return PROPERTY_KEY_LABELS[key] ?? key;
}

// ========================================
// フィールド値の取得
// ========================================

/**
 * StringEntityからフィールドパスに基づいて値を取得
 * relation.{label} パスの場合は relationContext が必要
 */
export function getFieldValue(
  entity: StringEntity,
  field: HierarchyFieldPath,
  relationContext?: RelationContext,
): string | null {
  if (field === "entityType") {
    return entity.entityType ?? null;
  }
  if (field === "domain") {
    return entity.domain ?? null;
  }
  if (field === "createdBy") {
    return entity.createdBy ?? null;
  }
  if (field.startsWith("sysTags.")) {
    const index = Number.parseInt(field.split(".")[1], 10);
    return entity.sysTags[index] ?? null;
  }
  if (field.startsWith("sysProps.")) {
    const key = field.slice("sysProps.".length);
    return entity.sysProps[key] ?? null;
  }
  if (field.startsWith("userProps.")) {
    const key = field.slice("userProps.".length);
    return entity.userProps[key] ?? null;
  }
  // 2-12: relation label ベースの階層
  if (field.startsWith("relation.") && relationContext) {
    const label = field.slice("relation.".length);
    const rel = relationContext.relations.find(
      (r) =>
        r.label === label &&
        (r.entity1Id === entity.id || r.entity2Id === entity.id),
    );
    if (!rel) return null;
    const targetId =
      rel.entity1Id === entity.id ? rel.entity2Id : rel.entity1Id;
    return relationContext.entityMap.get(targetId)?.name ?? null;
  }
  return null;
}

/**
 * フィールドパスの表示名を取得
 */
export function getFieldDisplayName(field: HierarchyFieldPath): string {
  if (field === "entityType") return "タイプ";
  if (field === "domain") return "ドメイン";
  if (field === "createdBy") return "登録ユーザー";
  if (field.startsWith("sysTags.")) {
    const index = field.split(".")[1];
    return `システムタグ[${index}]`;
  }
  if (field.startsWith("sysProps.")) {
    const key = field.slice("sysProps.".length);
    return `sysProps.${key}`;
  }
  if (field.startsWith("userProps.")) {
    const key = field.slice("userProps.".length);
    return `userProps.${key}`;
  }
  // 2-12: relation label
  if (field.startsWith("relation.")) {
    const label = field.slice("relation.".length);
    return `rel: ${label}`;
  }
  return field;
}

// ========================================
// 階層ノード・エッジの型定義
// ========================================

export type HierarchyNodeType = "level" | "entity";

export type HierarchyNode = {
  id: string;
  name: string;
  type: HierarchyNodeType;
  levelIndex: number; // 階層のインデックス（entityは最後のインデックス+1）
  levelId?: string; // HierarchyLevelのid
  color: string;
  size: number;
  entity?: StringEntity;
};

export type HierarchyLink = {
  source: string;
  target: string;
};

export type HierarchyDiagramData = {
  nodes: HierarchyNode[];
  links: HierarchyLink[];
  levels: HierarchyLevel[]; // 使用された階層レベル（参照用）
};

// ========================================
// デフォルトの階層色
// ========================================

const DEFAULT_LEVEL_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#d946ef", // fuchsia
  "#ec4899", // pink
  "#f43f5e", // rose
  "#f97316", // orange
  "#eab308", // yellow
];

const ENTITY_COLOR = "#64748b"; // slate

// ========================================
// 動的階層構築
// ========================================

type GroupNode = {
  id: string;
  name: string;
  levelIndex: number;
  levelId: string;
  color: string;
  children: Map<string, GroupNode | StringEntity[]>;
};

/**
 * 値フィルターを適用してエンティティをフィルタリング
 */
function applyValueFilter(
  entities: StringEntity[],
  level: HierarchyLevel,
): StringEntity[] {
  // valueFilterが未設定または空配列の場合は全て通す
  if (!level.valueFilter || level.valueFilter.length === 0) {
    return entities;
  }

  return entities.filter((entity) => {
    const value = getFieldValue(entity, level.field);
    // valueがnullの場合は「未分類」として扱う
    const effectiveValue = value ?? "未分類";
    return level.valueFilter?.includes(effectiveValue);
  });
}

/**
 * エンティティを階層的にグループ化
 */
function groupEntitiesRecursive(
  entities: StringEntity[],
  levels: HierarchyLevel[],
  levelIndex: number,
  parentPath: string,
  relationContext?: RelationContext,
): Map<string, GroupNode | StringEntity[]> {
  const result = new Map<string, GroupNode | StringEntity[]>();

  if (levelIndex >= levels.length) {
    // 最深層：エンティティをそのまま返す
    result.set("entities", entities);
    return result;
  }

  const level = levels[levelIndex];

  // 値フィルターを適用
  const filteredEntities = applyValueFilter(entities, level);

  const groups = new Map<string, StringEntity[]>();

  // 現在のレベルでグループ化
  for (const entity of filteredEntities) {
    const value =
      getFieldValue(entity, level.field, relationContext) ?? "未分類";
    if (!groups.has(value)) {
      groups.set(value, []);
    }
    groups.get(value)?.push(entity);
  }

  // 各グループを再帰的に処理
  for (const [groupName, groupEntities] of groups) {
    const nodeId = `${parentPath}:${level.id}:${groupName}`;
    const color =
      level.color ??
      DEFAULT_LEVEL_COLORS[levelIndex % DEFAULT_LEVEL_COLORS.length];

    const children = groupEntitiesRecursive(
      groupEntities,
      levels,
      levelIndex + 1,
      nodeId,
      relationContext,
    );

    const groupNode: GroupNode = {
      id: nodeId,
      name: groupName,
      levelIndex,
      levelId: level.id,
      color,
      children,
    };

    result.set(groupName, groupNode);
  }

  return result;
}

/**
 * グループツリーをフラットなノード・リンク構造に変換
 */
function flattenGroupTree(
  groups: Map<string, GroupNode | StringEntity[]>,
  parentId: string | null,
  nodes: HierarchyNode[],
  links: HierarchyLink[],
  levels: HierarchyLevel[],
  nodeIds: Set<string>,
): void {
  for (const [key, value] of groups) {
    if (key === "entities" && Array.isArray(value)) {
      // エンティティ配列
      for (const entity of value) {
        const entityId = `entity:${entity.id}`;
        if (!nodeIds.has(entityId)) {
          nodeIds.add(entityId);
          nodes.push({
            id: entityId,
            name: entity.name,
            type: "entity",
            levelIndex: levels.length,
            color: ENTITY_COLOR,
            size: 6,
            entity,
          });
        }
        if (parentId) {
          links.push({ source: parentId, target: entityId });
        }
      }
    } else if (typeof value === "object" && "children" in value) {
      // グループノード
      const groupNode = value as GroupNode;
      if (!nodeIds.has(groupNode.id)) {
        nodeIds.add(groupNode.id);
        const sizeByLevel = Math.max(8, 18 - groupNode.levelIndex * 3);
        nodes.push({
          id: groupNode.id,
          name: groupNode.name,
          type: "level",
          levelIndex: groupNode.levelIndex,
          levelId: groupNode.levelId,
          color: groupNode.color,
          size: sizeByLevel,
        });
      }
      if (parentId) {
        links.push({ source: parentId, target: groupNode.id });
      }
      // 子を再帰処理
      flattenGroupTree(
        groupNode.children,
        groupNode.id,
        nodes,
        links,
        levels,
        nodeIds,
      );
    }
  }
}

/**
 * 動的階層に基づいてダイアグラムデータを構築
 * 2-12: relationContext を渡すと relation.{label} フィールドを解決可能
 */
export function buildDynamicHierarchy(
  entities: StringEntity[],
  config: DynamicHierarchyConfig,
  relationContext?: RelationContext,
): HierarchyDiagramData {
  const { levels } = config;
  const nodes: HierarchyNode[] = [];
  const links: HierarchyLink[] = [];
  const nodeIds = new Set<string>();

  if (levels.length === 0) {
    // 階層なし：エンティティのみ
    for (const entity of entities) {
      const entityId = `entity:${entity.id}`;
      nodes.push({
        id: entityId,
        name: entity.name,
        type: "entity",
        levelIndex: 0,
        color: ENTITY_COLOR,
        size: 6,
        entity,
      });
    }
    return { nodes, links, levels };
  }

  // 階層的にグループ化
  const groupTree = groupEntitiesRecursive(
    entities,
    levels,
    0,
    "root",
    relationContext,
  );

  // フラット化
  flattenGroupTree(groupTree, null, nodes, links, levels, nodeIds);

  return { nodes, links, levels };
}

// ========================================
// プリセット定義
// ========================================

/**
 * デフォルトの階層プリセット
 */
export const DEFAULT_HIERARCHY_PRESETS: HierarchyPreset[] = [
  {
    id: "type-domain-tag",
    name: "タイプ → ドメイン → タグ",
    description:
      "デフォルト: エンティティタイプ、ドメイン、プライマリタグで階層化",
    levels: [
      {
        id: "entityType",
        label: "タイプ",
        field: "entityType",
        color: "#6366f1",
      },
      { id: "domain", label: "ドメイン", field: "domain", color: "#8b5cf6" },
      { id: "primaryTag", label: "タグ", field: "sysTags.0", color: "#f59e0b" },
    ],
  },
  {
    id: "user-type-domain",
    name: "ユーザー → タイプ → ドメイン",
    description: "登録ユーザーごとにグループ化",
    levels: [
      {
        id: "createdBy",
        label: "登録ユーザー",
        field: "createdBy",
        color: "#10b981",
      },
      {
        id: "entityType",
        label: "タイプ",
        field: "entityType",
        color: "#6366f1",
      },
      { id: "domain", label: "ドメイン", field: "domain", color: "#8b5cf6" },
    ],
  },
  {
    id: "domain-type",
    name: "ドメイン → タイプ",
    description: "ドメイン優先でグループ化",
    levels: [
      { id: "domain", label: "ドメイン", field: "domain", color: "#8b5cf6" },
      {
        id: "entityType",
        label: "タイプ",
        field: "entityType",
        color: "#6366f1",
      },
    ],
  },
  {
    id: "flat",
    name: "フラット表示",
    description: "階層なし（エンティティのみ）",
    levels: [],
  },
];

// ========================================
// 2-15: 自動階層検出
// ========================================

/**
 * relation label の出現頻度順に自動で階層を定義
 * ダイアグラムビュー用: 最も多いrelation labelから順に階層化
 */
export function autoDetectHierarchyFromRelations(
  relations: Relation[],
): HierarchyLevel[] {
  if (!relations || relations.length === 0) return [];

  // label の出現頻度をカウント
  const labelCount = new Map<string, number>();
  for (const rel of relations) {
    labelCount.set(rel.label, (labelCount.get(rel.label) ?? 0) + 1);
  }

  // 頻度順にソートし、上位3つまでを階層化
  const sortedLabels = Array.from(labelCount.entries())
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return sortedLabels.map(([label], idx) => ({
    id: `relation-${label}`,
    label: `rel: ${label}`,
    field: `relation.${label}` as HierarchyFieldPath,
    color: DEFAULT_LEVEL_COLORS[idx % DEFAULT_LEVEL_COLORS.length],
  }));
}

/**
 * 基本の階層フィールド（常に利用可能）
 */
const BASE_HIERARCHY_FIELDS: { field: HierarchyFieldPath; label: string }[] = [
  { field: "entityType", label: "タイプ" },
  { field: "domain", label: "ドメイン" },
  { field: "createdBy", label: "登録ユーザー" },
  { field: "sysTags.0", label: "プライマリタグ" },
  { field: "sysTags.1", label: "セカンダリタグ" },
];

/**
 * 利用可能な階層フィールドの一覧を取得
 * エンティティを渡すと、動的にプロパティを検出して追加
 * relationsを渡すと、relation labelも候補に追加 (2-12)
 */
export function getAvailableHierarchyFields(
  entities?: StringEntity[],
  relations?: Relation[],
): {
  field: HierarchyFieldPath;
  label: string;
  group?: "base" | "sysProps" | "userProps" | "relation";
}[] {
  const baseFields = BASE_HIERARCHY_FIELDS.map((f) => ({
    ...f,
    group: "base" as const,
  }));

  if (!entities || entities.length === 0) {
    return baseFields;
  }

  // エンティティからカスタムフィールドを検出
  const customFields = detectCustomFields(entities);

  // sysPropsとuserPropsに分類
  const sysPropsFields = customFields
    .filter((f) => f.field.startsWith("sysProps."))
    .map((f) => ({ ...f, group: "sysProps" as const }));
  const userPropsFields = customFields
    .filter((f) => f.field.startsWith("userProps."))
    .map((f) => ({ ...f, group: "userProps" as const }));

  // 2-12: relation label をフィールド候補に追加
  const relationFields: {
    field: HierarchyFieldPath;
    label: string;
    group: "relation";
  }[] = [];
  if (relations && relations.length > 0) {
    const labels = new Set<string>();
    for (const rel of relations) {
      labels.add(rel.label);
    }
    for (const label of labels) {
      relationFields.push({
        field: `relation.${label}` as HierarchyFieldPath,
        label: `rel: ${label}`,
        group: "relation",
      });
    }
  }

  return [
    ...baseFields,
    ...relationFields,
    ...sysPropsFields,
    ...userPropsFields,
  ];
}

/**
 * エンティティ群から動的にカスタムフィールドを検出
 * プロパティキーの出現頻度でソートして返す
 */
export function detectCustomFields(
  entities: StringEntity[],
): { field: HierarchyFieldPath; label: string }[] {
  // プロパティキーの出現頻度をカウント
  const sysPropsCount = new Map<string, number>();
  const userPropsCount = new Map<string, number>();

  for (const entity of entities) {
    for (const key of Object.keys(entity.sysProps)) {
      sysPropsCount.set(key, (sysPropsCount.get(key) ?? 0) + 1);
    }
    for (const key of Object.keys(entity.userProps)) {
      userPropsCount.set(key, (userPropsCount.get(key) ?? 0) + 1);
    }
  }

  const result: { field: HierarchyFieldPath; label: string }[] = [];

  // sysPropsを頻度順でソート
  const sortedSysProps = Array.from(sysPropsCount.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);

  for (const key of sortedSysProps) {
    result.push({
      field: `sysProps.${key}` as HierarchyFieldPath,
      label: getPropertyKeyLabel(`sysProps.${key}`),
    });
  }

  // userPropsを頻度順でソート
  const sortedUserProps = Array.from(userPropsCount.entries())
    .sort((a, b) => b[1] - a[1])
    .map(([key]) => key);

  for (const key of sortedUserProps) {
    result.push({
      field: `userProps.${key}` as HierarchyFieldPath,
      label: getPropertyKeyLabel(`userProps.${key}`),
    });
  }

  return result;
}
