import { NextResponse } from "next/server";
import { verifyToken } from "@/lib/auth";
import {
  getRelatedEntitiesGrouped,
  getRelationGraph,
  getRelationsByEntityId,
} from "@/lib/entity-repository";

function getUserIdFromRequest(req: Request): string | null {
  const authHeader = req.headers.get("Authorization");
  if (!authHeader?.startsWith("Bearer ")) return null;
  const token = authHeader.slice(7);
  const payload = verifyToken(token);
  return payload?.userId ?? null;
}

// GET /api/entities/[id]/relations - エンティティの関連を取得
export async function GET(
  req: Request,
  { params }: { params: Promise<{ id: string }> },
) {
  const userId = getUserIdFromRequest(req);
  if (!userId) {
    return NextResponse.json({ error: "Unauthorized" }, { status: 401 });
  }

  const { id } = await params;
  const { searchParams } = new URL(req.url);
  const grouped = searchParams.get("grouped") === "true";
  const graph = searchParams.get("graph") === "true";
  const maxDepth = Number(searchParams.get("maxDepth")) || 2;

  if (graph) {
    const graphData = await getRelationGraph(id, maxDepth);
    if (!graphData) {
      return NextResponse.json({ error: "Entity not found" }, { status: 404 });
    }
    return NextResponse.json({ data: graphData });
  }

  if (grouped) {
    const groups = await getRelatedEntitiesGrouped(id);
    return NextResponse.json({ data: groups });
  }

  const relations = await getRelationsByEntityId(id);
  return NextResponse.json({ data: relations });
}
