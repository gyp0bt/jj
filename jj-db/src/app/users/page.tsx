"use client";
import { useRouter } from "next/navigation";
import { useEffect, useMemo, useState } from "react";
import { TopNav } from "@/components/TopNav";
import { useAuth } from "@/contexts/AuthContext";
import { fetchUsers } from "@/lib/user-api";

export default function UsersPage() {
  const router = useRouter();
  const { user, isLoading } = useAuth();
  const [users, setUsers] = useState<
    { id: string; username: string; displayName: string; role: string }[]
  >([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetchUsers().then((res) => {
      if (res.data) setUsers(res.data);
      setLoading(false);
    });
  }, [user]);

  const sortedUsers = useMemo(
    () => [...users].sort((a, b) => a.username.localeCompare(b.username)),
    [users],
  );

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
        title="ユーザー一覧"
        items={[{ label: "ユーザー", href: "/users" }]}
        className="mb-4"
      />
      {loading ? (
        <div className="text-center py-12 text-neutral-500">読み込み中...</div>
      ) : (
        <div className="rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-900/70">
          <div className="border-b border-neutral-200 dark:border-neutral-800 px-4 py-3 text-sm text-neutral-500">
            {sortedUsers.length} 人
          </div>
          <div className="overflow-x-auto">
            <table className="w-full text-sm">
              <thead className="bg-neutral-50 dark:bg-neutral-800/50 text-left text-neutral-600 dark:text-neutral-300">
                <tr>
                  <th className="px-4 py-2">ユーザー名</th>
                  <th className="px-4 py-2">表示名</th>
                  <th className="px-4 py-2">権限</th>
                  <th className="px-4 py-2">ID</th>
                </tr>
              </thead>
              <tbody>
                {sortedUsers.map((row) => (
                  <tr
                    key={row.id}
                    className="border-b border-neutral-100 dark:border-neutral-800"
                  >
                    <td className="px-4 py-3 font-medium text-neutral-900 dark:text-neutral-100">
                      {row.username}
                    </td>
                    <td className="px-4 py-3 text-neutral-600 dark:text-neutral-300">
                      {row.displayName || "-"}
                    </td>
                    <td className="px-4 py-3 text-neutral-600 dark:text-neutral-300">
                      {row.role}
                    </td>
                    <td className="px-4 py-3 text-xs text-neutral-500">
                      {row.id}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
