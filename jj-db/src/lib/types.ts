export type EntityType = "Material" | "Project" | "Tag" | null;

/**
 * ドキュメント（別オブジェクト）
 * エンティティに添付されるファイルやドキュメントを管理
 */
export type Document = {
  id: number;
  name: string;
  relativePath: string;
  mimeType?: string | null;
  size?: number | null;
  description?: string | null;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
};

/**
 * 添付ドキュメント情報
 * エンティティとドキュメントの関連付け
 */
export type AttachedDocument = {
  relativePath: string;
  documentId: number;
};

export type StringEntity = {
  id: string;
  name: string;
  body: string;
  // entity type
  entityType?: EntityType;
  // tags
  sysTags: string[];
  userTags: string[];
  // properties
  sysProps: Record<string, string>;
  userProps: Record<string, string>;
  // attached documents
  attachedDocuments?: AttachedDocument[];
  remark?: string | null;
  domain?: string | null;
  domainSource?: "user" | "auto" | "curation" | null;
  domainConfidence?: number | null;
  createdBy?: string | null;
  createdAt: string;
  updatedAt: string;
};

// エンティティ間の関係
// 階層リレーション（child/contains）では entity1Id が親（上位）、entity2Id が子（下位）
export type Relation = {
  id: string;
  label: string;
  entity1Id: string;
  entity2Id: string;
  createdAt: string;
};

// ========================================
// 階層制約の型定義 (spec-roadmap5)
// ========================================

/** 階層制約の対象となるリレーションラベル */
export const HIERARCHY_LABELS = ["child", "contains"] as const;
export type HierarchyLabel = (typeof HIERARCHY_LABELS)[number];

/** 階層制約バリデーションエラー */
export type HierarchyConstraintError = {
  code: string;
  message: string;
};

// ユーザー関連の型
export type User = {
  id: string;
  username: string;
  displayName: string;
  avatar?: string | null;
  role: "admin" | "user";
  createdAt: string;
  updatedAt: string;
};

export type UserWithPassword = User & {
  passwordHash: string;
};

export type SearchHistory = {
  id: string;
  userId: string;
  query: string;
  filters: Record<string, unknown>;
  resultCount: number;
  createdAt: string;
};

export type Favorite = {
  id: string;
  userId: string;
  entityId: string;
  createdAt: string;
};

export type Good = {
  id: string;
  userId: string;
  entityId: string;
  createdAt: string;
};

export type Download = {
  id: string;
  userId: string;
  entityId: string;
  createdAt: string;
};

// エンティティ統計（集計用）
export type EntityStats = {
  entityId: string;
  favoriteCount: number;
  goodCount: number;
  downloadCount: number;
};

export type DomainPlugin = {
  key: string; // 例: "abaqus_inp"
  label: string; // 表示名
  color: "sky" | "teal" | "slate" | "zinc" | string;
  icon?: React.ComponentType<{ className?: string }>;
  // レンダラー（詳細ビュー用）。未実装でもOK（汎用ビューにフォールバック）。
  Renderer?: React.ComponentType<{ entity: StringEntity }>;
  // アップローダ（取り込み画面）。未実装なら汎用アップローダを使う。
  Uploader?: React.ComponentType;
  // 軽量検出器（検索・一覧での候補ドメイン推定用）
  detect?: (body: string) => number; // 0..1 のスコア
};

// ========================================
// 動的階層グループ化の型定義
// ========================================

/**
 * 階層レベルの定義
 * ダイアグラムで使用する階層の1レベルを表す
 */
export type HierarchyLevel = {
  id: string; // 一意のID（ドラッグ&ドロップ用）
  label: string; // 表示ラベル（例: "登録ユーザー", "製品", "材料種"）
  field: HierarchyFieldPath; // StringEntityのフィールドパス
  color?: string; // 階層の色（省略時はデフォルト色）
  /** 値フィルター: 指定した値のみを表示（空配列または未指定で全て表示） */
  valueFilter?: string[];
};

/**
 * フィールドパスの型
 * StringEntityから値を取得するためのパス指定
 *
 * 例:
 * - "entityType" → entity.entityType
 * - "domain" → entity.domain
 * - "createdBy" → entity.createdBy
 * - "sysTags.0" → entity.sysTags[0]（最初のシステムタグ）
 * - "sysProps.product" → entity.sysProps["product"]
 * - "userProps.category" → entity.userProps["category"]
 * - "relation.tagged_with" → entity の relation(label=tagged_with) 先のname (2-12)
 */
export type HierarchyFieldPath =
  | "entityType"
  | "domain"
  | "createdBy"
  | `sysTags.${number}`
  | `sysProps.${string}`
  | `userProps.${string}`
  | `relation.${string}`;

/**
 * Relation解決コンテキスト
 * getFieldValue でrelationフィールドを解決するために使用
 */
export type RelationContext = {
  relations: Relation[];
  entityMap: Map<string, StringEntity>;
};

/**
 * 階層プリセット
 * よく使う階層構成のテンプレート
 */
export type HierarchyPreset = {
  id: string;
  name: string;
  description?: string;
  levels: HierarchyLevel[];
};

/**
 * 動的階層設定
 * ダイアグラムに渡す階層構成
 */
export type DynamicHierarchyConfig = {
  levels: HierarchyLevel[]; // 階層レベルの配列（順序が階層順序）
};
