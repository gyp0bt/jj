import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { testConnection } from "@/lib/datasource";

// POST /api/datasource/test - Neo4j接続テスト
export async function POST(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth || auth.role !== "admin") {
      return NextResponse.json(
        { error: "管理者権限が必要です" },
        { status: 403 },
      );
    }

    const body = await request.json();
    const { uri, user, password } = body;

    if (!uri || !user || !password) {
      return NextResponse.json(
        { error: "uri, user, password は必須です" },
        { status: 400 },
      );
    }

    const result = await testConnection({ uri, user, password });

    return NextResponse.json(result);
  } catch (error) {
    console.error("POST /api/datasource/test error:", error);
    return NextResponse.json(
      { ok: false, error: "接続テストに失敗しました" },
      { status: 500 },
    );
  }
}
