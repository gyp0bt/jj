"use client";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "@/contexts/AuthContext";

export default function Home() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-neutral-500">読み込み中...</div>
      </div>
    );
  }

  if (!user) {
    return null;
  }

  return (
    <main className="min-h-screen p-8 sm:p-12 font-sans">
      <div className="max-w-4xl mx-auto">
        <div className="text-center space-y-6">
          <h1 className="text-3xl font-semibold">材料物性データベース</h1>
          <p className="text-neutral-600 dark:text-neutral-400">
            CAE用材料物性データを登録・検索・管理するアプリケーション
          </p>
          <div className="flex items-center justify-center gap-3">
            <Link
              href="/search"
              className="rounded-xl border px-4 py-2 hover:bg-neutral-50 dark:hover:bg-neutral-900"
            >
              検索
            </Link>
            <Link
              href="/register"
              className="rounded-xl border px-4 py-2 bg-neutral-900 text-white"
            >
              取り込み
            </Link>
            <Link
              href="/users"
              className="rounded-xl border px-4 py-2 hover:bg-neutral-50 dark:hover:bg-neutral-900"
            >
              ユーザー一覧
            </Link>
          </div>
        </div>
      </div>
    </main>
  );
}
