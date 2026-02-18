/**
 * データソースファクトリ切替テスト（Node.js直接実行）
 *
 * 実行方法: npx tsx tests/test-datasource-factory.ts
 *
 * テスト内容:
 * - デフォルトはSQLite
 * - switchDataSource()でNeo4jに切替可能
 * - switchDataSource(null)で環境変数に戻る
 * - resetRepositories()でシングルトンがクリアされる
 * - getCurrentDataSourceType()が正しい値を返す
 *
 * Neo4jサーバー不要（インスタンス生成のみ、接続は行わない）
 */

import {
  getCurrentDataSourceType,
  getEntityRepository,
  getRelationRepository,
} from "../src/lib/datasource/factory";
import { resetRepositories, switchDataSource } from "../src/lib/datasource/factory";

let passed = 0;
let failed = 0;

function assert(condition: boolean, message: string): void {
  if (condition) {
    console.log(`  PASS: ${message}`);
    passed++;
  } else {
    console.error(`  FAIL: ${message}`);
    failed++;
  }
}

function test(name: string, fn: () => void | Promise<void>): void {
  console.log(`\n[TEST] ${name}`);
  try {
    const result = fn();
    if (result instanceof Promise) {
      result.catch((err) => {
        console.error(`  ERROR: ${err}`);
        failed++;
      });
    }
  } catch (err) {
    console.error(`  ERROR: ${err}`);
    failed++;
  }
}

// --- テスト開始 ---

test("デフォルトはSQLite", () => {
  resetRepositories();
  switchDataSource(null);
  // 環境変数DATA_SOURCEが未設定の場合、sqliteがデフォルト
  const dsType = getCurrentDataSourceType();
  assert(dsType === "sqlite", `getCurrentDataSourceType() === "sqlite" (got: "${dsType}")`);
});

test("getEntityRepository()はSQLite実装を返す", () => {
  resetRepositories();
  switchDataSource(null);
  const repo = getEntityRepository();
  assert(
    repo.constructor.name === "SqliteEntityRepository",
    `constructor.name === "SqliteEntityRepository" (got: "${repo.constructor.name}")`,
  );
});

test("getRelationRepository()はSQLite実装を返す", () => {
  resetRepositories();
  switchDataSource(null);
  const repo = getRelationRepository();
  assert(
    repo.constructor.name === "SqliteRelationRepository",
    `constructor.name === "SqliteRelationRepository" (got: "${repo.constructor.name}")`,
  );
});

test("switchDataSource('neo4j')でNeo4j実装に切替", () => {
  resetRepositories();
  switchDataSource("neo4j");
  const dsType = getCurrentDataSourceType();
  assert(dsType === "neo4j", `getCurrentDataSourceType() === "neo4j" (got: "${dsType}")`);

  const entityRepo = getEntityRepository();
  assert(
    entityRepo.constructor.name === "Neo4jEntityRepository",
    `entity constructor === "Neo4jEntityRepository" (got: "${entityRepo.constructor.name}")`,
  );

  const relationRepo = getRelationRepository();
  assert(
    relationRepo.constructor.name === "Neo4jRelationRepository",
    `relation constructor === "Neo4jRelationRepository" (got: "${relationRepo.constructor.name}")`,
  );
});

test("switchDataSource(null)で環境変数に戻る", () => {
  switchDataSource(null);
  const dsType = getCurrentDataSourceType();
  // 環境変数未設定なのでsqliteに戻るはず
  assert(dsType === "sqlite", `getCurrentDataSourceType() === "sqlite" (got: "${dsType}")`);
});

test("resetRepositories()でシングルトンがリセットされる", () => {
  switchDataSource(null);
  const repo1 = getEntityRepository();
  resetRepositories();
  const repo2 = getEntityRepository();
  // リセット後は新しいインスタンスが生成される
  assert(repo1 !== repo2, "リセット後に新しいインスタンスが生成される");
});

test("シングルトン: 同一のリポジトリインスタンスが返る", () => {
  resetRepositories();
  switchDataSource(null);
  const repo1 = getEntityRepository();
  const repo2 = getEntityRepository();
  assert(repo1 === repo2, "同一インスタンスが返る");
});

// --- 結果サマリ ---
setTimeout(() => {
  console.log(`\n${"=".repeat(40)}`);
  console.log(`結果: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}, 100);
