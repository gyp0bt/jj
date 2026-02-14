"use client";

import { Filter, X } from "lucide-react";
import { useCallback, useMemo, useState } from "react";
import { EntityCard } from "@/components/EntityCard";
import { EntityDiagram } from "@/components/EntityDiagram";
import { EntityGraph } from "@/components/EntityGraph";
import {
  type EntityMeta,
  EntityMetaBadges,
} from "@/components/EntityMetaBadges";
import { EntityTable } from "@/components/EntityTable";
import { ViewSwitcher, type ViewType } from "@/components/ViewSwitcher";
import type { StringEntity } from "@/lib/types";

type EntityGroupProps = {
  label: string;
  entities: StringEntity[];
  onEntityClick?: (entity: StringEntity) => void;
  metaById?: Record<string, EntityMeta>;
  selectedIds?: Set<string>;
  onToggleSelect?: (entityId: string) => void;
  selectionMode?: boolean;
  favoriteStateMap?: Record<string, boolean>;
  onFavoriteChange?: (entityId: string, next: boolean) => void;
  defaultView?: ViewType;
  className?: string;
  subgroups?: { label: string; entities: StringEntity[] }[];
  subgroupLabel?: string;
  /** グループ化に使用したプロパティキーのラベル（表示用） */
  propertyKeyLabel?: string;
  /** フィルター機能を有効にする（デフォルト: true） */
  enableFiltering?: boolean;
};

/**
 * 空白区切りキーワードで文字列をマッチ（AND条件）
 */
function matchesFilter(
  value: string | null | undefined,
  filter: string,
): boolean {
  if (!filter.trim()) return true;
  const keywords = filter.toLowerCase().split(/\s+/).filter(Boolean);
  const target = (value ?? "").toLowerCase();
  return keywords.every((kw) => target.includes(kw));
}

/**
 * クイックフィルターコンポーネント（カード・グラフビュー用）
 */
function QuickFilter({
  value,
  onChange,
  resultCount,
  totalCount,
}: {
  value: string;
  onChange: (value: string) => void;
  resultCount: number;
  totalCount: number;
}) {
  const [expanded, setExpanded] = useState(false);

  if (!expanded && !value) {
    return (
      <button
        type="button"
        onClick={() => setExpanded(true)}
        className="flex items-center gap-1 text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300 transition-colors"
        title="フィルターを開く"
      >
        <Filter size={14} />
        <span>絞り込み</span>
      </button>
    );
  }

  return (
    <div className="flex items-center gap-2">
      <div className="relative">
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder="名前・ドメイン・タグで絞り込み..."
          className="w-48 px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-sky-400 focus:border-sky-400"
        />
        {value && (
          <button
            type="button"
            onClick={() => onChange("")}
            className="absolute right-1 top-1/2 -translate-y-1/2 p-0.5 text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
          >
            <X size={12} />
          </button>
        )}
      </div>
      {value && (
        <span className="text-xs text-neutral-500">
          {resultCount}/{totalCount}
        </span>
      )}
      {!value && (
        <button
          type="button"
          onClick={() => setExpanded(false)}
          className="text-xs text-neutral-400 hover:text-neutral-600 dark:hover:text-neutral-200"
        >
          閉じる
        </button>
      )}
    </div>
  );
}

const LABEL_COLORS: Record<
  string,
  { bg: string; text: string; border: string }
> = {
  Material: { bg: "bg-sky-50", text: "text-sky-700", border: "border-sky-200" },
  Tag: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
  },
  Template: {
    bg: "bg-teal-50",
    text: "text-teal-700",
    border: "border-teal-200",
  },
  Document: {
    bg: "bg-slate-50",
    text: "text-slate-700",
    border: "border-slate-200",
  },
  related: {
    bg: "bg-violet-50",
    text: "text-violet-700",
    border: "border-violet-200",
  },
  tag: {
    bg: "bg-amber-50",
    text: "text-amber-700",
    border: "border-amber-200",
  },
};

function getLabelStyle(label: string) {
  return (
    LABEL_COLORS[label] || {
      bg: "bg-neutral-50",
      text: "text-neutral-700",
      border: "border-neutral-200",
    }
  );
}

export function EntityGroup({
  label,
  entities,
  onEntityClick,
  metaById,
  selectedIds,
  onToggleSelect,
  selectionMode = false,
  favoriteStateMap,
  onFavoriteChange,
  defaultView = "card",
  className = "",
  subgroups,
  subgroupLabel = "サブグループ",
  propertyKeyLabel,
  enableFiltering = true,
}: EntityGroupProps) {
  const [view, setView] = useState<ViewType>(defaultView);
  const [quickFilter, setQuickFilter] = useState("");
  const style = getLabelStyle(label);
  const displayLabel = propertyKeyLabel ? label : label;
  const resolvedSubgroups = (subgroups ?? []).filter(
    (group) => group.entities.length > 0,
  );
  const hasSubgroups = resolvedSubgroups.length > 0;
  const totalEntityCount = hasSubgroups
    ? resolvedSubgroups.reduce((sum, group) => sum + group.entities.length, 0)
    : entities.length;
  const viewOptions: ViewType[] = hasSubgroups
    ? ["card", "table", "diagram", "graph"]
    : ["card", "table", "graph"];

  // クイックフィルター適用（カード・グラフビュー用）
  const filterEntity = useCallback(
    (entity: StringEntity): boolean => {
      if (!quickFilter.trim()) return true;
      const allTags = [...entity.userTags, ...entity.sysTags].join(" ");
      const searchTarget = `${entity.name} ${entity.domain ?? ""} ${allTags}`;
      return matchesFilter(searchTarget, quickFilter);
    },
    [quickFilter],
  );

  const filteredEntities = useMemo(
    () => entities.filter(filterEntity),
    [entities, filterEntity],
  );

  const filteredSubgroups = useMemo(
    () =>
      resolvedSubgroups
        .map((group) => ({
          ...group,
          entities: group.entities.filter(filterEntity),
        }))
        .filter((group) => group.entities.length > 0),
    [resolvedSubgroups, filterEntity],
  );

  const filteredEntityCount = hasSubgroups
    ? filteredSubgroups.reduce((sum, group) => sum + group.entities.length, 0)
    : filteredEntities.length;

  // テーブルビューは自前のフィルター機能を使うのでクイックフィルターは無効
  const showQuickFilter = enableFiltering && view !== "table";

  if (totalEntityCount === 0) {
    return null;
  }

  return (
    <div
      className={`rounded-xl border ${style.border} ${style.bg} dark:bg-neutral-900/50 p-4 ${className}`}
    >
      <div className="flex items-center justify-between mb-4">
        <h3 className={`font-semibold ${style.text} flex items-center gap-2`}>
          {propertyKeyLabel && (
            <span className="text-xs font-normal text-neutral-500 bg-neutral-100 dark:bg-neutral-800 px-1.5 py-0.5 rounded">
              {propertyKeyLabel}
            </span>
          )}
          <span>{displayLabel}</span>
          <span className="text-sm font-normal text-neutral-500">
            ({quickFilter ? `${filteredEntityCount}/` : ""}
            {totalEntityCount}件)
          </span>
        </h3>
        <div className="flex items-center gap-3">
          {showQuickFilter && (
            <QuickFilter
              value={quickFilter}
              onChange={setQuickFilter}
              resultCount={filteredEntityCount}
              totalCount={totalEntityCount}
            />
          )}
          <ViewSwitcher
            value={view}
            onChange={setView}
            size="sm"
            views={viewOptions}
          />
        </div>
      </div>

      {view === "graph" ? (
        filteredEntities.length === 0 ? (
          <div className="py-8 text-center text-neutral-500 text-sm">
            フィルター条件に一致するデータがありません
          </div>
        ) : (
          <EntityGraph
            entities={filteredEntities}
            onNodeClick={onEntityClick}
            onToggleSelect={onToggleSelect}
            selectionMode={selectionMode}
            selectedIds={selectedIds}
            height={320}
          />
        )
      ) : view === "diagram" ? (
        <EntityDiagram
          entities={entities}
          onNodeClick={onEntityClick}
          onToggleSelect={onToggleSelect}
          selectionMode={selectionMode}
          selectedIds={selectedIds}
          height={320}
        />
      ) : view === "table" ? (
        <div className="space-y-4">
          {(hasSubgroups ? resolvedSubgroups : [{ label, entities }]).map(
            (group) => (
              <section key={group.label} className="space-y-2">
                {hasSubgroups && (
                  <div className="text-xs font-semibold text-neutral-600 flex items-center gap-2">
                    <span>{subgroupLabel}</span>
                    <span className="inline-flex items-center rounded-full bg-white/80 dark:bg-neutral-800 px-2 py-0.5 text-[11px]">
                      {group.label} ({group.entities.length}件)
                    </span>
                  </div>
                )}
                <EntityTable
                  entities={group.entities}
                  onRowClick={onEntityClick}
                  metaById={metaById}
                  selectedIds={selectionMode ? selectedIds : undefined}
                  onToggleSelect={selectionMode ? onToggleSelect : undefined}
                  selectionMode={selectionMode}
                  favoriteStateMap={favoriteStateMap}
                  onFavoriteChange={onFavoriteChange}
                  enableFiltering
                />
              </section>
            ),
          )}
        </div>
      ) : (
        <div className="space-y-4">
          {(hasSubgroups
            ? filteredSubgroups
            : [{ label, entities: filteredEntities }]
          ).map((group) => (
            <section key={group.label} className="space-y-3">
              {hasSubgroups && (
                <div className="text-xs font-semibold text-neutral-600 flex items-center gap-2">
                  <span>{subgroupLabel}</span>
                  <span className="inline-flex items-center rounded-full bg-white/80 dark:bg-neutral-800 px-2 py-0.5 text-[11px]">
                    {group.label} ({group.entities.length}件)
                  </span>
                </div>
              )}
              {group.entities.length === 0 ? (
                <div className="py-8 text-center text-neutral-500 text-sm">
                  フィルター条件に一致するデータがありません
                </div>
              ) : (
                <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                  {group.entities.map((entity) => (
                    <EntityCard
                      key={entity.id}
                      entity={entity}
                      className="h-full w-full"
                      onClick={() => {
                        if (selectionMode && onToggleSelect) {
                          onToggleSelect(entity.id);
                          return;
                        }
                        onEntityClick?.(entity);
                      }}
                      clickLabel={`${entity.name} を開く`}
                      selected={selectedIds?.has(entity.id)}
                      favoriteState={favoriteStateMap?.[entity.id]}
                      onFavoriteChange={(next) =>
                        onFavoriteChange?.(entity.id, next)
                      }
                      meta={
                        metaById?.[entity.id] ? (
                          <EntityMetaBadges
                            owner={metaById[entity.id].owner}
                            favorites={metaById[entity.id].favorites}
                            downloads={metaById[entity.id].downloads}
                            favoriteUsers={metaById[entity.id].favoriteUsers}
                            usedBy={metaById[entity.id].usedBy}
                            className="text-[11px]"
                          />
                        ) : undefined
                      }
                    />
                  ))}
                </div>
              )}
            </section>
          ))}
        </div>
      )}
    </div>
  );
}
