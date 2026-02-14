import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  countOrphanEntities,
  migrateOrphansToRoot,
} from "@/lib/migration-hierarchy";

/**
 * GET /api/migration — 孤立ノード数を取得（ドライラン）
 */
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth || auth.role !== "admin") {
      return NextResponse.json(
        { error: "管理者権限が必要です" },
        { status: 403 },
      );
    }

    const orphanCount = await countOrphanEntities();
    return NextResponse.json({ orphanCount });
  } catch (error) {
    console.error("GET /api/migration error:", error);
    return NextResponse.json(
      { error: "マイグレーション情報の取得に失敗しました" },
      { status: 500 },
    );
  }
}

/**
 * POST /api/migration — 孤立ノードをルートレポジトリ配下に配置
 */
export async function POST(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth || auth.role !== "admin") {
      return NextResponse.json(
        { error: "管理者権限が必要です" },
        { status: 403 },
      );
    }

    const result = await migrateOrphansToRoot();
    return NextResponse.json({ result });
  } catch (error) {
    console.error("POST /api/migration error:", error);
    return NextResponse.json(
      { error: "マイグレーションの実行に失敗しました" },
      { status: 500 },
    );
  }
}
