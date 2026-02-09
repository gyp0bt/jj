/**
 * ルートレポジトリ管理
 *
 * システムに唯一のルートレポジトリを提供し、
 * すべてのノードの階層ツリーの起点とする。
 */

import { ROOT_REPOSITORY_ID } from "./constants";
import { getDb } from "./db";
import type { StringEntity } from "./types";

export { ROOT_REPOSITORY_ID };

/** ルートレポジトリのデフォルト名 */
const ROOT_REPOSITORY_NAME = "Root Repository";

/**
 * ルートレポジトリを取得する。
 * 存在しなければ自動作成する。
 */
export async function ensureRootRepository(): Promise<StringEntity> {
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
  }>("SELECT * FROM entities WHERE id = ?", ROOT_REPOSITORY_ID);

  if (row) {
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

  // ルートレポジトリを作成
  const now = new Date().toISOString();
  const rootEntity: StringEntity = {
    id: ROOT_REPOSITORY_ID,
    name: ROOT_REPOSITORY_NAME,
    body: "[system] ルートレポジトリ — すべてのノードの起点",
    sysTags: ["repository"],
    userTags: [],
    sysProps: {},
    userProps: {},
    remark: null,
    domain: null,
    domainSource: null,
    domainConfidence: null,
    createdBy: null,
    createdAt: now,
    updatedAt: now,
  };

  await db.run(
    `INSERT INTO entities (
      id, name, body, entity_type, sys_tags, user_tags, sys_props, user_props,
      remark, domain, domain_source, domain_confidence, created_by, created_at, updated_at
    ) VALUES (
      @id, @name, @body, @entity_type, @sys_tags, @user_tags, @sys_props, @user_props,
      @remark, @domain, @domain_source, @domain_confidence, @created_by, @created_at, @updated_at
    )`,
    {
      id: rootEntity.id,
      name: rootEntity.name,
      body: rootEntity.body,
      entity_type: rootEntity.entityType ?? null,
      sys_tags: JSON.stringify(rootEntity.sysTags),
      user_tags: JSON.stringify(rootEntity.userTags),
      sys_props: JSON.stringify(rootEntity.sysProps),
      user_props: JSON.stringify(rootEntity.userProps),
      remark: rootEntity.remark ?? null,
      domain: rootEntity.domain ?? null,
      domain_source: rootEntity.domainSource ?? null,
      domain_confidence: rootEntity.domainConfidence ?? null,
      created_by: rootEntity.createdBy ?? null,
      created_at: rootEntity.createdAt,
      updated_at: rootEntity.updatedAt,
    },
  );

  return rootEntity;
}

/**
 * ルートレポジトリかどうかを判定
 */
export function isRootRepository(entityId: string): boolean {
  return entityId === ROOT_REPOSITORY_ID;
}
