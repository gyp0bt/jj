/**
 * Neo4jドライバ設定テスト（Node.js直接実行）
 *
 * 実行方法: npx tsx tests/test-neo4j-driver.ts
 *
 * テスト内容:
 * - getCurrentConfig()がデフォルト設定を返す
 * - setRuntimeConfig()で設定を上書きできる
 * - testConnection()が接続不可時にエラーを返す
 *
 * Neo4jサーバー不要のテストのみ（接続テストはtimeout想定）
 */

import {
  closeDriver,
  getCurrentConfig,
  setRuntimeConfig,
  testConnection,
} from "../src/lib/datasource/neo4j-driver";

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

async function test(
  name: string,
  fn: () => void | Promise<void>,
): Promise<void> {
  console.log(`\n[TEST] ${name}`);
  try {
    await fn();
  } catch (err) {
    console.error(`  ERROR: ${err}`);
    failed++;
  }
}

async function main() {
  await test("getCurrentConfig()のデフォルト値", () => {
    const config = getCurrentConfig();
    assert(config.uri === "bolt://localhost:7687", `uri === "bolt://localhost:7687" (got: "${config.uri}")`);
    assert(config.user === "neo4j", `user === "neo4j" (got: "${config.user}")`);
  });

  await test("setRuntimeConfig()で設定を上書き", async () => {
    await setRuntimeConfig({
      uri: "bolt://custom-host:7688",
      user: "testuser",
      password: "testpass",
    });

    const config = getCurrentConfig();
    assert(
      config.uri === "bolt://custom-host:7688",
      `uri === "bolt://custom-host:7688" (got: "${config.uri}")`,
    );
    assert(config.user === "testuser", `user === "testuser" (got: "${config.user}")`);
  });

  await test("setRuntimeConfig(null)でデフォルトに戻る", async () => {
    await setRuntimeConfig(null);
    const config = getCurrentConfig();
    assert(config.uri === "bolt://localhost:7687", `uri === "bolt://localhost:7687" (got: "${config.uri}")`);
  });

  await test("testConnection()が接続不可時にエラーを返す", async () => {
    // 存在しないホストへの接続テスト（タイムアウトするので短いURIを使用）
    const result = await testConnection({
      uri: "bolt://127.0.0.1:19999",
      user: "neo4j",
      password: "wrong",
    });
    assert(result.ok === false, `ok === false (got: ${result.ok})`);
    assert(typeof result.error === "string", `error is string (got: ${typeof result.error})`);
  });

  // クリーンアップ
  await closeDriver();

  console.log(`\n${"=".repeat(40)}`);
  console.log(`結果: ${passed} passed, ${failed} failed`);
  process.exit(failed > 0 ? 1 : 0);
}

main();
