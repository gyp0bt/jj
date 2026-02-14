import { getDb } from "./db";

export type EntityCounts = {
  entityId: string;
  favoriteCount: number;
  goodCount: number;
  downloadCount: number;
};

export type FavoriteUser = {
  entityId: string;
  userId: string;
  username: string;
  displayName: string;
};

export async function getCountsForEntity(
  entityId: string,
): Promise<EntityCounts> {
  const db = await getDb();
  const favoriteCount = await db.get<{ count: number }>(
    "SELECT COUNT(*) as count FROM favorites WHERE entity_id = ?",
    entityId,
  );
  const downloadCount = await db.get<{ count: number }>(
    "SELECT COUNT(*) as count FROM downloads WHERE entity_id = ?",
    entityId,
  );
  const goodCount = await db.get<{ count: number }>(
    "SELECT COUNT(*) as count FROM goods WHERE entity_id = ?",
    entityId,
  );

  return {
    entityId,
    favoriteCount: favoriteCount?.count ?? 0,
    goodCount: goodCount?.count ?? 0,
    downloadCount: downloadCount?.count ?? 0,
  };
}

export async function getCountsForEntities(
  entityIds: string[],
): Promise<EntityCounts[]> {
  if (entityIds.length === 0) return [];
  const db = await getDb();
  const placeholders = entityIds.map(() => "?").join(", ");
  const favoriteRows = await db.all<{ entity_id: string; count: number }>(
    `SELECT entity_id, COUNT(*) as count FROM favorites WHERE entity_id IN (${placeholders}) GROUP BY entity_id`,
    ...entityIds,
  );
  const downloadRows = await db.all<{ entity_id: string; count: number }>(
    `SELECT entity_id, COUNT(*) as count FROM downloads WHERE entity_id IN (${placeholders}) GROUP BY entity_id`,
    ...entityIds,
  );
  const goodRows = await db.all<{ entity_id: string; count: number }>(
    `SELECT entity_id, COUNT(*) as count FROM goods WHERE entity_id IN (${placeholders}) GROUP BY entity_id`,
    ...entityIds,
  );

  const favoriteMap = new Map(
    favoriteRows.map((row) => [row.entity_id, row.count]),
  );
  const downloadMap = new Map(
    downloadRows.map((row) => [row.entity_id, row.count]),
  );
  const goodMap = new Map(goodRows.map((row) => [row.entity_id, row.count]));

  return entityIds.map((entityId) => ({
    entityId,
    favoriteCount: favoriteMap.get(entityId) ?? 0,
    goodCount: goodMap.get(entityId) ?? 0,
    downloadCount: downloadMap.get(entityId) ?? 0,
  }));
}

export async function isFavorite(
  userId: string,
  entityId: string,
): Promise<boolean> {
  const db = await getDb();
  const row = await db.get<{ marker: number }>(
    "SELECT 1 as marker FROM favorites WHERE user_id = ? AND entity_id = ?",
    userId,
    entityId,
  );
  return Boolean(row);
}

export async function toggleFavorite(
  userId: string,
  entityId: string,
): Promise<boolean> {
  const db = await getDb();
  const exists = await isFavorite(userId, entityId);
  if (exists) {
    await db.run(
      "DELETE FROM favorites WHERE user_id = ? AND entity_id = ?",
      userId,
      entityId,
    );
    return false;
  }
  await addFavorite(userId, entityId);
  return true;
}

export async function addFavorite(
  userId: string,
  entityId: string,
): Promise<void> {
  const db = await getDb();
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  await db.run(
    "INSERT OR IGNORE INTO favorites (id, user_id, entity_id, created_at) VALUES (?, ?, ?, ?)",
    id,
    userId,
    entityId,
    now,
  );
}

export async function getFavoriteUsersForEntities(
  entityIds: string[],
): Promise<FavoriteUser[]> {
  if (entityIds.length === 0) return [];
  const db = await getDb();
  const placeholders = entityIds.map(() => "?").join(", ");
  const rows = await db.all<{
    entity_id: string;
    user_id: string;
    username: string;
    display_name: string;
  }>(
    `
      SELECT
        f.entity_id as entity_id,
        u.id as user_id,
        u.username as username,
        u.display_name as display_name
      FROM favorites f
      JOIN users u ON u.id = f.user_id
      WHERE f.entity_id IN (${placeholders})
      ORDER BY f.created_at DESC
    `,
    ...entityIds,
  );

  return rows.map((row) => ({
    entityId: row.entity_id,
    userId: row.user_id,
    username: row.username,
    displayName: row.display_name,
  }));
}

export async function getFavoriteStatesForEntities(
  userId: string,
  entityIds: string[],
): Promise<string[]> {
  if (entityIds.length === 0) return [];
  const db = await getDb();
  const placeholders = entityIds.map(() => "?").join(", ");
  const rows = await db.all<{ entity_id: string }>(
    `
      SELECT entity_id
      FROM favorites
      WHERE user_id = ? AND entity_id IN (${placeholders})
    `,
    userId,
    ...entityIds,
  );

  return rows.map((row) => row.entity_id);
}

export async function addDownload(
  userId: string,
  entityId: string,
): Promise<void> {
  const db = await getDb();
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  await db.run(
    "INSERT INTO downloads (id, user_id, entity_id, created_at) VALUES (?, ?, ?, ?)",
    id,
    userId,
    entityId,
    now,
  );
}
