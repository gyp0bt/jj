import { getDb } from "./db";
import type { SearchHistory } from "./types";

type SearchHistoryRow = {
  id: string;
  user_id: string;
  query: string;
  filters: string;
  result_count: number;
  created_at: string;
};

function rowToSearchHistory(row: SearchHistoryRow): SearchHistory {
  return {
    id: row.id,
    userId: row.user_id,
    query: row.query,
    filters: JSON.parse(row.filters),
    resultCount: row.result_count,
    createdAt: row.created_at,
  };
}

export async function addSearchHistory(
  history: Omit<SearchHistory, "id" | "createdAt">,
): Promise<SearchHistory> {
  const db = await getDb();
  const id = crypto.randomUUID();
  const now = new Date().toISOString();
  await db.run(
    `
    INSERT INTO search_history (
      id, user_id, query, filters, result_count, created_at
    ) VALUES (
      @id, @user_id, @query, @filters, @result_count, @created_at
    )
  `,
    {
      id,
      user_id: history.userId,
      query: history.query,
      filters: JSON.stringify(history.filters ?? {}),
      result_count: history.resultCount,
      created_at: now,
    },
  );
  return {
    id,
    userId: history.userId,
    query: history.query,
    filters: history.filters ?? {},
    resultCount: history.resultCount,
    createdAt: now,
  };
}

export async function getSearchHistoryByUser(
  userId: string,
  limit = 20,
): Promise<SearchHistory[]> {
  const db = await getDb();
  const rows = await db.all<SearchHistoryRow>(
    `SELECT * FROM search_history WHERE user_id = ? ORDER BY created_at DESC LIMIT ?`,
    userId,
    limit,
  );
  return rows.map(rowToSearchHistory);
}
