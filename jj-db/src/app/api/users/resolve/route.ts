import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getUsersByIds } from "@/lib/user-repository";

export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const { searchParams } = new URL(request.url);
    const ids = (searchParams.get("ids") ?? "")
      .split(",")
      .map((id) => id.trim())
      .filter(Boolean);

    const users = (await getUsersByIds(ids)).map((user) => ({
      id: user.id,
      username: user.username,
      displayName: user.displayName,
    }));

    return NextResponse.json({ users });
  } catch (error) {
    console.error("GET /api/users/resolve error:", error);
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}
