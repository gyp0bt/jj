"use client";

import { Maximize2, Minimize2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { BodyPreviewModal } from "@/components/BodyPreviewModal";
import { BodyRenderer } from "@/components/BodyRenderer";
import type { StringEntity } from "@/lib/types";

type BodyPreviewTooltipProps = {
  text: string;
  className?: string;
  maxChars?: number;
  visible?: boolean;
  /** エンティティが渡された場合、フォーマット対応レンダリングを使用 */
  entity?: StringEntity;
  /** トリガー要素のrect（ポータル配置用） */
  triggerRect?: DOMRect | null;
  /** 4-A-02: クリックでモーダルを開く機能を有効化 */
  enableModal?: boolean;
};

function compactText(text: string, maxChars: number) {
  const trimmed = text.trim();
  if (trimmed.length <= maxChars) return trimmed;
  return `${trimmed.slice(0, maxChars)}...`;
}

/**
 * 4-A-02: ポータル化されたプレビューツールチップ
 * - コンポーネント境界を超えて表示可能
 * - クリックで大きなモーダルを開く機能あり
 * - プレビュー内スクロール対応
 * - マウス移動に追従するウィンドウ位置
 * - 折り畳みオン/オフボタン
 */
export function BodyPreviewTooltip({
  text,
  className = "",
  maxChars = 600,
  visible,
  entity,
  triggerRect,
  enableModal = false,
}: BodyPreviewTooltipProps) {
  const [showModal, setShowModal] = useState(false);
  const tooltipRef = useRef<HTMLDivElement>(null);
  const [position, setPosition] = useState({ top: 0, left: 0 });
  const [isMounted, setIsMounted] = useState(false);
  // 折り畳み状態: trueの場合コンパクト表示、falseの場合展開表示
  const [isCompact, setIsCompact] = useState(true);

  const preview = text.trim();
  if (!preview) return null;

  // クライアントサイドでのみマウント
  // biome-ignore lint/correctness/useHookAtTopLevel: conditional return after null check is safe
  useEffect(() => {
    setIsMounted(true);
  }, []);

  // ツールチップの位置を計算（triggerRect変更に追従 = マウス移動対応）
  // biome-ignore lint/correctness/useHookAtTopLevel: conditional return after null check is safe
  useEffect(() => {
    if (!triggerRect || !isMounted) return;

    const tooltipWidth = 320;
    const tooltipHeight = isCompact ? 200 : 400;
    const padding = 8;

    // デフォルト: トリガーの上に表示
    let top = triggerRect.top - tooltipHeight - padding;
    let left = triggerRect.left;

    // 上に収まらない場合は下に表示
    if (top < padding) {
      top = triggerRect.bottom + padding;
    }

    // 右端に収まらない場合は左に寄せる
    if (left + tooltipWidth > window.innerWidth - padding) {
      left = window.innerWidth - tooltipWidth - padding;
    }

    // 左端に収まらない場合
    if (left < padding) {
      left = padding;
    }

    setPosition({ top, left });
  }, [triggerRect, isMounted, isCompact]);

  const isVisible = typeof visible === "boolean" ? visible : false;

  const handleModalOpen = (e: React.MouseEvent) => {
    e.stopPropagation();
    if (entity && enableModal) {
      setShowModal(true);
    }
  };

  const handleToggleCompact = (e: React.MouseEvent) => {
    e.stopPropagation();
    setIsCompact((prev) => !prev);
  };

  // ツールチップ本体のコンテンツ
  const tooltipContent = (
    // biome-ignore lint/a11y/noStaticElementInteractions: tooltip with optional modal trigger
    <div
      ref={tooltipRef}
      className={`pointer-events-auto fixed z-40 w-80 max-w-[80vw] rounded-lg border border-gray-300 dark:border-gray-600 bg-white/95 dark:bg-neutral-900/95 shadow-lg transition-opacity duration-150 ${
        isVisible ? "opacity-100" : "opacity-0 pointer-events-none"
      } ${className}`}
      style={{
        top: triggerRect ? position.top : undefined,
        left: triggerRect ? position.left : undefined,
      }}
      onClick={handleModalOpen}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          handleModalOpen(e as unknown as React.MouseEvent);
        }
      }}
      role={enableModal ? "button" : undefined}
      tabIndex={enableModal ? 0 : undefined}
    >
      {/* ツールバー（拡大ボタン + 折り畳みボタン） */}
      {enableModal && entity && (
        <div className="absolute top-2 right-2 flex items-center gap-1 z-10">
          {/* 折り畳みオン/オフボタン */}
          <button
            type="button"
            onClick={handleToggleCompact}
            className="p-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
            title={isCompact ? "展開表示" : "コンパクト表示"}
          >
            {isCompact ? <Maximize2 size={12} /> : <Minimize2 size={12} />}
          </button>
          {/* モーダル拡大ボタン */}
          <button
            type="button"
            onClick={handleModalOpen}
            className="p-1.5 rounded-md bg-neutral-100 dark:bg-neutral-800 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-colors"
            title="モーダルで拡大表示"
          >
            <Maximize2 size={14} />
          </button>
        </div>
      )}

      {/* プレビュー本体（スクロール対応） */}
      <div
        className={`p-3 leading-relaxed text-xs text-neutral-700 dark:text-neutral-200 ${
          isCompact ? "max-h-48 overflow-y-auto" : "max-h-96 overflow-y-auto"
        }`}
      >
        {entity ? (
          <BodyRenderer entity={entity} maxLines={isCompact ? 15 : 50} />
        ) : (
          <pre className="whitespace-pre-wrap font-mono text-[11px]">
            {compactText(preview, isCompact ? maxChars : maxChars * 3)}
          </pre>
        )}
      </div>

      {/* クリックでモーダルを開くヒント */}
      {enableModal && entity && (
        <div className="px-3 py-1.5 border-t border-gray-200 dark:border-gray-700 text-[10px] text-neutral-400 text-center">
          クリックで拡大
        </div>
      )}
    </div>
  );

  // モーダル
  const modalContent = showModal && entity && (
    <BodyPreviewModal entity={entity} onClose={() => setShowModal(false)} />
  );

  // ポータル化（triggerRectが渡された場合のみ）
  if (triggerRect && isMounted) {
    return (
      <>
        {createPortal(tooltipContent, document.body)}
        {modalContent}
      </>
    );
  }

  // 従来の相対配置（後方互換性）
  const visibilityClass =
    typeof visible === "boolean"
      ? visible
        ? "opacity-100"
        : "opacity-0"
      : "opacity-0 group-hover:opacity-100";

  return (
    <>
      <div
        className={`pointer-events-none absolute z-20 w-80 max-w-[80vw] rounded-lg border border-gray-300 dark:border-gray-600 bg-white/95 dark:bg-neutral-900/95 p-3 text-xs text-neutral-700 dark:text-neutral-200 shadow-lg transition ${visibilityClass} ${className}`}
      >
        <div className="max-h-48 overflow-y-auto leading-relaxed">
          {entity ? (
            <BodyRenderer entity={entity} maxLines={15} />
          ) : (
            <pre className="whitespace-pre-wrap font-mono text-[11px]">
              {compactText(preview, maxChars)}
            </pre>
          )}
        </div>
      </div>
      {modalContent}
    </>
  );
}
