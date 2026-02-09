import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  getCountsForEntity,
  isFavorite,
  toggleFavorite,
} from "@/lib/entity-stats-repository";

type RouteParams = { params: Promise<{ id: string }> };

// GET /api/entities/[id]/favorite
export async function GET(request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;
    const favorite = await isFavorite(auth.userId, id);
    const stats = await getCountsForEntity(id);
    return NextResponse.json({ favorite, stats });
  } catch (error) {
    console.error("GET /api/entities/[id]/favorite error:", error);
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}

// POST /api/entities/[id]/favorite
export async function POST(request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;
    const favorite = await toggleFavorite(auth.userId, id);
    const stats = await getCountsForEntity(id);
    return NextResponse.json({ favorite, stats });
  } catch (error) {
    console.error("POST /api/entities/[id]/favorite error:", error);
    return NextResponse.json({ error: "更新に失敗しました" }, { status: 500 });
  }
}
