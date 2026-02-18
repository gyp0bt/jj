import neo4j, { type Driver, type Session } from "neo4j-driver";

let driver: Driver | null = null;

export type Neo4jConfig = {
  uri: string;
  user: string;
  password: string;
};

/** ランタイムオーバーライド設定（API経由で更新可能） */
let runtimeConfig: Neo4jConfig | null = null;

function getConfig(): Neo4jConfig {
  if (runtimeConfig) return runtimeConfig;
  return {
    uri: process.env.NEO4J_URI || "bolt://localhost:7687",
    user: process.env.NEO4J_USER || "neo4j",
    password: process.env.NEO4J_PASSWORD || "password",
  };
}

/** 現在の接続設定を取得（パスワードはマスク） */
export function getCurrentConfig(): { uri: string; user: string } {
  const config = getConfig();
  return { uri: config.uri, user: config.user };
}

/** ランタイム設定を更新し、既存ドライバをリセット */
export async function setRuntimeConfig(
  config: Neo4jConfig | null,
): Promise<void> {
  await closeDriver();
  runtimeConfig = config;
}

export function getDriver(): Driver {
  if (driver) return driver;
  const config = getConfig();
  driver = neo4j.driver(
    config.uri,
    neo4j.auth.basic(config.user, config.password),
  );
  return driver;
}

export function getSession(): Session {
  return getDriver().session();
}

export async function closeDriver(): Promise<void> {
  if (driver) {
    await driver.close();
    driver = null;
  }
}

export async function verifyConnection(): Promise<boolean> {
  const session = getSession();
  try {
    await session.run("RETURN 1");
    return true;
  } catch {
    return false;
  } finally {
    await session.close();
  }
}

/** 指定した設定で接続テストを行う（既存ドライバには影響しない） */
export async function testConnection(
  config: Neo4jConfig,
): Promise<{ ok: boolean; error?: string; serverInfo?: string }> {
  let testDriver: Driver | null = null;
  try {
    testDriver = neo4j.driver(
      config.uri,
      neo4j.auth.basic(config.user, config.password),
    );
    const session = testDriver.session();
    try {
      const result = await session.run(
        "CALL dbms.components() YIELD name, versions RETURN name, versions[0] AS version",
      );
      const record = result.records[0];
      const serverInfo = record
        ? `${record.get("name")} ${record.get("version")}`
        : "Connected";
      return { ok: true, serverInfo };
    } finally {
      await session.close();
    }
  } catch (err) {
    return {
      ok: false,
      error: err instanceof Error ? err.message : String(err),
    };
  } finally {
    if (testDriver) {
      await testDriver.close();
    }
  }
}
