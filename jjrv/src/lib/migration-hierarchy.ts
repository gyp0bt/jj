/**
 * 階層制約マイグレーション (spec-roadmap5: 5-14, 5-15, 5-16)
 *
 * 既存データを階層制約に適合させるためのマイグレーションユーティリティ。
 * 孤立ノード（レポジトリツリーに属さないノード）をルートレポジトリ配下に配置する。
 */

import { getDb } from "./db";
import { findOrphanEntities } from "./hierarchy-validator";
import { ROOT_REPOSITORY_ID } from "./root-repository";

export type MigrationResult = {
  orphansFound: number;
  orphansFixed: number;
  details: Array<{
    entityId: string;
    entityName: string;
    action: "linked_to_root";
    label: "child" | "contains";
  }>;
};

/**
 * 孤立ノードをルートレポジトリ配下に配置する
 *
 * - レポジトリ → child リレーションでルートに接続
 * - ディレクトリ → child リレーションでルートに接続
 * - その他 → contains リレーションでルートに接続
 */
export async function migrateOrphansToRoot(): Promise<MigrationResult> {
  const db = await getDb();
  const orphans = await findOrphanEntities();

  const result: MigrationResult = {
    orphansFound: orphans.length,
    orphansFixed: 0,
    details: [],
  };

  for (const orphan of orphans) {
    const isRepoOrDir =
      orphan.entity.sysTags.includes("repository") ||
      orphan.entity.sysTags.includes("directory");
    const label: "child" | "contains" = isRepoOrDir ? "child" : "contains";
    const now = new Date().toISOString();
    const relationId = crypto.randomUUID();

    await db.run(
      `INSERT INTO relations (id, label, entity1_id, entity2_id, created_at)
       VALUES (@id, @label, @entity1_id, @entity2_id, @created_at)`,
      {
        id: relationId,
        label,
        entity1_id: ROOT_REPOSITORY_ID,
        entity2_id: orphan.entity.id,
        created_at: now,
      },
    );

    // エンティティ名を取得
    const entityRow = await db.get<{ name: string }>(
      "SELECT name FROM entities WHERE id = ?",
      orphan.entity.id,
    );

    result.details.push({
      entityId: orphan.entity.id,
      entityName: entityRow?.name ?? "(unknown)",
      action: "linked_to_root",
      label,
    });
    result.orphansFixed++;
  }

  return result;
}

/**
 * 孤立ノードの数を取得（ドライラン用）
 */
export async function countOrphanEntities(): Promise<number> {
  const orphans = await findOrphanEntities();
  return orphans.length;
}
