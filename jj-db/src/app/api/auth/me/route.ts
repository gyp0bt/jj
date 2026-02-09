import { NextResponse } from "next/server";
import { getAuthPayload, hashPassword, verifyPassword } from "@/lib/auth";
import {
  getUserById,
  getUserByUsername,
  updatePassword,
  updateUser,
} from "@/lib/user-repository";

export async function GET(request: Request) {
  try {
    const payload = getAuthPayload(request);
    if (!payload) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }

    const user = await getUserById(payload.userId);
    if (!user) {
      return NextResponse.json(
        { error: "ユーザーが見つかりません" },
        { status: 404 },
      );
    }

    return NextResponse.json({ user });
  } catch (error) {
    console.error("Get me error:", error);
    return NextResponse.json(
      { error: "ユーザー情報の取得中にエラーが発生しました" },
      { status: 500 },
    );
  }
}

export async function PATCH(request: Request) {
  try {
    const payload = getAuthPayload(request);
    if (!payload) {
      return NextResponse.json({ error: "認証が必要です" }, { status: 401 });
    }

    const body = await request.json();
    const { displayName, avatar, currentPassword, newPassword } = body;

    // パスワード変更の場合
    if (newPassword) {
      if (!currentPassword) {
        return NextResponse.json(
          { error: "現在のパスワードを入力してください" },
          { status: 400 },
        );
      }

      const userWithPassword = await getUserByUsername(payload.username);
      if (!userWithPassword) {
        return NextResponse.json(
          { error: "ユーザーが見つかりません" },
          { status: 404 },
        );
      }

      const isValid = await verifyPassword(
        currentPassword,
        userWithPassword.passwordHash,
      );
      if (!isValid) {
        return NextResponse.json(
          { error: "現在のパスワードが正しくありません" },
          { status: 400 },
        );
      }

      if (newPassword.length < 4) {
        return NextResponse.json(
          { error: "パスワードは4文字以上で入力してください" },
          { status: 400 },
        );
      }

      const hashedPassword = await hashPassword(newPassword);
      await updatePassword(payload.userId, hashedPassword);
    }

    // プロフィール更新（displayName, avatar）
    const updates: { displayName?: string; avatar?: string | null } = {};
    if (displayName !== undefined) {
      if (typeof displayName !== "string" || displayName.trim().length === 0) {
        return NextResponse.json(
          { error: "表示名を入力してください" },
          { status: 400 },
        );
      }
      updates.displayName = displayName.trim();
    }
    if (avatar !== undefined) {
      updates.avatar = avatar;
    }

    let user = await getUserById(payload.userId);
    if (!user) {
      return NextResponse.json(
        { error: "ユーザーが見つかりません" },
        { status: 404 },
      );
    }

    if (Object.keys(updates).length > 0) {
      user = await updateUser(payload.userId, updates);
    }

    return NextResponse.json({
      user,
      message: newPassword ? "パスワードを更新しました" : "更新しました",
    });
  } catch (error) {
    console.error("Update me error:", error);
    return NextResponse.json(
      { error: "更新中にエラーが発生しました" },
      { status: 500 },
    );
  }
}
