import { NextResponse } from "next/server";
import { getAuthPayload, hashPassword } from "@/lib/auth";
import { ensureUserNamespace } from "@/lib/user-namespace";
import { createUser, getUserByUsername } from "@/lib/user-repository";

type RegisterRequest = {
  username: string;
  password: string;
  displayName: string;
  role?: "admin" | "user";
};

export async function POST(request: Request) {
  try {
    // 管理者のみがユーザーを登録できる
    const payload = getAuthPayload(request);
    if (!payload || payload.role !== "admin") {
      return NextResponse.json(
        { error: "管理者権限が必要です" },
        { status: 403 },
      );
    }

    const body = (await request.json()) as RegisterRequest;

    if (!body.username || !body.password || !body.displayName) {
      return NextResponse.json(
        { error: "ユーザー名、パスワード、表示名を入力してください" },
        { status: 400 },
      );
    }

    if (body.password.length < 6) {
      return NextResponse.json(
        { error: "パスワードは6文字以上で入力してください" },
        { status: 400 },
      );
    }

    const existing = await getUserByUsername(body.username);
    if (existing) {
      return NextResponse.json(
        { error: "このユーザー名は既に使用されています" },
        { status: 409 },
      );
    }

    const passwordHash = await hashPassword(body.password);
    const id = crypto.randomUUID();
    const user = await createUser(
      id,
      body.username,
      passwordHash,
      body.displayName,
      body.role ?? "user",
    );

    // ユーザー名前空間を自動作成（root > user_namespace）
    await ensureUserNamespace(id, body.username, body.displayName);

    return NextResponse.json({ user }, { status: 201 });
  } catch (error) {
    console.error("Register error:", error);
    return NextResponse.json(
      { error: "ユーザー登録中にエラーが発生しました" },
      { status: 500 },
    );
  }
}
