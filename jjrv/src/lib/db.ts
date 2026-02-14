import fs from "node:fs";
import { createRequire } from "node:module";
import path from "node:path";
import initSqlJs from "sql.js";

const DB_PATH = path.join(process.cwd(), "data", "mat-db.sqlite");

type Params = unknown[] | Record<string, unknown> | undefined;

export type DbClient = {
  exec: (sql: string) => Promise<void>;
  run: (sql: string, ...params: unknown[]) => Promise<{ changes: number }>;
  get: <T>(sql: string, ...params: unknown[]) => Promise<T | undefined>;
  all: <T>(sql: string, ...params: unknown[]) => Promise<T[]>;
  close: () => Promise<void>;
};

let db: import("sql.js").Database | null = null;
let dbInitPromise: Promise<DbClient> | null = null;

function ensureDataDir(): void {
  const dataDir = path.dirname(DB_PATH);
  if (!fs.existsSync(dataDir)) {
    fs.mkdirSync(dataDir, { recursive: true });
  }
}

function normalizeNamedParams(
  value: Record<string, unknown>,
): Record<string, unknown> {
  const keys = Object.keys(value);
  if (keys.length === 0) return value;
  const hasPrefix = keys.some(
    (key) => key.startsWith(":") || key.startsWith("@") || key.startsWith("$"),
  );
  if (hasPrefix) return value;
  return Object.fromEntries(keys.map((key) => [`@${key}`, value[key]]));
}

function normalizeParams(params: unknown[]): Params {
  if (params.length === 0) return undefined;
  if (params.length === 1) {
    const first = params[0];
    if (first && typeof first === "object" && !Array.isArray(first)) {
      return normalizeNamedParams(first as Record<string, unknown>);
    }
    return [first];
  }
  return params;
}

function persist(current: import("sql.js").Database): void {
  const data = current.export();
  fs.writeFileSync(DB_PATH, Buffer.from(data));
}

function createClient(current: import("sql.js").Database): DbClient {
  return {
    exec: async (sql: string) => {
      current.exec(sql);
      persist(current);
    },
    run: async (sql: string, ...params: unknown[]) => {
      const stmt = current.prepare(sql);
      const bound = normalizeParams(params);
      if (bound !== undefined) {
        stmt.bind(bound as never);
      }
      stmt.run();
      stmt.free();
      const changes = current.getRowsModified();
      if (changes > 0) {
        persist(current);
      }
      return { changes };
    },
    get: async <T>(sql: string, ...params: unknown[]) => {
      const stmt = current.prepare(sql);
      const bound = normalizeParams(params);
      if (bound !== undefined) {
        stmt.bind(bound as never);
      }
      const hasRow = stmt.step();
      const row = hasRow ? (stmt.getAsObject() as T) : undefined;
      stmt.free();
      return row;
    },
    all: async <T>(sql: string, ...params: unknown[]) => {
      const stmt = current.prepare(sql);
      const bound = normalizeParams(params);
      if (bound !== undefined) {
        stmt.bind(bound as never);
      }
      const rows: T[] = [];
      while (stmt.step()) {
        rows.push(stmt.getAsObject() as T);
      }
      stmt.free();
      return rows;
    },
    close: async () => {
      current.close();
      db = null;
      dbInitPromise = null;
    },
  };
}

export async function getDb(): Promise<DbClient> {
  if (db) return createClient(db);
  if (dbInitPromise) return dbInitPromise;

  dbInitPromise = (async () => {
    ensureDataDir();

    const require = createRequire(import.meta.url);
    const wasmPath = require.resolve("sql.js/dist/sql-wasm.wasm");
    const SQL = await initSqlJs({
      locateFile: (file) => (file.endsWith(".wasm") ? wasmPath : file),
    });

    const data = fs.existsSync(DB_PATH) ? fs.readFileSync(DB_PATH) : undefined;
    const instance = data
      ? new SQL.Database(new Uint8Array(data))
      : new SQL.Database();

    const client = createClient(instance);
    await initSchema(client);
    await ensureRootRepo(client);
    db = instance;
    return client;
  })();

  return dbInitPromise;
}

async function initSchema(dbClient: DbClient): Promise<void> {
  // entities テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS entities (
      id TEXT PRIMARY KEY,
      name TEXT NOT NULL,
      body TEXT NOT NULL,
      sys_tags TEXT NOT NULL DEFAULT '[]',
      user_tags TEXT NOT NULL DEFAULT '[]',
      sys_props TEXT NOT NULL DEFAULT '{}',
      user_props TEXT NOT NULL DEFAULT '{}',
      remark TEXT,
      domain TEXT,
      domain_source TEXT,
      domain_confidence REAL,
      created_by TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_entities_name ON entities(name);
    CREATE INDEX IF NOT EXISTS idx_entities_domain ON entities(domain);
    CREATE INDEX IF NOT EXISTS idx_entities_updated_at ON entities(updated_at);
    CREATE INDEX IF NOT EXISTS idx_entities_created_by ON entities(created_by);
  `);

  // 既存テーブルへのカラム追加（マイグレーション）
  try {
    await dbClient.exec(`ALTER TABLE entities ADD COLUMN created_by TEXT`);
  } catch {
    // カラムが既に存在する場合は無視
  }

  // entity_type カラム追加
  try {
    await dbClient.exec(`ALTER TABLE entities ADD COLUMN entity_type TEXT`);
  } catch {
    // カラムが既に存在する場合は無視
  }

  // relations テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS relations (
      id TEXT PRIMARY KEY,
      label TEXT NOT NULL,
      entity1_id TEXT NOT NULL,
      entity2_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (entity1_id) REFERENCES entities(id) ON DELETE CASCADE,
      FOREIGN KEY (entity2_id) REFERENCES entities(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_relations_entity1_id ON relations(entity1_id);
    CREATE INDEX IF NOT EXISTS idx_relations_entity2_id ON relations(entity2_id);
    CREATE INDEX IF NOT EXISTS idx_relations_label ON relations(label);
  `);

  // users テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS users (
      id TEXT PRIMARY KEY,
      username TEXT NOT NULL UNIQUE,
      password_hash TEXT NOT NULL,
      display_name TEXT NOT NULL,
      avatar TEXT,
      role TEXT NOT NULL DEFAULT 'user',
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL
    );

    CREATE INDEX IF NOT EXISTS idx_users_username ON users(username);
  `);

  // avatar カラム追加（マイグレーション）
  try {
    await dbClient.exec(`ALTER TABLE users ADD COLUMN avatar TEXT`);
  } catch {
    // カラムが既に存在する場合は無視
  }

  // search_history テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS search_history (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      query TEXT NOT NULL,
      filters TEXT NOT NULL DEFAULT '{}',
      result_count INTEGER NOT NULL DEFAULT 0,
      created_at TEXT NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_search_history_user_id ON search_history(user_id);
    CREATE INDEX IF NOT EXISTS idx_search_history_created_at ON search_history(created_at);
  `);

  // favorites テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS favorites (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
      UNIQUE(user_id, entity_id)
    );

    CREATE INDEX IF NOT EXISTS idx_favorites_user_id ON favorites(user_id);
    CREATE INDEX IF NOT EXISTS idx_favorites_entity_id ON favorites(entity_id);
  `);

  // goods テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS goods (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
      UNIQUE(user_id, entity_id)
    );

    CREATE INDEX IF NOT EXISTS idx_goods_user_id ON goods(user_id);
    CREATE INDEX IF NOT EXISTS idx_goods_entity_id ON goods(entity_id);
  `);

  // downloads テーブル
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS downloads (
      id TEXT PRIMARY KEY,
      user_id TEXT NOT NULL,
      entity_id TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
      FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE
    );

    CREATE INDEX IF NOT EXISTS idx_downloads_user_id ON downloads(user_id);
    CREATE INDEX IF NOT EXISTS idx_downloads_entity_id ON downloads(entity_id);
  `);

  // documents テーブル（ドキュメント管理）
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      name TEXT NOT NULL,
      relative_path TEXT NOT NULL,
      mime_type TEXT,
      size INTEGER,
      description TEXT,
      created_by TEXT,
      created_at TEXT NOT NULL,
      updated_at TEXT NOT NULL,
      FOREIGN KEY (created_by) REFERENCES users(id) ON DELETE SET NULL
    );

    CREATE INDEX IF NOT EXISTS idx_documents_relative_path ON documents(relative_path);
    CREATE INDEX IF NOT EXISTS idx_documents_created_by ON documents(created_by);
  `);

  // entity_documents 中間テーブル（エンティティとドキュメントの関連）
  await dbClient.exec(`
    CREATE TABLE IF NOT EXISTS entity_documents (
      id INTEGER PRIMARY KEY AUTOINCREMENT,
      entity_id TEXT NOT NULL,
      document_id INTEGER NOT NULL,
      relative_path TEXT NOT NULL,
      created_at TEXT NOT NULL,
      FOREIGN KEY (entity_id) REFERENCES entities(id) ON DELETE CASCADE,
      FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE,
      UNIQUE(entity_id, document_id)
    );

    CREATE INDEX IF NOT EXISTS idx_entity_documents_entity_id ON entity_documents(entity_id);
    CREATE INDEX IF NOT EXISTS idx_entity_documents_document_id ON entity_documents(document_id);
  `);
}

/**
 * ルートレポジトリの自動作成 (spec-roadmap5: 5-01)
 * DB初期化時にルートレポジトリが存在しなければ作成する
 */
async function ensureRootRepo(dbClient: DbClient): Promise<void> {
  const ROOT_ID = "root";
  const existing = await dbClient.get<{ id: string }>(
    "SELECT id FROM entities WHERE id = ?",
    ROOT_ID,
  );
  if (existing) return;

  const now = new Date().toISOString();
  await dbClient.run(
    `INSERT INTO entities (
      id, name, body, entity_type, sys_tags, user_tags, sys_props, user_props,
      remark, domain, domain_source, domain_confidence, created_by, created_at, updated_at
    ) VALUES (
      @id, @name, @body, @entity_type, @sys_tags, @user_tags, @sys_props, @user_props,
      @remark, @domain, @domain_source, @domain_confidence, @created_by, @created_at, @updated_at
    )`,
    {
      id: ROOT_ID,
      name: "Root Repository",
      body: "[system] ルートレポジトリ — すべてのノードの起点",
      entity_type: null,
      sys_tags: '["repository"]',
      user_tags: "[]",
      sys_props: "{}",
      user_props: "{}",
      remark: null,
      domain: null,
      domain_source: null,
      domain_confidence: null,
      created_by: null,
      created_at: now,
      updated_at: now,
    },
  );
}

export async function closeDb(): Promise<void> {
  if (db) {
    db.close();
    db = null;
    dbInitPromise = null;
  }
}
