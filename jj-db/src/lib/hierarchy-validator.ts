/**
 * 階層バリデーション
 *
 * レポジトリ階層制約を検証するユーティリティ。
 *
 * ルール:
 * 1. レポジトリ以外のノードはレポジトリの下にしか存在できない
 * 2. レポジトリはレポジトリの下にしか存在できない
 * 3. ルートレポジトリが階層の最上位
 * 4. child/contains リレーションの entity1Id が親、entity2Id が子
 */

import { getDb } from "./db";
import { USER_NAMESPACE_TAG } from "./constants";
import { isRootRepository, ROOT_REPOSITORY_ID } from "./root-repository";
import type { StringEntity } from "./types";

// ========================================
// 定数
// ========================================

/** 階層制約の対象となるリレーションラベル */
export const HIERARCHY_RELATION_LABELS = new Set(["child", "contains"]);

// ========================================
// エラー型
// ========================================

export type HierarchyValidationError = {
  code:
    | "PARENT_REQUIRED"
    | "REPOSITORY_UNDER_NON_REPOSITORY"
    | "NON_REPOSITORY_PARENT_FOR_HIERARCHY"
    | "CIRCULAR_REFERENCE"
    | "ROOT_CANNOT_BE_CHILD"
    | "INVALID_HIERARCHY_LABEL"
    | "PARENT_NOT_FOUND";
  message: string;
};

export type HierarchyValidationResult =
  | { valid: true }
  | { valid: false; error: HierarchyValidationError };

// ========================================
// ユーティリティ
// ========================================

/**
 * エンティティがレポジトリかどうかを判定
 */
export function isRepository(entity: StringEntity): boolean {
  return entity.sysTags.includes("repository");
}

/**
 * エンティティがディレクトリかどうかを判定
 */
export function isDirectory(entity: StringEntity): boolean {
  return entity.sysTags.includes("directory");
}

/**
 * エンティティがユーザー名前空間かどうかを判定
 */
export function isUserNamespace(entity: StringEntity): boolean {
  return entity.sysTags.includes(USER_NAMESPACE_TAG);
}

/**
 * sysTagsからレポジトリかどうかを判定（JSON文字列対応）
 */
function isRepositoryFromTags(sysTags: string[]): boolean {
  return sysTags.includes("repository");
}

/**
 * sysTagsからディレクトリかどうかを判定
 */
function isDirectoryFromTags(sysTags: string[]): boolean {
  return sysTags.includes("directory");
}

/**
 * sysTagsからユーザー名前空間かどうかを判定
 */
function isUserNamespaceFromTags(sysTags: string[]): boolean {
  return sysTags.includes(USER_NAMESPACE_TAG);
}

// ========================================
// 階層リレーション検証
// ========================================

type EntityInfo = {
  id: string;
  sysTags: string[];
};

async function getEntityInfo(entityId: string): Promise<EntityInfo | null> {
  const db = await getDb();
  const row = await db.get<{ id: string; sys_tags: string }>(
    "SELECT id, sys_tags FROM entities WHERE id = ?",
    entityId,
  );
  if (!row) return null;
  return { id: row.id, sysTags: JSON.parse(row.sys_tags) };
}

/**
 * 階層リレーション（child/contains）の作成を検証
 *
 * @param parentId 親エンティティID (entity1Id)
 * @param childId 子エンティティID (entity2Id)
 * @param label リレーションラベル
 */
export async function validateHierarchyRelation(
  parentId: string,
  childId: string,
  label: string,
): Promise<HierarchyValidationResult> {
  // 階層リレーション以外は制約対象外
  if (!HIERARCHY_RELATION_LABELS.has(label)) {
    return { valid: true };
  }

  // ルートレポジトリを子にはできない
  if (isRootRepository(childId)) {
    return {
      valid: false,
      error: {
        code: "ROOT_CANNOT_BE_CHILD",
        message: "ルートレポジトリを子ノードにすることはできません",
      },
    };
  }

  // 親エンティティの情報を取得
  const parent = await getEntityInfo(parentId);
  if (!parent) {
    return {
      valid: false,
      error: {
        code: "PARENT_NOT_FOUND",
        message: `親エンティティが見つかりません: ${parentId}`,
      },
    };
  }

  // 子エンティティの情報を取得
  const child = await getEntityInfo(childId);
  if (!child) {
    return {
      valid: false,
      error: {
        code: "PARENT_NOT_FOUND",
        message: `子エンティティが見つかりません: ${childId}`,
      },
    };
  }

  const parentIsRepo = isRepositoryFromTags(parent.sysTags);
  const parentIsDir = isDirectoryFromTags(parent.sysTags);
  const parentIsUserNs = isUserNamespaceFromTags(parent.sysTags);
  const childIsRepo = isRepositoryFromTags(child.sysTags);
  const childIsUserNs = isUserNamespaceFromTags(child.sysTags);

  // ルール: 親はレポジトリ、ディレクトリ、またはユーザー名前空間でなければならない
  if (!parentIsRepo && !parentIsDir && !parentIsUserNs) {
    return {
      valid: false,
      error: {
        code: "NON_REPOSITORY_PARENT_FOR_HIERARCHY",
        message:
          "階層リレーション（child/contains）の親はレポジトリ、ディレクトリ、またはユーザー名前空間である必要があります",
      },
    };
  }

  // ルール: ユーザー名前空間の親はルートレポジトリのみ
  if (childIsUserNs && !isRootRepository(parentId)) {
    return {
      valid: false,
      error: {
        code: "REPOSITORY_UNDER_NON_REPOSITORY",
        message: "ユーザー名前空間はルートレポジトリの直下にのみ配置できます",
      },
    };
  }

  // ルール: レポジトリの親はレポジトリまたはユーザー名前空間のみ
  if (childIsRepo && !parentIsRepo && !parentIsUserNs) {
    return {
      valid: false,
      error: {
        code: "REPOSITORY_UNDER_NON_REPOSITORY",
        message:
          "レポジトリはレポジトリまたはユーザー名前空間の下にしか配置できません",
      },
    };
  }

  // ルール: ユーザー名前空間の下にはレポジトリのみ配置可能
  if (parentIsUserNs && !childIsRepo) {
    return {
      valid: false,
      error: {
        code: "NON_REPOSITORY_PARENT_FOR_HIERARCHY",
        message: "ユーザー名前空間の下にはレポジトリのみ配置できます",
      },
    };
  }

  // ルール: child ラベルの検証
  // child: レポジトリ→レポジトリ、レポジトリ→ディレクトリ、ディレクトリ→ディレクトリ
  // contains: レポジトリ/ディレクトリ→ファイル等
  // （ここでは厳密なラベル検証は行わず、親子の型整合のみ検証）

  // 循環参照チェック
  const circularCheck = await checkCircularReference(parentId, childId);
  if (!circularCheck.valid) {
    return circularCheck;
  }

  return { valid: true };
}

/**
 * 循環参照チェック
 * childId の子孫に parentId が存在しないことを確認
 */
async function checkCircularReference(
  parentId: string,
  childId: string,
): Promise<HierarchyValidationResult> {
  if (parentId === childId) {
    return {
      valid: false,
      error: {
        code: "CIRCULAR_REFERENCE",
        message: "自己参照はできません",
      },
    };
  }

  const db = await getDb();
  const visited = new Set<string>([childId]);
  const queue = [childId];

  while (queue.length > 0) {
    const currentId = queue.shift();
    if (!currentId) continue;
    const childRelations = await db.all<{
      entity2_id: string;
      label: string;
    }>(
      `SELECT entity2_id, label FROM relations
       WHERE entity1_id = ? AND label IN ('child', 'contains')`,
      currentId,
    );

    for (const rel of childRelations) {
      if (rel.entity2_id === parentId) {
        return {
          valid: false,
          error: {
            code: "CIRCULAR_REFERENCE",
            message:
              "循環参照が検出されました: この関係を作成すると循環が生じます",
          },
        };
      }
      if (!visited.has(rel.entity2_id)) {
        visited.add(rel.entity2_id);
        queue.push(rel.entity2_id);
      }
    }
  }

  return { valid: true };
}

// ========================================
// 祖先レポジトリ探索
// ========================================

/**
 * エンティティの祖先レポジトリを探索する。
 * child/contains 経路を逆順にたどり、最初に見つかるレポジトリを返す。
 *
 * @returns 祖先レポジトリのID、見つからなければ null
 */
export async function findAncestorRepository(
  entityId: string,
): Promise<string | null> {
  if (isRootRepository(entityId)) {
    return ROOT_REPOSITORY_ID;
  }

  const db = await getDb();
  const visited = new Set<string>([entityId]);
  const queue = [entityId];

  while (queue.length > 0) {
    const currentId = queue.shift();
    if (!currentId) continue;

    // currentId を子に持つ親を探す (entity1_id が親)
    const parentRelations = await db.all<{
      entity1_id: string;
      label: string;
    }>(
      `SELECT entity1_id, label FROM relations
       WHERE entity2_id = ? AND label IN ('child', 'contains')`,
      currentId,
    );

    for (const rel of parentRelations) {
      const parentEntity = await getEntityInfo(rel.entity1_id);
      if (
        parentEntity &&
        (isRepositoryFromTags(parentEntity.sysTags) ||
          isUserNamespaceFromTags(parentEntity.sysTags))
      ) {
        return parentEntity.id;
      }
      if (!visited.has(rel.entity1_id)) {
        visited.add(rel.entity1_id);
        queue.push(rel.entity1_id);
      }
    }
  }

  return null;
}

/**
 * エンティティからルートレポジトリまでの経路を取得
 * @returns ID配列（自身→...→ルート）、ルートに到達できない場合は null
 */
export async function getPathToRoot(
  entityId: string,
): Promise<string[] | null> {
  if (isRootRepository(entityId)) {
    return [ROOT_REPOSITORY_ID];
  }

  const db = await getDb();
  const path = [entityId];
  const visited = new Set<string>([entityId]);
  let currentId = entityId;

  while (currentId !== ROOT_REPOSITORY_ID) {
    // 親を探す
    const parentRel = await db.get<{
      entity1_id: string;
    }>(
      `SELECT entity1_id FROM relations
       WHERE entity2_id = ? AND label IN ('child', 'contains')
       LIMIT 1`,
      currentId,
    );

    if (!parentRel || visited.has(parentRel.entity1_id)) {
      return null; // ルートに到達できない
    }

    visited.add(parentRel.entity1_id);
    path.push(parentRel.entity1_id);
    currentId = parentRel.entity1_id;
  }

  return path;
}

// ========================================
// 全エンティティの階層適合チェック
// ========================================

export type OrphanEntity = {
  entity: EntityInfo;
  reason: "no_parent" | "parent_not_repository";
};

/**
 * 階層制約に適合しないエンティティ（孤児ノード）を検出
 * ルートレポジトリ自身は除外する
 */
export async function findOrphanEntities(): Promise<OrphanEntity[]> {
  const db = await getDb();
  const orphans: OrphanEntity[] = [];

  // 全エンティティを取得（ルートレポジトリ除外）
  const entities = await db.all<{ id: string; sys_tags: string }>(
    "SELECT id, sys_tags FROM entities WHERE id != ?",
    ROOT_REPOSITORY_ID,
  );

  for (const row of entities) {
    const sysTags: string[] = JSON.parse(row.sys_tags);
    const entityInfo: EntityInfo = { id: row.id, sysTags };

    // 親がいるかチェック
    const parentRel = await db.get<{ entity1_id: string }>(
      `SELECT entity1_id FROM relations
       WHERE entity2_id = ? AND label IN ('child', 'contains')
       LIMIT 1`,
      row.id,
    );

    if (!parentRel) {
      orphans.push({ entity: entityInfo, reason: "no_parent" });
      continue;
    }

    // レポジトリが祖先にあるかチェック
    const ancestorRepo = await findAncestorRepository(row.id);
    if (!ancestorRepo) {
      orphans.push({
        entity: entityInfo,
        reason: "parent_not_repository",
      });
    }
  }

  return orphans;
}
