"use client";

import { Clock, RotateCcw, Search, X } from "lucide-react";
import { useEffect, useState } from "react";
import { fetchSearchHistory } from "@/lib/search-history-api";
import type { SearchHistory } from "@/lib/types";

type SearchHistoryPanelProps = {
  isOpen: boolean;
  onClose: () => void;
  onApply: (history: SearchHistory) => void;
};

export function SearchHistoryPanel({
  isOpen,
  onClose,
  onApply,
}: SearchHistoryPanelProps) {
  const [history, setHistory] = useState<SearchHistory[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!isOpen) return;
    setLoading(true);
    fetchSearchHistory(30).then((res) => {
      if (res.data) {
        setHistory(res.data);
      }
      setLoading(false);
    });
  }, [isOpen]);

  if (!isOpen) return null;

  const formatDate = (dateStr: string) => {
    const date = new Date(dateStr);
    const now = new Date();
    const diff = now.getTime() - date.getTime();
    const hours = Math.floor(diff / (1000 * 60 * 60));
    const minutes = Math.floor(diff / (1000 * 60));

    if (minutes < 1) return "たった今";
    if (minutes < 60) return `${minutes}分前`;
    if (hours < 24) return `${hours}時間前`;
    return date.toLocaleDateString("ja-JP", {
      month: "short",
      day: "numeric",
      hour: "2-digit",
      minute: "2-digit",
    });
  };

  const formatFilters = (filters: Record<string, unknown>) => {
    const parts: string[] = [];
    if (
      filters.tags &&
      Array.isArray(filters.tags) &&
      filters.tags.length > 0
    ) {
      parts.push(`タグ: ${filters.tags.join(", ")}`);
    }
    if (filters.domain && typeof filters.domain === "string") {
      parts.push(`ドメイン: ${filters.domain}`);
    }
    if (filters.entityType && typeof filters.entityType === "string") {
      parts.push(`タイプ: ${filters.entityType}`);
    }
    if (filters.createdBy && typeof filters.createdBy === "string") {
      parts.push("作成者でフィルタ");
    }
    if (filters.favoritedBy && typeof filters.favoritedBy === "string") {
      parts.push("お気に入りでフィルタ");
    }
    return parts.join(" / ");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-start justify-center pt-20 bg-black/50">
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-2xl max-h-[70vh] overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2">
            <Clock size={20} className="text-neutral-500" />
            <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">
              検索履歴
            </h2>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            aria-label="閉じる"
          >
            <X size={20} className="text-neutral-500" />
          </button>
        </div>

        <div className="overflow-y-auto max-h-[calc(70vh-64px)]">
          {loading ? (
            <div className="p-8 text-center text-neutral-500">
              読み込み中...
            </div>
          ) : history.length === 0 ? (
            <div className="p-8 text-center text-neutral-500">
              <Search size={40} className="mx-auto mb-3 opacity-50" />
              <p>検索履歴はありません</p>
            </div>
          ) : (
            <ul className="divide-y divide-neutral-100 dark:divide-neutral-800">
              {history.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => {
                      onApply(item);
                      onClose();
                    }}
                    className="w-full px-5 py-4 text-left hover:bg-neutral-50 dark:hover:bg-neutral-800/50 transition-colors group"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="flex-1 min-w-0">
                        <div className="flex items-center gap-2 mb-1">
                          <Search
                            size={14}
                            className="text-neutral-400 flex-shrink-0"
                          />
                          <span className="font-medium text-neutral-800 dark:text-neutral-100 truncate">
                            {item.query || "(キーワードなし)"}
                          </span>
                        </div>
                        {formatFilters(item.filters) && (
                          <p className="text-xs text-neutral-500 dark:text-neutral-400 truncate pl-5">
                            {formatFilters(item.filters)}
                          </p>
                        )}
                      </div>
                      <div className="flex items-center gap-3 flex-shrink-0">
                        <span className="text-xs text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
                          {item.resultCount}件
                        </span>
                        <span className="text-xs text-neutral-400 whitespace-nowrap">
                          {formatDate(item.createdAt)}
                        </span>
                        <RotateCcw
                          size={14}
                          className="text-neutral-400 opacity-0 group-hover:opacity-100 transition-opacity"
                        />
                      </div>
                    </div>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>
    </div>
  );
}
