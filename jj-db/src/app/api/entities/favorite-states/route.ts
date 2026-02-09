import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getFavoriteStatesForEntities } from "@/lib/entity-stats-repository";

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

    const favoriteIds = await getFavoriteStatesForEntities(auth.userId, ids);
    return NextResponse.json({ favoriteIds });
  } catch (error) {
    console.error("GET /api/entities/favorite-states error:", error);
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}
