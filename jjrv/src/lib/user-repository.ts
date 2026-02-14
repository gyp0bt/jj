import { getDb } from "./db";
import type { User, UserWithPassword } from "./types";

type UserRow = {
  id: string;
  username: string;
  password_hash: string;
  display_name: string;
  avatar: string | null;
  role: string;
  created_at: string;
  updated_at: string;
};

function rowToUser(row: UserRow): User {
  return {
    id: row.id,
    username: row.username,
    displayName: row.display_name,
    avatar: row.avatar,
    role: row.role as "admin" | "user",
    createdAt: row.created_at,
    updatedAt: row.updated_at,
  };
}

function rowToUserWithPassword(row: UserRow): UserWithPassword {
  return {
    ...rowToUser(row),
    passwordHash: row.password_hash,
  };
}

export async function getAllUsers(): Promise<User[]> {
  const db = await getDb();
  const rows = await db.all<UserRow>(
    "SELECT * FROM users ORDER BY created_at DESC",
  );
  return rows.map(rowToUser);
}

export async function getUsersByIds(ids: string[]): Promise<User[]> {
  if (ids.length === 0) return [];
  const db = await getDb();
  const placeholders = ids.map(() => "?").join(", ");
  const rows = await db.all<UserRow>(
    `SELECT * FROM users WHERE id IN (${placeholders})`,
    ...ids,
  );
  return rows.map(rowToUser);
}

export async function getUserById(id: string): Promise<User | null> {
  const db = await getDb();
  const row = await db.get<UserRow>("SELECT * FROM users WHERE id = ?", id);
  return row ? rowToUser(row) : null;
}

export async function getUserByUsername(
  username: string,
): Promise<UserWithPassword | null> {
  const db = await getDb();
  const row = await db.get<UserRow>(
    "SELECT * FROM users WHERE username = ?",
    username,
  );
  return row ? rowToUserWithPassword(row) : null;
}

export async function createUser(
  id: string,
  username: string,
  passwordHash: string,
  displayName: string,
  role: "admin" | "user" = "user",
): Promise<User> {
  const db = await getDb();
  const now = new Date().toISOString();
  await db.run(
    `
    INSERT INTO users (id, username, password_hash, display_name, role, created_at, updated_at)
    VALUES (?, ?, ?, ?, ?, ?, ?)
  `,
    id,
    username,
    passwordHash,
    displayName,
    role,
    now,
    now,
  );
  return {
    id,
    username,
    displayName,
    role,
    createdAt: now,
    updatedAt: now,
  };
}

export async function updateUser(
  id: string,
  updates: Partial<{
    displayName: string;
    avatar: string | null;
    role: "admin" | "user";
  }>,
): Promise<User | null> {
  const db = await getDb();
  const existing = await getUserById(id);
  if (!existing) {
    return null;
  }

  const now = new Date().toISOString();
  const newDisplayName = updates.displayName ?? existing.displayName;
  const newAvatar =
    updates.avatar !== undefined ? updates.avatar : existing.avatar;
  const newRole = updates.role ?? existing.role;

  await db.run(
    `
    UPDATE users SET display_name = ?, avatar = ?, role = ?, updated_at = ? WHERE id = ?
  `,
    newDisplayName,
    newAvatar,
    newRole,
    now,
    id,
  );

  return {
    ...existing,
    displayName: newDisplayName,
    avatar: newAvatar,
    role: newRole,
    updatedAt: now,
  };
}

export async function updatePassword(
  id: string,
  passwordHash: string,
): Promise<boolean> {
  const db = await getDb();
  const now = new Date().toISOString();
  const result = await db.run(
    `UPDATE users SET password_hash = ?, updated_at = ? WHERE id = ?`,
    passwordHash,
    now,
    id,
  );
  return result.changes > 0;
}

export async function deleteUser(id: string): Promise<boolean> {
  const db = await getDb();
  const result = await db.run("DELETE FROM users WHERE id = ?", id);
  return result.changes > 0;
}

export async function getUserCount(): Promise<number> {
  const db = await getDb();
  const result = await db.get<{ count: number }>(
    "SELECT COUNT(*) as count FROM users",
  );
  return result?.count ?? 0;
}
