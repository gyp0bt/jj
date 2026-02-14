"use client";
import { Filter, SlidersHorizontal } from "lucide-react";
import { useId } from "react";

type SearchFilterProps = {
  sortBy: "created" | "updated" | "name" | "favoriteCount" | "downloadCount";
  sortOrder: "asc" | "desc";
  onSortChange: (
    sortBy: "created" | "updated" | "name" | "favoriteCount" | "downloadCount",
    sortOrder: "asc" | "desc",
  ) => void;
  createdBy: string;
  onCreatedByChange: (userId: string) => void;
  favoritedBy: string;
  onFavoritedByChange: (userId: string) => void;
  availableUsers?: { id: string; username: string }[];
  className?: string;
};

export function SearchFilter({
  sortBy,
  sortOrder,
  onSortChange,
  createdBy,
  onCreatedByChange,
  favoritedBy,
  onFavoritedByChange,
  availableUsers = [],
  className = "",
}: SearchFilterProps) {
  const sortSelectId = useId();
  const createdBySelectId = useId();
  const favoritedBySelectId = useId();

  return (
    <div
      className={`w-full rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/70 px-3 py-2 ${className}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex items-center gap-2 text-xs font-semibold text-neutral-700 dark:text-neutral-200">
          <Filter size={14} />
          フィルタ
        </div>
        <label
          htmlFor={sortSelectId}
          className="flex items-center gap-1 text-xs text-neutral-600 dark:text-neutral-300"
        >
          <SlidersHorizontal size={12} />
          並び替え
        </label>
        <select
          id={sortSelectId}
          value={sortBy}
          onChange={(e) =>
            onSortChange(
              e.target.value as
                | "created"
                | "updated"
                | "name"
                | "favoriteCount"
                | "downloadCount",
              sortOrder,
            )
          }
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
        >
          <option value="updated">更新日時</option>
          <option value="created">作成日時</option>
          <option value="name">名前</option>
          <option value="favoriteCount">お気に入り数</option>
          <option value="downloadCount">ダウンロード数</option>
        </select>
        <button
          type="button"
          onClick={() =>
            onSortChange(sortBy, sortOrder === "asc" ? "desc" : "asc")
          }
          className="whitespace-nowrap rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 text-xs font-medium hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
        >
          {sortOrder === "asc" ? "昇順 ↑" : "降順 ↓"}
        </button>
        <label
          htmlFor={createdBySelectId}
          className="flex items-center gap-1 text-xs text-neutral-600 dark:text-neutral-300"
        >
          登録ユーザー
        </label>
        <select
          id={createdBySelectId}
          value={createdBy}
          onChange={(e) => onCreatedByChange(e.target.value)}
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
        >
          <option value="">すべて</option>
          {availableUsers.map((user) => (
            <option key={user.id} value={user.id}>
              {user.username}
            </option>
          ))}
        </select>
        <label
          htmlFor={favoritedBySelectId}
          className="flex items-center gap-1 text-xs text-neutral-600 dark:text-neutral-300"
        >
          お気に入りユーザー
        </label>
        <select
          id={favoritedBySelectId}
          value={favoritedBy}
          onChange={(e) => onFavoritedByChange(e.target.value)}
          className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
        >
          <option value="">すべて</option>
          {availableUsers.map((user) => (
            <option key={user.id} value={user.id}>
              {user.username}
            </option>
          ))}
        </select>
      </div>
    </div>
  );
}
