"use client";

import { X } from "lucide-react";
import { useEffect, useRef } from "react";
import { createPortal } from "react-dom";
import { BodyRenderer } from "@/components/BodyRenderer";
import type { StringEntity } from "@/lib/types";

type BodyPreviewModalProps = {
  /** プレビュー対象のエンティティ */
  entity: StringEntity;
  /** モーダルを閉じるコールバック */
  onClose: () => void;
};

/**
 * 4-A-02: ボディプレビューモーダル
 * コンポーネント境界に関係なく、document.bodyにポータルで表示する
 * 大きなサイズでコンテンツを確認可能
 */
export function BodyPreviewModal({ entity, onClose }: BodyPreviewModalProps) {
  const modalRef = useRef<HTMLDivElement>(null);

  // ESCキーで閉じる
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [onClose]);

  // モーダル外クリックで閉じる（バックの要素へのイベント伝播を防止）
  const handleBackdropClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (modalRef.current && !modalRef.current.contains(e.target as Node)) {
      onClose();
    }
  };

  // フォーカストラップ
  useEffect(() => {
    const previousActiveElement = document.activeElement as HTMLElement;
    modalRef.current?.focus();
    return () => {
      previousActiveElement?.focus?.();
    };
  }, []);

  const content = (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm"
      onClick={handleBackdropClick}
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          onClose();
        }
      }}
      role="dialog"
      aria-modal="true"
    >
      <div
        ref={modalRef}
        className="relative w-[90vw] max-w-4xl h-[80vh] max-h-[800px] rounded-2xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-900 shadow-2xl flex flex-col overflow-hidden"
        role="dialog"
        aria-modal="true"
        aria-labelledby="preview-modal-title"
        tabIndex={-1}
      >
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-gray-200 dark:border-gray-700 bg-neutral-50 dark:bg-neutral-800/50">
          <div className="flex items-center gap-3 min-w-0">
            <h2
              id="preview-modal-title"
              className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 truncate"
            >
              {entity.name}
            </h2>
            {entity.domain && (
              <span className="px-2 py-0.5 text-xs rounded-full bg-sky-100 dark:bg-sky-900/50 text-sky-700 dark:text-sky-300">
                {entity.domain}
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={onClose}
            className="p-2 rounded-lg hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
            aria-label="閉じる"
          >
            <X size={20} />
          </button>
        </div>

        {/* コンテンツ */}
        <div className="flex-1 overflow-y-auto p-6">
          {entity.body ? (
            <BodyRenderer entity={entity} />
          ) : (
            <div className="text-neutral-500 text-center py-12">
              本文がありません
            </div>
          )}
        </div>

        {/* フッター（メタ情報） */}
        <div className="px-6 py-3 border-t border-gray-200 dark:border-gray-700 bg-neutral-50 dark:bg-neutral-800/50 text-xs text-neutral-500 flex items-center gap-4">
          <span>
            更新: {new Date(entity.updatedAt).toLocaleString("ja-JP")}
          </span>
          {entity.sysTags.length > 0 && (
            <span className="flex items-center gap-1">
              <span>タグ:</span>
              {entity.sysTags.slice(0, 3).map((tag) => (
                <span
                  key={tag}
                  className="px-1.5 py-0.5 rounded bg-neutral-200 dark:bg-neutral-700"
                >
                  {tag}
                </span>
              ))}
              {entity.sysTags.length > 3 && (
                <span>+{entity.sysTags.length - 3}</span>
              )}
            </span>
          )}
          <span className="ml-auto text-neutral-400">
            ESCまたは外側クリックで閉じる
          </span>
        </div>
      </div>
    </div>
  );

  // document.bodyにポータルでレンダリング
  if (typeof window === "undefined") return null;
  return createPortal(content, document.body);
}
