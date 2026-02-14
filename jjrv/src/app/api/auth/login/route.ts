import { NextResponse } from "next/server";
import { generateToken, verifyPassword } from "@/lib/auth";
import { getUserByUsername } from "@/lib/user-repository";

type LoginRequest = {
  username: string;
  password: string;
};

export async function POST(request: Request) {
  try {
    const body = (await request.json()) as LoginRequest;

    if (!body.username || !body.password) {
      return NextResponse.json(
        { error: "ユーザー名とパスワードを入力してください" },
        { status: 400 },
      );
    }

    const user = await getUserByUsername(body.username);
    if (!user) {
      return NextResponse.json(
        { error: "ユーザー名またはパスワードが正しくありません" },
        { status: 401 },
      );
    }

    const isValid = await verifyPassword(body.password, user.passwordHash);
    if (!isValid) {
      return NextResponse.json(
        { error: "ユーザー名またはパスワードが正しくありません" },
        { status: 401 },
      );
    }

    const token = generateToken(user);

    return NextResponse.json({
      token,
      user: {
        id: user.id,
        username: user.username,
        displayName: user.displayName,
        role: user.role,
      },
    });
  } catch (error) {
    console.error("Login error:", error);
    return NextResponse.json(
      { error: "ログイン中にエラーが発生しました" },
      { status: 500 },
    );
  }
}
