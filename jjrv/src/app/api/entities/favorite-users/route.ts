import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getFavoriteUsersForEntities } from "@/lib/entity-stats-repository";

export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { searchParams } = new URL(request.url);
    const ids = (searchParams.get("ids") ?? "")
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);

    const users = await getFavoriteUsersForEntities(ids);
    const usersByEntity: Record<
      string,
      { id: string; username: string; displayName: string }[]
    > = {};

    for (const row of users) {
      if (!usersByEntity[row.entityId]) {
        usersByEntity[row.entityId] = [];
      }
      usersByEntity[row.entityId].push({
        id: row.userId,
        username: row.username,
        displayName: row.displayName,
      });
    }

    return NextResponse.json({ usersByEntity });
  } catch (error) {
    console.error("GET /api/entities/favorite-users error:", error);
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}
