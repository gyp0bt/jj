import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  getCurrentConfig,
  getCurrentDataSourceType,
  verifyConnection,
} from "@/lib/datasource";

// GET /api/datasource - 現在のデータソース設定とステータスを返す
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth || auth.role !== "admin") {
      return NextResponse.json(
        { error: "管理者権限が必要です" },
        { status: 403 },
      );
    }

    const dataSourceType = getCurrentDataSourceType();
    const neo4jConfig = getCurrentConfig();

    let neo4jConnected = false;
    if (dataSourceType === "neo4j") {
      neo4jConnected = await verifyConnection();
    }

    return NextResponse.json({
      dataSourceType,
      neo4j: {
        uri: neo4jConfig.uri,
        user: neo4jConfig.user,
        connected: neo4jConnected,
      },
    });
  } catch (error) {
    console.error("GET /api/datasource error:", error);
    return NextResponse.json(
      { error: "データソース情報の取得に失敗しました" },
      { status: 500 },
    );
  }
}
