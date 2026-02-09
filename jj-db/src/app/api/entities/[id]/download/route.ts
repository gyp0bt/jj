import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { addDownload, getCountsForEntity } from "@/lib/entity-stats-repository";

type RouteParams = { params: Promise<{ id: string }> };

// POST /api/entities/[id]/download
export async function POST(request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;
    await addDownload(auth.userId, id);
    const stats = await getCountsForEntity(id);
    return NextResponse.json({ stats });
  } catch (error) {
    console.error("POST /api/entities/[id]/download error:", error);
    return NextResponse.json({ error: "更新に失敗しました" }, { status: 500 });
  }
}
