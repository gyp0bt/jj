import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getCurrentDataSourceType } from "@/lib/datasource";
import {
  getNodeTypes,
  getProjects,
  searchNeo4j,
} from "@/lib/datasource/neo4j-search";

// GET /api/datasource/search - Neo4j全文検索
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }

    const dsType = getCurrentDataSourceType();
    if (dsType !== "neo4j") {
      return NextResponse.json(
        { error: "Neo4jデータソースが有効でありません" },
        { status: 400 },
      );
    }

    const { searchParams } = new URL(request.url);
    const query = searchParams.get("q") || "";
    const nodeType = searchParams.get("type") || undefined;
    const format = searchParams.get("format") || undefined;
    const project = searchParams.get("project") || undefined;
    const propertyKey = searchParams.get("propKey") || undefined;
    const propertyValue = searchParams.get("propValue") || undefined;
    const limit = Number(searchParams.get("limit")) || 100;
    const offset = Number(searchParams.get("offset")) || 0;

    const result = await searchNeo4j({
      query,
      nodeType,
      format,
      project,
      propertyKey,
      propertyValue,
      limit,
      offset,
    });

    return NextResponse.json(result);
  } catch (error) {
    console.error("GET /api/datasource/search error:", error);
    return NextResponse.json({ error: "検索に失敗しました" }, { status: 500 });
  }
}

// GET /api/datasource/search?meta=projects - メタデータ取得
// このルートはmeta queryパラメータで分岐
export async function POST(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }

    const dsType = getCurrentDataSourceType();
    if (dsType !== "neo4j") {
      return NextResponse.json(
        { error: "Neo4jデータソースが有効でありません" },
        { status: 400 },
      );
    }

    const body = await request.json();
    const { action } = body as { action: string };

    if (action === "projects") {
      const projects = await getProjects();
      return NextResponse.json({ projects });
    }
    if (action === "nodeTypes") {
      const nodeTypes = await getNodeTypes();
      return NextResponse.json({ nodeTypes });
    }

    return NextResponse.json(
      { error: `不明なaction: ${action}` },
      { status: 400 },
    );
  } catch (error) {
    console.error("POST /api/datasource/search error:", error);
    return NextResponse.json(
      { error: "メタデータの取得に失敗しました" },
      { status: 500 },
    );
  }
}
