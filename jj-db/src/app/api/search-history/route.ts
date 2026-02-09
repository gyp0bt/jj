import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import {
  addSearchHistory,
  getSearchHistoryByUser,
} from "@/lib/search-history-repository";

// GET /api/search-history - 検索履歴取得
export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { searchParams } = new URL(request.url);
    const limit = Number(searchParams.get("limit") ?? "20");
    const history = await getSearchHistoryByUser(auth.userId, limit);
    return NextResponse.json({ history });
  } catch (error) {
    console.error("GET /api/search-history error:", error);
    return NextResponse.json(
      { error: "検索履歴の取得に失敗しました" },
      { status: 500 },
    );
  }
}

// POST /api/search-history - 検索履歴登録
export async function POST(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const body = (await request.json()) as {
      query?: string;
      filters?: Record<string, unknown>;
      resultCount?: number;
    };

    const history = await addSearchHistory({
      userId: auth.userId,
      query: body.query ?? "",
      filters: body.filters ?? {},
      resultCount: body.resultCount ?? 0,
    });

    return NextResponse.json({ history }, { status: 201 });
  } catch (error) {
    console.error("POST /api/search-history error:", error);
    return NextResponse.json(
      { error: "検索履歴の登録に失敗しました" },
      { status: 500 },
    );
  }
}
