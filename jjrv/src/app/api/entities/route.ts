import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  createEntity,
  getAllEntities,
  getEntitiesByUser,
  getEntityCount,
  getEntityCountByUser,
  searchEntities,
  searchEntitiesByUser,
} from "@/lib/entity-repository";
import type { StringEntity } from "@/lib/types";

// GET /api/entities - エンティティ一覧取得
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const isAdmin = auth.role === "admin";
    const { searchParams } = new URL(request.url);
    const query = searchParams.get("q");

    if (query) {
      const entities = isAdmin
        ? await searchEntities(query)
        : await searchEntitiesByUser(query, auth.userId);
      return NextResponse.json({ entities, count: entities.length });
    }

    const entities = isAdmin
      ? await getAllEntities()
      : await getEntitiesByUser(auth.userId);
    const count = isAdmin
      ? await getEntityCount()
      : await getEntityCountByUser(auth.userId);
    return NextResponse.json({ entities, count });
  } catch (error) {
    console.error("GET /api/entities error:", error);
    return NextResponse.json(
      { error: "エンティティの取得に失敗しました" },
      { status: 500 },
    );
  }
}

// POST /api/entities - 新規エンティティ作成
export async function POST(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const body = (await request.json()) as StringEntity;

    // バリデーション
    if (!body.id || !body.name) {
      return NextResponse.json(
        { error: "id と name は必須です" },
        { status: 400 },
      );
    }

    const entity = await createEntity({ ...body, createdBy: auth.userId });
    return NextResponse.json({ entity }, { status: 201 });
  } catch (error) {
    console.error("POST /api/entities error:", error);
    return NextResponse.json(
      { error: "エンティティの作成に失敗しました" },
      { status: 500 },
    );
  }
}
