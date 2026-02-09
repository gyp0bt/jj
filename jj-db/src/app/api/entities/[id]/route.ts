import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  deleteEntity,
  deleteEntityForUser,
  getEntityById,
  getEntityByIdForUser,
  updateEntity,
} from "@/lib/entity-repository";
import { isRootRepository } from "@/lib/root-repository";
import type { StringEntity } from "@/lib/types";

type RouteParams = { params: Promise<{ id: string }> };

// GET /api/entities/[id] - 単体取得
export async function GET(_request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(_request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;
    const entity =
      auth.role === "admin"
        ? await getEntityById(id)
        : await getEntityByIdForUser(id, auth.userId);

    if (!entity) {
      return NextResponse.json(
        { error: "エンティティが見つかりません" },
        { status: 404 },
      );
    }

    return NextResponse.json({ entity });
  } catch (error) {
    console.error("GET /api/entities/[id] error:", error);
    return NextResponse.json(
      { error: "エンティティの取得に失敗しました" },
      { status: 500 },
    );
  }
}

// PUT /api/entities/[id] - 更新
export async function PUT(request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;
    const body = (await request.json()) as StringEntity;

    // IDの整合性チェック
    if (body.id !== id) {
      return NextResponse.json({ error: "IDが一致しません" }, { status: 400 });
    }

    const existing =
      auth.role === "admin"
        ? await getEntityById(id)
        : await getEntityByIdForUser(id, auth.userId);
    if (!existing) {
      return NextResponse.json(
        { error: "エンティティが見つかりません" },
        { status: 404 },
      );
    }
    if (auth.role !== "admin" && existing.createdBy !== auth.userId) {
      return NextResponse.json({ error: "権限がありません" }, { status: 403 });
    }

    const entity = await updateEntity({
      ...body,
      createdBy: existing.createdBy,
    });
    return NextResponse.json({ entity });
  } catch (error) {
    console.error("PUT /api/entities/[id] error:", error);
    return NextResponse.json(
      { error: "エンティティの更新に失敗しました" },
      { status: 500 },
    );
  }
}

// DELETE /api/entities/[id] - 削除
export async function DELETE(_request: Request, { params }: RouteParams) {
  try {
    const auth = getAuthPayload(_request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { id } = await params;

    // ルートレポジトリは削除不可
    if (isRootRepository(id)) {
      return NextResponse.json(
        { error: "ルートレポジトリは削除できません" },
        { status: 403 },
      );
    }

    const deleted =
      auth.role === "admin"
        ? await deleteEntity(id)
        : await deleteEntityForUser(id, auth.userId);

    if (!deleted) {
      return NextResponse.json(
        { error: "エンティティが見つかりません" },
        { status: 404 },
      );
    }

    return NextResponse.json({ success: true });
  } catch (error) {
    console.error("DELETE /api/entities/[id] error:", error);
    return NextResponse.json(
      { error: "エンティティの削除に失敗しました" },
      { status: 500 },
    );
  }
}
