import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import type { DataSourceType } from "@/lib/datasource";
import {
  getCurrentDataSourceType,
  setRuntimeConfig,
  switchDataSource,
  verifyConnection,
} from "@/lib/datasource";

// POST /api/datasource/switch - データソース切替
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
    const { dataSourceType, neo4jConfig } = body as {
      dataSourceType: DataSourceType;
      neo4jConfig?: { uri: string; user: string; password: string };
    };

    if (dataSourceType !== "sqlite" && dataSourceType !== "neo4j") {
      return NextResponse.json(
        {
          error: 'dataSourceType は "sqlite" または "neo4j" を指定してください',
        },
        { status: 400 },
      );
    }

    if (dataSourceType === "neo4j") {
      // Neo4j切替時: 接続設定を更新してから切替
      if (neo4jConfig) {
        await setRuntimeConfig({
          uri: neo4jConfig.uri,
          user: neo4jConfig.user,
          password: neo4jConfig.password,
        });
      }

      // 接続確認
      const connected = await verifyConnection();
      if (!connected) {
        // 切替せず元に戻す
        return NextResponse.json(
          {
            error: "Neo4jへの接続に失敗しました。接続設定を確認してください。",
          },
          { status: 400 },
        );
      }
    } else {
      // SQLite切替時: Neo4jランタイム設定をクリア
      await setRuntimeConfig(null);
    }

    switchDataSource(dataSourceType);

    return NextResponse.json({
      dataSourceType: getCurrentDataSourceType(),
      message: `データソースを ${dataSourceType} に切り替えました`,
    });
  } catch (error) {
    console.error("POST /api/datasource/switch error:", error);
    return NextResponse.json(
      { error: "データソースの切替に失敗しました" },
      { status: 500 },
    );
  }
}
