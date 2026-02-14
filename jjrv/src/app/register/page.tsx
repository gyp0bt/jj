"use client";
import { useRouter } from "next/navigation";
import { useEffect } from "react";
import { GenericUploader } from "@/components/GenericUploader";
import { TopNav } from "@/components/TopNav";
import { useAuth } from "@/contexts/AuthContext";

export default function RegisterPage() {
  const { user, isLoading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  if (isLoading || !user) {
    return (
      <div className="min-h-screen p-6 sm:p-10 font-sans">
        <div className="text-center py-12 text-neutral-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen p-6 sm:p-10 font-sans">
      <TopNav
        title="エンティティ取り込み"
        items={[{ label: "取り込み", href: "/register" }]}
        className="mb-4"
      />
      <GenericUploader />
    </div>
  );
}
