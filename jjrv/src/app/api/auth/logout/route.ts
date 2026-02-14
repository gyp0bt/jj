import { NextResponse } from "next/server";

export async function POST() {
  // JWTはステートレスなので、サーバー側では特に何もしない
  // クライアント側でトークンを削除する
  return NextResponse.json({ success: true });
}
