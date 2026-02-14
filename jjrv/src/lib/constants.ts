/**
 * 共有定数
 * クライアント/サーバー双方で利用可能な定数定義
 */

/** ルートレポジトリの固定ID */
export const ROOT_REPOSITORY_ID = "root";

/** 階層制約の対象となるリレーションラベル */
export const HIERARCHY_RELATION_LABELS_ARRAY = ["child", "contains"] as const;

/** ユーザー名前空間を示すsysTag */
export const USER_NAMESPACE_TAG = "user_namespace";

/**
 * レポジトリタイプ（管理データの大分類）
 * sysProps.repository_type に格納する値の候補
 */
export const REPOSITORY_TYPES = [
  "CAE案件",
  "材料物性",
  "解析モデル",
  "実験データ",
  "ドキュメント",
  "その他",
] as const;

export type RepositoryType = (typeof REPOSITORY_TYPES)[number] | string;
