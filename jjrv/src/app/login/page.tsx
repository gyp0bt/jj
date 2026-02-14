"use client";

import { useRouter } from "next/navigation";
import { useEffect } from "react";
import LoginForm from "@/components/LoginForm";
import { useAuth } from "@/contexts/AuthContext";

export default function LoginPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();

  useEffect(() => {
    if (!isLoading && user) {
      router.replace("/");
    }
  }, [user, isLoading, router]);

  if (isLoading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-gray-500">読み込み中...</div>
      </div>
    );
  }

  if (user) {
    return null;
  }

  return (
    <div className="min-h-screen flex items-center justify-center bg-neutral-950">
      <div className="max-w-md w-full mx-4">
        <div className="bg-neutral-900 rounded-lg border border-neutral-800 p-8">
          <h1 className="text-2xl font-bold text-center text-neutral-100 mb-6">
            材料物性データベース
          </h1>
          <p className="text-center text-neutral-400 mb-6">
            ログインしてください
          </p>
          <LoginForm onSuccess={() => router.replace("/")} />
        </div>
      </div>
    </div>
  );
}
