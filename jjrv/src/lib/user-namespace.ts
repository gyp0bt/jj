/**
 * ユーザー名前空間管理
 *
 * GitHub同様、root > ユーザー > レポジトリ の階層構造を実現する。
 * ユーザー名前空間はユーザー登録時に自動作成され、
 * そのユーザーが作成するレポジトリの親となる。
 */

import { ROOT_REPOSITORY_ID, USER_NAMESPACE_TAG } from "./constants";
import { getDb } from "./db";
import type { StringEntity } from "./types";

/**
 * ユーザー名前空間のIDを生成
 * GitHub同様 username をそのままIDに使う
 */
export function getUserNamespaceId(username: string): string {
  return `user:${username}`;
}

/**
 * ユーザー名前空間を取得する
 * @returns 名前空間エンティティ、存在しなければ null
 */
export async function getUserNamespace(
  username: string,
): Promise<StringEntity | null> {
  const db = await getDb();
  const nsId = getUserNamespaceId(username);
  const row = await db.get<{
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
  }>("SELECT * FROM entities WHERE id = ?", nsId);
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    body: row.body,
    entityType: row.entity_type as StringEntity["entityType"],
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

/**
 * ユーザー名前空間を作成し、ルートレポジトリの子として登録する。
 * 既に存在する場合はそのまま返す。
 *
 * @param userId ユーザーID（created_by に設定）
 * @param username ユーザー名（名前空間のIDと名前に使用）
 * @param displayName ユーザー表示名
 */
export async function ensureUserNamespace(
  userId: string,
  username: string,
  displayName: string,
): Promise<StringEntity> {
  const existing = await getUserNamespace(username);
  if (existing) return existing;

  const db = await getDb();
  const now = new Date().toISOString();
  const nsId = getUserNamespaceId(username);

  const entity: StringEntity = {
    id: nsId,
    name: username,
    body: `[user_namespace] ${displayName} (${username})`,
    sysTags: [USER_NAMESPACE_TAG],
    userTags: [],
    sysProps: { owner_user_id: userId, owner_username: username },
    userProps: {},
    remark: `${displayName} のレポジトリ一覧`,
    domain: null,
    domainSource: null,
    domainConfidence: null,
    createdBy: userId,
    createdAt: now,
    updatedAt: now,
  };

  // エンティティ作成
  await db.run(
    `INSERT INTO entities (
      id, name, body, entity_type, sys_tags, user_tags, sys_props, user_props,
      remark, domain, domain_source, domain_confidence, created_by, created_at, updated_at
    ) VALUES (
      @id, @name, @body, @entity_type, @sys_tags, @user_tags, @sys_props, @user_props,
      @remark, @domain, @domain_source, @domain_confidence, @created_by, @created_at, @updated_at
    )`,
    {
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
    },
  );

  // ルートレポジトリの子として登録
  const relationId = `rel:root->${nsId}`;
  await db.run(
    `INSERT OR IGNORE INTO relations (id, label, entity1_id, entity2_id, created_at)
     VALUES (@id, @label, @entity1_id, @entity2_id, @created_at)`,
    {
      id: relationId,
      label: "child",
      entity1_id: ROOT_REPOSITORY_ID,
      entity2_id: nsId,
      created_at: now,
    },
  );

  return entity;
}

/**
 * 現在のユーザーの名前空間IDを取得するAPI向けヘルパー
 */
export async function findUserNamespaceByUserId(
  userId: string,
): Promise<StringEntity | null> {
  const db = await getDb();
  const row = await db.get<{
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
  }>(
    `SELECT * FROM entities WHERE sys_tags LIKE ? AND created_by = ? LIMIT 1`,
    `%${USER_NAMESPACE_TAG}%`,
    userId,
  );
  if (!row) return null;
  return {
    id: row.id,
    name: row.name,
    body: row.body,
    entityType: row.entity_type as StringEntity["entityType"],
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
