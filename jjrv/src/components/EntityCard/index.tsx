"use client";
import {
  BadgeCheck,
  Clipboard,
  Database,
  Download,
  Pencil,
  Star,
} from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { BodyPreviewTooltip } from "@/components/BodyPreviewTooltip";
import { BodyRenderer } from "@/components/BodyRenderer";
import { downloadEntity } from "@/lib/entity-export";
import {
  fetchFavoriteState,
  recordEntityDownload,
  toggleEntityFavorite,
} from "@/lib/entity-stats-api";
import type { StringEntity } from "@/lib/types";
import { chip, colorClasses } from "./style";

const TAG_WEIGHT_CACHE = new Map<string, number>();
export function tagWeight(tag: string) {
  // 最初は定数1、後でインデクサから差し替え可能
  const cached = TAG_WEIGHT_CACHE.get(tag);
  if (cached !== undefined) return cached;
  TAG_WEIGHT_CACHE.set(tag, 1);
  return 1;
}

export function accentFromSysTags(sysTags: string[]) {
  const s = sysTags.map((t) => t.toLowerCase());
  if (s.includes("repository")) return { color: "violet", emoji: "R" } as const;
  if (s.includes("abaqus") || s.includes("abaqus_inp"))
    return { color: "sky", emoji: "A" } as const;
  if (s.includes("material")) return { color: "teal", emoji: "◈" } as const;
  if (s.includes("doc") || s.includes("markdown"))
    return { color: "slate", emoji: "✎" } as const;
  return { color: "zinc", emoji: "•" } as const;
}

function autoSummary(e: StringEntity) {
  const remark = e.remark?.trim();
  if (remark) return remark;
  const lines = e.body.split(/\r?\n/);
  for (const raw of lines) {
    const l = raw.trim();
    if (!l || l.startsWith("**")) continue;
    if (/^\*material/i.test(l))
      return l.replace(/^\*/, "").replace(/,/g, " · ");
    if (!l.startsWith("*")) return l.slice(0, 120);
  }
  return "";
}

export function EntityCard({
  entity,
  onEdit,
  enableActions = true,
  className = "",
  onClick,
  clickLabel,
  meta,
  selected = false,
  favoriteState,
  onFavoriteChange,
}: {
  entity: StringEntity;
  onEdit?: (e: StringEntity) => void;
  enableActions?: boolean;
  className?: string;
  onClick?: () => void;
  clickLabel?: string;
  meta?: React.ReactNode;
  selected?: boolean;
  favoriteState?: boolean;
  onFavoriteChange?: (next: boolean) => void;
}) {
  const accent = accentFromSysTags(entity.sysTags);
  const cc = colorClasses(accent.color);
  const summary = autoSummary(entity);
  const hasActions = enableActions || Boolean(onEdit);

  const [favorite, setFavorite] = useState(favoriteState ?? false);
  const [copied, setCopied] = useState(false);
  const [copyHover, setCopyHover] = useState(false);
  const copyTimerRef = useRef<number | null>(null);

  useEffect(() => {
    if (favoriteState === undefined) return;
    setFavorite(favoriteState);
  }, [favoriteState]);

  useEffect(() => {
    let active = true;
    if (favoriteState !== undefined) {
      return () => {
        active = false;
      };
    }
    async function load() {
      const favRes = await fetchFavoriteState(entity.id);
      if (!active) return;
      if (favRes.data) {
        setFavorite(favRes.data.favorite);
        return;
      }
    }
    load();
    return () => {
      active = false;
    };
  }, [entity.id, favoriteState]);

  useEffect(
    () => () => {
      if (copyTimerRef.current) {
        window.clearTimeout(copyTimerRef.current);
      }
    },
    [],
  );

  return (
    <article
      className={`relative group rounded-2xl border p-4 shadow-sm bg-white/80 dark:bg-neutral-900/50 ${
        selected
          ? "border-pink-400 dark:border-pink-400 border-[3px]"
          : cc.border
      } ${className}`}
    >
      {onClick && (
        <button
          type="button"
          onClick={onClick}
          aria-label={clickLabel ?? entity.name}
          className="absolute inset-0 rounded-2xl focus:outline-none focus-visible:ring-2 focus-visible:ring-pink-400"
        />
      )}
      {copied && (
        <div className="absolute right-3 bottom-14 rounded-full bg-sky-600/90 text-white text-[11px] px-2 py-1 shadow-sm z-30">
          copied!
        </div>
      )}
      <div
        className={`absolute inset-y-0 left-0 rounded-l-2xl pointer-events-none ${
          selected ? "border-l-[6px] border-pink-400" : cc.left
        }`}
      />
      <div className="flex items-start gap-3 pr-20">
        <div
          className={`mt-0.5 inline-flex items-center justify-center h-6 w-6 rounded-md ${cc.bg} ${cc.text}`}
          title={entity.sysTags.join(" ")}
        >
          {accent.emoji}
        </div>
        <div className="flex-1 min-w-0">
          <h3
            className="font-semibold tracking-tight truncate"
            title={entity.name}
          >
            {entity.name}
          </h3>
          <div className="mt-1 flex flex-wrap items-center gap-1.5">
            {entity.userTags.map((t) => (
              <span
                key={`u-${t}`}
                className={`${chip} border-amber-300/80 bg-amber-50/70 text-amber-900`}
              >
                {t}
              </span>
            ))}
            {entity.sysTags.map((t) => (
              <span
                key={`s-${t}`}
                className={`${chip} ${cc.bg} ${cc.text} ${cc.border}`}
                title={`w=${tagWeight(t).toFixed(2)}`}
              >
                {t}
              </span>
            ))}
          </div>
        </div>
        {/* 右上: お気に入り・編集（常時表示） */}
        {hasActions && (
          <div className="absolute right-3 top-3 flex items-center gap-2">
            {enableActions && (
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  toggleEntityFavorite(entity.id).then((res) => {
                    if (!res.data) return;
                    setFavorite(res.data.favorite);
                    onFavoriteChange?.(res.data.favorite);
                  });
                }}
                className={`h-8 w-8 inline-flex items-center justify-center rounded-lg border ${
                  favorite
                    ? "border-rose-300 bg-rose-50 text-rose-600"
                    : "border-gray-300 dark:border-gray-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                }`}
                title="お気に入り"
                aria-pressed={favorite ? "true" : "false"}
              >
                <Star
                  size={16}
                  fill={favorite ? "currentColor" : "none"}
                  className={favorite ? "text-amber-500" : "text-neutral-400"}
                />
              </button>
            )}
            {onEdit && (
              <button
                type="button"
                onClick={() => onEdit(entity)}
                className="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
                title="編集"
              >
                <Pencil size={16} />
              </button>
            )}
          </div>
        )}
        {/* 右下: コピー・ダウンロード（hover時のみ表示） */}
        {enableActions && (
          <div className="absolute right-3 bottom-3 flex items-center gap-2 opacity-0 group-hover:opacity-100 transition-opacity">
            <div className="relative">
              <button
                type="button"
                onClick={(event) => {
                  event.stopPropagation();
                  navigator.clipboard.writeText(entity.body);
                  setCopied(true);
                  if (copyTimerRef.current) {
                    window.clearTimeout(copyTimerRef.current);
                  }
                  copyTimerRef.current = window.setTimeout(() => {
                    setCopied(false);
                  }, 1200);
                }}
                onMouseEnter={() => setCopyHover(true)}
                onMouseLeave={() => setCopyHover(false)}
                className="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white/90 dark:bg-neutral-900/90 hover:bg-neutral-100 dark:hover:bg-neutral-800 shadow-sm"
                title="コピー"
              >
                <Clipboard size={16} />
              </button>
              <BodyPreviewTooltip
                text={entity.body}
                entity={entity}
                visible={copyHover}
                className="absolute bottom-10 right-0"
              />
            </div>
            <button
              type="button"
              onClick={(event) => {
                event.stopPropagation();
                downloadEntity(entity);
                recordEntityDownload(entity.id).then((res) => {
                  if (!res.data) return;
                });
              }}
              className="h-8 w-8 inline-flex items-center justify-center rounded-lg border border-gray-300 dark:border-gray-600 bg-white/90 dark:bg-neutral-900/90 hover:bg-neutral-100 dark:hover:bg-neutral-800 shadow-sm"
              title="ダウンロード"
            >
              <Download size={16} />
            </button>
          </div>
        )}
      </div>
      <p className="mt-2 text-sm text-neutral-700 dark:text-neutral-300 line-clamp-2">
        {summary}
      </p>
      {/* ボディプレビュー（先頭3行をフォーマット対応で表示） */}
      {entity.body && (
        <div className="mt-2 rounded-lg bg-neutral-50 dark:bg-neutral-800/50 p-2 max-h-20 overflow-hidden text-[11px] leading-tight">
          <BodyRenderer entity={entity} maxLines={3} />
        </div>
      )}
      {meta && <div className="mt-3">{meta}</div>}
      <div className="mt-3 flex items-center gap-3 text-xs text-neutral-500">
        <span className="inline-flex items-center gap-1">
          <BadgeCheck size={14} /> 更新{" "}
          {new Date(entity.updatedAt).toLocaleDateString()}
        </span>
        {entity.sysProps?.extension && (
          <span className="inline-flex items-center gap-1">
            <Database size={14} /> .{entity.sysProps.extension}
          </span>
        )}
      </div>
    </article>
  );
}
