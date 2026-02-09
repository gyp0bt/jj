import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getCountsForEntities } from "@/lib/entity-stats-repository";

// GET /api/entities/stats?ids=a,b,c
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { searchParams } = new URL(request.url);
    const idsParam = searchParams.get("ids") ?? "";
    const ids = idsParam
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);
    const stats = await getCountsForEntities(ids);
    return NextResponse.json({ stats });
  } catch (error) {
    console.error("GET /api/entities/stats error:", error);
    return NextResponse.json(
      { error: "統計取得に失敗しました" },
      { status: 500 },
    );
  }
}
