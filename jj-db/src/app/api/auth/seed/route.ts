import { NextResponse } from "next/server";
import { hashPassword } from "@/lib/auth";
import { ensureUserNamespace } from "@/lib/user-namespace";
import {
  createUser,
  getUserByUsername,
  getUserCount,
} from "@/lib/user-repository";

export async function GET() {
  try {
    const count = await getUserCount();
    return NextResponse.json({
      userCount: count,
      hasAdmin: (await getUserByUsername("admin")) !== null,
    });
  } catch (error) {
    console.error("Seed GET error:", error);
    return NextResponse.json(
      { error: "ユーザー状態の確認中にエラーが発生しました" },
      { status: 500 },
    );
  }
}

export async function POST() {
  try {
    // 既に管理者が存在する場合は作成しない
    const existing = await getUserByUsername("admin");
    if (existing) {
      return NextResponse.json(
        { error: "管理者ユーザーは既に存在します", user: null },
        { status: 409 },
      );
    }

    const passwordHash = await hashPassword("admin123");
    const id = crypto.randomUUID();
    const user = await createUser(id, "admin", passwordHash, "管理者", "admin");

    // adminのユーザー名前空間を自動作成
    await ensureUserNamespace(id, "admin", "管理者");

    return NextResponse.json(
      {
        message:
          "初期管理者を作成しました。パスワードは 'admin123' です。本番環境では必ず変更してください。",
        user,
      },
      { status: 201 },
    );
  } catch (error) {
    console.error("Seed POST error:", error);
    return NextResponse.json(
      { error: "初期管理者の作成中にエラーが発生しました" },
      { status: 500 },
    );
  }
}
