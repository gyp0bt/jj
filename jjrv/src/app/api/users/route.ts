import { NextResponse } from "next/server";
import { getAuthPayload } from "@/lib/auth";
import { getAllUsers } from "@/lib/user-repository";

export async function GET(request: Request) {
  try {
    const auth = getAuthPayload(request);
    if (!auth) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }
    const users = (await getAllUsers()).map((user) => ({
      id: user.id,
      username: user.username,
      displayName: user.displayName,
      role: user.role,
    }));
    return NextResponse.json({ users });
  } catch (error) {
    console.error("GET /api/users error:", error);
    return NextResponse.json({ error: "取得に失敗しました" }, { status: 500 });
  }
}
