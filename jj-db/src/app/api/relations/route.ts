import crypto from "node:crypto";
import { NextResponse } from "next/server";
import { verifyToken } from "@/lib/auth";
import {
  createRelation,
  getAllRelations,
  getRelationsByEntityIds,
  getRelationsByLabel,
} from "@/lib/entity-repository";
import {
  HIERARCHY_RELATION_LABELS,
  validateHierarchyRelation,
} from "@/lib/hierarchy-validator";
import type { Relation } from "@/lib/types";

function getUserIdFromRequest(req: Request): string | null {
  const authHeader = req.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) return null;
  const token = authHeader.slice(7);
  const payload = verifyToken(token);
  return payload?.userId ?? null;
}

// GET /api/relations?label=xxx - ラベルで関連を取得
export async function GET(req: Request) {
  const userId = getUserIdFromRequest(req);
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { searchParams } = new URL(req.url);
  const label = searchParams.get("label");
  const entityIdsParam = searchParams.get("entityIds");

  if (entityIdsParam) {
    const entityIds = entityIdsParam.split(",").filter(Boolean);
    const relations = await getRelationsByEntityIds(entityIds);
    return NextResponse.json({ data: relations });
  }

  if (label) {
    const relations = await getRelationsByLabel(label);
    return NextResponse.json({ data: relations });
  }

  // ラベル・entityIds未指定時は全件取得
  const relations = await getAllRelations();
  return NextResponse.json({ data: relations });
}

// POST /api/relations - 新規関連を作成
export async function POST(req: Request) {
  const userId = getUserIdFromRequest(req);
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const body = await req.json();
  const { label, entity1Id, entity2Id } = body;

  if (!label || !entity1Id || !entity2Id) {
    return NextResponse.json(
      { error: "label, entity1Id, entity2Id are required" },
      { status: 400 },
    );
  }

  // 階層リレーション（child/contains）の場合はバリデーション実行
  if (HIERARCHY_RELATION_LABELS.has(label)) {
    const validation = await validateHierarchyRelation(
      entity1Id,
      entity2Id,
      label,
    );
    if (!validation.valid) {
      return NextResponse.json(
        { error: validation.error.message, code: validation.error.code },
        { status: 400 },
      );
    }
  }

  const now = new Date().toISOString();
  const relation: Relation = {
    id: crypto.randomUUID(),
    label,
    entity1Id,
    entity2Id,
    createdAt: now,
  };

  const created = await createRelation(relation);
  return NextResponse.json({ data: created }, { status: 201 });
}
