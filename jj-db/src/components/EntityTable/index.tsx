"use client";

import {
  ArrowDown,
  ArrowUp,
  Check,
  ChevronDown,
  ChevronRight,
  ChevronUp,
  Clipboard,
  Download,
  Eye,
  FileText,
  FolderClosed,
  FolderOpen,
  GitBranch,
  Link2,
  Pencil,
  SlidersHorizontal,
  Star,
  X,
} from "lucide-react";
import { useEffect, useMemo, useRef, useState } from "react";
import { BodyPreviewModal } from "@/components/BodyPreviewModal";
import { BodyPreviewTooltip } from "@/components/BodyPreviewTooltip";
import { accentFromSysTags } from "@/components/EntityCard";
import { chip, colorClasses } from "@/components/EntityCard/style";
import { EntityEditPanel } from "@/components/EntityEditPanel";
import {
  type EntityMeta,
  EntityMetaBadges,
} from "@/components/EntityMetaBadges";
import {
  applySearchFilters,
  type FilterCondition,
  FullTextSearchBar,
  loadSavedFilters,
  type SavedFilter,
  saveSavedFilters,
} from "@/components/SearchBar";
import {
  fetchFavoriteState,
  recordEntityDownload,
  toggleEntityFavorite,
} from "@/lib/entity-stats-api";
import type { Relation, StringEntity } from "@/lib/types";

type SortColumn =
  | "name"
  | "domain"
  | "tags"
  | "updatedAt"
  | `prop:${string}`
  | `rel:${string}`
  | null;
type SortDirection = "asc" | "desc";

/** 4-A-04: マルチセル選択のためのセル識別子 */
type CellId = {
  entityId: string;
  column: "domain" | "body" | `prop:${string}` | `tag:${string}`;
};

/** 階層構造を持つエンティティ行の型 */
type HierarchicalEntity = {
  entity: StringEntity;
  depth: number;
  hasChildren: boolean;
  parentId: string | null;
};

/** 階層ラベル（これらのRelationラベルは階層関係を示す） */
const HIERARCHY_LABELS = new Set([
  "child",
  "contains",
  "parent_of",
  "belongs_to",
]);

type ColumnFilters = {
  name: string;
  domain: string;
  tags: string;
};

type EntityTableProps = {
  entities: StringEntity[];
  onRowClick?: (entity: StringEntity) => void;
  metaById?: Record<string, EntityMeta>;
  selectedIds?: Set<string>;
  onToggleSelect?: (entityId: string) => void;
  onToggleSelectAll?: (next: boolean) => void;
  selectionMode?: boolean;
  favoriteStateMap?: Record<string, boolean>;
  onFavoriteChange?: (entityId: string, next: boolean) => void;
  /** フィルター・ソート機能を有効にする（デフォルト: false） */
  enableFiltering?: boolean;
  /** 編集モード: 行クリックでインライン編集パネルを展開 */
  editable?: boolean;
  /** 編集モードでエンティティが変更された時のコールバック */
  onEntityChange?: (entity: StringEntity) => void;
  /** 現在編集中のエンティティID */
  editingEntityId?: string | null;
  /** 編集対象エンティティが選択/解除された時のコールバック */
  onEditEntity?: (entity: StringEntity | null) => void;
  /** Relation一覧（テーブルにrelation列を表示する際に使用） */
  relations?: Relation[];
  /** 全エンティティ（relation先のnameを解決するために使用） */
  allEntities?: StringEntity[];
  /** Relation変更コールバック */
  onRelationsChange?: (relations: Relation[]) => void;
  /** 4-A-01: 階層表示を有効にする（child/containsのRelationでツリー表示） */
  enableHierarchy?: boolean;
  /** 4-A-03: 全文検索バーを有効にする（デフォルト: false） */
  enableFullTextSearch?: boolean;
  /** 4-A-04: Body列を表示する（ダブルクリックでインライン編集） */
  enableBodyColumn?: boolean;
  /** 4-A-04: マルチセル選択を有効にする（Ctrl+クリックで複数セル選択、一括編集） */
  enableMultiCellSelect?: boolean;
  /** タグクリック時のコールバック（検索ページへの遷移等） */
  onTagClick?: (tag: string) => void;
  /** Relation先エンティティクリック時のコールバック（詳細ビューへの遷移等） */
  onRelationClick?: (entity: StringEntity) => void;
};

function formatDate(dateStr: string) {
  const d = new Date(dateStr);
  return d.toLocaleDateString("ja-JP", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

function TableRow({
  entity,
  onRowClick,
  meta,
  selected,
  onToggleSelect,
  selectionMode = false,
  favoriteState,
  onFavoriteChange,
  relations,
  allEntities,
  relationLabels,
  propertyKeys,
  onEntityChange,
  onRelationsChange,
  // 4-A-01: 階層表示用props
  hierarchyDepth,
  hierarchyHasChildren,
  hierarchyCollapsed,
  onToggleCollapse,
  onTagClick,
  onRelationClick,
}: {
  entity: StringEntity;
  onRowClick?: (entity: StringEntity) => void;
  meta?: EntityMeta;
  selected?: boolean;
  onToggleSelect?: (entityId: string) => void;
  selectionMode?: boolean;
  favoriteState?: boolean;
  onFavoriteChange?: (next: boolean) => void;
  relations?: Relation[];
  allEntities?: StringEntity[];
  relationLabels?: string[];
  propertyKeys?: string[];
  /** 2-22: インラインセル編集コールバック */
  onEntityChange?: (entity: StringEntity) => void;
  /** 2-22: Relation変更コールバック */
  onRelationsChange?: (relations: Relation[]) => void;
  /** 4-A-01: 階層の深さ */
  hierarchyDepth?: number;
  /** 4-A-01: 子を持つかどうか */
  hierarchyHasChildren?: boolean;
  /** 4-A-01: 折りたたまれているか */
  hierarchyCollapsed?: boolean;
  /** タグクリック時のコールバック */
  onTagClick?: (tag: string) => void;
  /** Relation先エンティティクリック時のコールバック */
  onRelationClick?: (entity: StringEntity) => void;
  /** 4-A-01: 折りたたみトグルコールバック */
  onToggleCollapse?: () => void;
}) {
  const accent = accentFromSysTags(entity.sysTags);
  const cc = colorClasses(accent.color);
  const allTags = [...entity.userTags, ...entity.sysTags];
  const displayTags = allTags.slice(0, 3);
  const moreTags = allTags.length - 3;

  const [favorite, setFavorite] = useState(favoriteState ?? false);
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<number | null>(null);
  // 2-23: 名前列hover
  const [nameHover, setNameHover] = useState(false);
  // 4-A-02: 名前列のtriggerRect（ポータル配置用）
  const [nameTriggerRect, setNameTriggerRect] = useState<DOMRect | null>(null);
  const nameRef = useRef<HTMLTableCellElement>(null);
  // プレビューモーダル表示用state
  const [showPreviewModal, setShowPreviewModal] = useState(false);
  // 2-22: インライン編集中のセル
  const [editingCol, setEditingCol] = useState<string | null>(null);

  // relation label → target entity name の解決
  const relationValueMap = useMemo(() => {
    if (!relations || !allEntities || !relationLabels?.length) return {};
    const entityMap = new Map(allEntities.map((e) => [e.id, e]));
    const map: Record<string, string> = {};
    for (const label of relationLabels) {
      const rel = relations.find(
        (r) =>
          r.label === label &&
          (r.entity1Id === entity.id || r.entity2Id === entity.id),
      );
      if (rel) {
        const targetId =
          rel.entity1Id === entity.id ? rel.entity2Id : rel.entity1Id;
        const target = entityMap.get(targetId);
        if (target) map[label] = target.name;
      }
    }
    return map;
  }, [relations, allEntities, relationLabels, entity.id]);

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
    fetchFavoriteState(entity.id).then((res) => {
      if (!active || !res.data) return;
      setFavorite(res.data.favorite);
    });
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

  const handleFavorite = (event: React.MouseEvent) => {
    event.stopPropagation();
    toggleEntityFavorite(entity.id).then((res) => {
      if (!res.data) return;
      setFavorite(res.data.favorite);
      onFavoriteChange?.(res.data.favorite);
    });
  };

  const handleCopy = (event: React.MouseEvent) => {
    event.stopPropagation();
    navigator.clipboard.writeText(entity.body);
    setCopied(true);
    if (copyTimerRef.current) {
      window.clearTimeout(copyTimerRef.current);
    }
    copyTimerRef.current = window.setTimeout(() => {
      setCopied(false);
    }, 1200);
  };

  const handleDownload = (event: React.MouseEvent) => {
    event.stopPropagation();
    const blob = new Blob([entity.body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = entity.name || `${entity.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    recordEntityDownload(entity.id).then((res) => {
      if (res.data) return;
    });
  };

  const canSelect = selectionMode && onToggleSelect;
  // 2-23: 行クリックは選択モードのみ（詳細遷移は名前列に限定）
  const handleRowClick = () => {
    if (canSelect) {
      onToggleSelect(entity.id);
    }
  };

  const hasExtraColumns =
    (propertyKeys && propertyKeys.length > 0) ||
    (relationLabels && relationLabels.length > 0);

  return (
    <tr
      onClick={handleRowClick}
      className={`
        group
        border-b border-gray-300 dark:border-gray-600
        hover:bg-neutral-50 dark:hover:bg-neutral-800/50
        ${canSelect ? "cursor-pointer" : ""}
        transition-colors
      `}
    >
      {onToggleSelect && (
        <td className="py-3 px-4">
          <input
            type="checkbox"
            checked={Boolean(selected)}
            onChange={() => onToggleSelect(entity.id)}
            onClick={(event) => event.stopPropagation()}
            className="h-5 w-5 accent-pink-500 cursor-pointer"
          />
        </td>
      )}
      {/* 2-23: 名前列（クリックで詳細遷移、hover時プレビュー） */}
      {/* 4-A-01: 階層表示対応 */}
      {/* 4-A-02: ポータル化されたプレビュー対応 */}
      <td
        ref={nameRef}
        className="py-3 px-4 relative"
        onClick={(e) => {
          if (!canSelect && onRowClick) {
            e.stopPropagation();
            onRowClick(entity);
          }
        }}
        onMouseEnter={() => {
          setNameHover(true);
          if (nameRef.current) {
            setNameTriggerRect(nameRef.current.getBoundingClientRect());
          }
        }}
        onMouseMove={() => {
          if (nameRef.current) {
            setNameTriggerRect(nameRef.current.getBoundingClientRect());
          }
        }}
        onMouseLeave={() => {
          setNameHover(false);
          setNameTriggerRect(null);
        }}
      >
        <div
          className="flex items-center gap-2"
          style={{
            paddingLeft:
              hierarchyDepth !== undefined ? `${hierarchyDepth * 20}px` : 0,
          }}
        >
          {/* 4-A-01: 階層トグルボタン */}
          {hierarchyDepth !== undefined && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                onToggleCollapse?.();
              }}
              className={`inline-flex items-center justify-center h-5 w-5 rounded transition-colors ${
                hierarchyHasChildren
                  ? "hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer"
                  : ""
              }`}
              disabled={!hierarchyHasChildren}
            >
              {hierarchyHasChildren ? (
                hierarchyCollapsed ? (
                  <ChevronRight size={14} className="text-amber-500" />
                ) : (
                  <ChevronDown size={14} className="text-amber-500" />
                )
              ) : (
                <span className="w-3.5" />
              )}
            </button>
          )}
          {/* 4-A-01: レポジトリ/フォルダ/ファイルアイコン */}
          {hierarchyDepth !== undefined ? (
            entity.sysTags.includes("repository") ? (
              <GitBranch
                size={16}
                className="text-violet-500 dark:text-violet-400 flex-shrink-0"
              />
            ) : entity.sysTags.includes("directory") ? (
              hierarchyCollapsed ? (
                <FolderClosed
                  size={16}
                  className="text-amber-500 dark:text-amber-400 flex-shrink-0"
                />
              ) : (
                <FolderOpen
                  size={16}
                  className="text-amber-500 dark:text-amber-400 flex-shrink-0"
                />
              )
            ) : (
              <span
                className={`inline-flex items-center justify-center h-5 w-5 rounded text-xs ${cc.bg} ${cc.text}`}
              >
                {accent.emoji}
              </span>
            )
          ) : (
            <span
              className={`inline-flex items-center justify-center h-5 w-5 rounded text-xs ${cc.bg} ${cc.text}`}
            >
              {accent.emoji}
            </span>
          )}
          <span
            className={`font-medium truncate max-w-[200px] ${onRowClick && !canSelect ? "cursor-pointer hover:underline" : ""}`}
            title={entity.name}
          >
            {entity.name}
          </span>
          {/* プレビューボタン: クリックでモーダル表示 */}
          {entity.body && (
            <button
              type="button"
              onClick={(e) => {
                e.stopPropagation();
                setShowPreviewModal(true);
              }}
              className="ml-1 inline-flex items-center justify-center h-5 w-5 rounded opacity-0 group-hover:opacity-100 hover:bg-neutral-200 dark:hover:bg-neutral-700 transition-all flex-shrink-0"
              title="プレビュー"
            >
              <Eye size={13} className="text-neutral-500" />
            </button>
          )}
        </div>
        {/* 4-A-02: ポータル化されたプレビューツールチップ */}
        {nameHover && entity.body && (
          <BodyPreviewTooltip
            text={entity.body}
            entity={entity}
            visible={nameHover}
            triggerRect={nameTriggerRect}
            enableModal
          />
        )}
        {/* プレビューモーダル */}
        {showPreviewModal && entity.body && (
          <BodyPreviewModal
            entity={entity}
            onClose={() => setShowPreviewModal(false)}
          />
        )}
      </td>

      {/* 2-22: プロパティ列（ダブルクリックで編集） */}
      {propertyKeys?.map((key) => (
        <td
          key={`prop-${key}`}
          className="py-3 px-4 text-sm text-neutral-600 dark:text-neutral-400"
          onDoubleClick={() => {
            if (onEntityChange) setEditingCol(`prop:${key}`);
          }}
        >
          {editingCol === `prop:${key}` ? (
            <InlineEditInput
              value={entity.userProps[key] ?? ""}
              onSave={(v) => {
                onEntityChange?.({
                  ...entity,
                  userProps: { ...entity.userProps, [key]: v },
                });
                setEditingCol(null);
              }}
              onCancel={() => setEditingCol(null)}
            />
          ) : entity.userProps[key] ? (
            <span className="truncate max-w-[120px] block">
              {entity.userProps[key]}
            </span>
          ) : (
            <span className="text-neutral-300 dark:text-neutral-600">-</span>
          )}
        </td>
      ))}

      {/* 2-22: Relation列（ダブルクリックで編集） */}
      {relationLabels?.map((label) => (
        <td
          key={`rel-${label}`}
          className="py-3 px-4 text-sm"
          onDoubleClick={() => {
            if (onRelationsChange && relations) setEditingCol(`rel:${label}`);
          }}
        >
          {editingCol === `rel:${label}` ? (
            <InlineEditInput
              value={relationValueMap[label] ?? ""}
              onSave={(v) => {
                // relation labelの変更: 既存のrelationを更新
                if (relations && onRelationsChange) {
                  const rel = relations.find(
                    (r) =>
                      r.label === label &&
                      (r.entity1Id === entity.id || r.entity2Id === entity.id),
                  );
                  if (rel) {
                    onRelationsChange(
                      relations.map((r) =>
                        r.id === rel.id ? { ...r, label: v || label } : r,
                      ),
                    );
                  }
                }
                setEditingCol(null);
              }}
              onCancel={() => setEditingCol(null)}
              placeholder="label..."
            />
          ) : relationValueMap[label] ? (
            <button
              type="button"
              className="inline-flex items-center gap-1 text-purple-700 dark:text-purple-300 hover:underline cursor-pointer"
              onClick={(e) => {
                e.stopPropagation();
                if (onRelationClick && relations && allEntities) {
                  const rel = relations.find(
                    (r) =>
                      r.label === label &&
                      (r.entity1Id === entity.id || r.entity2Id === entity.id),
                  );
                  if (rel) {
                    const targetId =
                      rel.entity1Id === entity.id
                        ? rel.entity2Id
                        : rel.entity1Id;
                    const target = allEntities.find((en) => en.id === targetId);
                    if (target) onRelationClick(target);
                  }
                }
              }}
            >
              <Link2 size={11} className="opacity-60" />
              <span className="truncate max-w-[120px]">
                {relationValueMap[label]}
              </span>
            </button>
          ) : (
            <span className="text-neutral-300 dark:text-neutral-600">-</span>
          )}
        </td>
      ))}

      {!hasExtraColumns && (
        <>
          {/* 拡張子 */}
          <td className="py-3 px-4 text-sm text-neutral-500 dark:text-neutral-400 whitespace-nowrap">
            {entity.sysProps?.extension ? (
              <span className="font-mono text-xs">
                .{entity.sysProps.extension}
              </span>
            ) : entity.sysTags.includes("repository") ? (
              <span className="text-violet-600 dark:text-violet-400 text-xs">
                レポジトリ
              </span>
            ) : entity.sysTags.includes("directory") ? (
              <span className="text-amber-600 dark:text-amber-400 text-xs">
                フォルダ
              </span>
            ) : (
              <span className="text-neutral-300 dark:text-neutral-600">-</span>
            )}
          </td>

          {/* タイプ */}
          <td className="py-3 px-4 text-sm whitespace-nowrap">
            {entity.entityType ? (
              <span className="text-xs rounded-full border border-sky-200 dark:border-sky-700 bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400 px-2 py-0.5">
                {entity.entityType}
              </span>
            ) : (
              <span className="text-neutral-300 dark:text-neutral-600">-</span>
            )}
          </td>

          {/* 2-22: ドメイン（ダブルクリックで編集） */}
          <td
            className="py-3 px-4"
            onDoubleClick={() => {
              if (onEntityChange) setEditingCol("domain");
            }}
          >
            {editingCol === "domain" ? (
              <InlineEditInput
                value={entity.domain ?? ""}
                onSave={(v) => {
                  onEntityChange?.({ ...entity, domain: v || null });
                  setEditingCol(null);
                }}
                onCancel={() => setEditingCol(null)}
              />
            ) : entity.domain ? (
              <span className={`${chip} ${cc.bg} ${cc.text}`}>
                {entity.domain}
              </span>
            ) : (
              <span className="text-neutral-400">-</span>
            )}
          </td>

          {/* 2-22: タグ（ダブルクリックで編集、スペースで確定） */}
          <td
            className="py-3 px-4"
            onDoubleClick={() => {
              if (onEntityChange) setEditingCol("tags");
            }}
          >
            <div className="flex flex-wrap gap-1 max-w-[200px]">
              {displayTags.map((t) => (
                <button
                  type="button"
                  key={`${entity.id}-${t}`}
                  className={`${chip} text-[11px] ${
                    entity.userTags.includes(t)
                      ? "border-amber-300/80 bg-amber-50/70 text-amber-900"
                      : `${cc.bg} ${cc.text}`
                  } ${onTagClick ? "cursor-pointer hover:opacity-80" : ""}`}
                  onClick={(e) => {
                    if (onTagClick) {
                      e.stopPropagation();
                      onTagClick(t);
                    }
                  }}
                >
                  {t}
                </button>
              ))}
              {moreTags > 0 && (
                <span className="text-xs text-neutral-500">+{moreTags}</span>
              )}
              {editingCol === "tags" && (
                <InlineTagEditInput
                  onAdd={(tag) => {
                    if (!entity.userTags.includes(tag)) {
                      onEntityChange?.({
                        ...entity,
                        userTags: [...entity.userTags, tag],
                      });
                    }
                  }}
                  onDone={() => setEditingCol(null)}
                />
              )}
            </div>
          </td>

          {/* 更新日 */}
          <td className="py-3 px-4 text-sm text-neutral-600 dark:text-neutral-400 whitespace-nowrap">
            {formatDate(entity.updatedAt)}
          </td>
        </>
      )}

      {/* メタ */}
      <td className="py-3 px-4">
        {meta ? (
          <EntityMetaBadges
            owner={meta.owner}
            favorites={meta.favorites}
            downloads={meta.downloads}
            favoriteUsers={meta.favoriteUsers}
            usedBy={meta.usedBy}
            className="text-[11px]"
          />
        ) : (
          <span className="text-xs text-neutral-400">-</span>
        )}
      </td>

      {/* アクション */}
      <td className="py-3 px-4 relative">
        <div className="flex items-center gap-1">
          {/* お気に入り: 常時表示 */}
          <button
            type="button"
            onClick={handleFavorite}
            className={`h-7 w-7 inline-flex items-center justify-center rounded-md border ${
              favorite
                ? "border-rose-300 bg-rose-50 text-rose-600"
                : "border-gray-300 dark:border-gray-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            }`}
            title="お気に入り"
          >
            <Star
              size={14}
              fill={favorite ? "currentColor" : "none"}
              className={favorite ? "text-amber-500" : "text-neutral-400"}
            />
          </button>
          {/* 2-23: コピーボタン（プレビュー廃止） */}
          <button
            type="button"
            onClick={handleCopy}
            className="h-7 w-7 inline-flex items-center justify-center rounded-md border border-gray-300 dark:border-gray-600 bg-white/90 dark:bg-neutral-900/90 hover:bg-neutral-100 dark:hover:bg-neutral-800 opacity-0 group-hover:opacity-100 transition-opacity"
            title="コピー"
          >
            <Clipboard size={14} />
          </button>
          <button
            type="button"
            onClick={handleDownload}
            className="h-7 w-7 inline-flex items-center justify-center rounded-md border border-gray-300 dark:border-gray-600 bg-white/90 dark:bg-neutral-900/90 hover:bg-neutral-100 dark:hover:bg-neutral-800 opacity-0 group-hover:opacity-100 transition-opacity"
            title="ダウンロード"
          >
            <Download size={14} />
          </button>
        </div>
        {copied && (
          <div className="absolute right-12 top-1/2 -translate-y-1/2 rounded-full bg-sky-600/90 text-white text-[10px] px-2 py-0.5 shadow-sm whitespace-nowrap z-10">
            copied!
          </div>
        )}
      </td>
    </tr>
  );
}

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
 * タグ配列を空白区切りキーワードでマッチ（AND条件）
 */
function matchesTagsFilter(tags: string[], filter: string): boolean {
  if (!filter.trim()) return true;
  const keywords = filter.toLowerCase().split(/\s+/).filter(Boolean);
  const joinedTags = tags.join(" ").toLowerCase();
  return keywords.every((kw) => joinedTags.includes(kw));
}

/**
 * ソート関数（2-19: prop/rel列対応）
 */
function sortEntities(
  entities: StringEntity[],
  column: SortColumn,
  direction: SortDirection,
  relations?: Relation[],
  allEntities?: StringEntity[],
): StringEntity[] {
  if (!column) return entities;

  return [...entities].sort((a, b) => {
    let cmp = 0;
    if (typeof column === "string" && column.startsWith("prop:")) {
      const key = column.slice(5);
      cmp = (a.userProps[key] ?? "").localeCompare(
        b.userProps[key] ?? "",
        "ja",
      );
    } else if (typeof column === "string" && column.startsWith("rel:")) {
      const label = column.slice(4);
      const aVal = resolveRelationTarget(a.id, label, relations, allEntities);
      const bVal = resolveRelationTarget(b.id, label, relations, allEntities);
      cmp = aVal.localeCompare(bVal, "ja");
    } else {
      switch (column) {
        case "name":
          cmp = a.name.localeCompare(b.name, "ja");
          break;
        case "domain":
          cmp = (a.domain ?? "").localeCompare(b.domain ?? "", "ja");
          break;
        case "tags": {
          const aTags = [...a.userTags, ...a.sysTags].join(",");
          const bTags = [...b.userTags, ...b.sysTags].join(",");
          cmp = aTags.localeCompare(bTags, "ja");
          break;
        }
        case "updatedAt":
          cmp =
            new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
          break;
      }
    }
    return direction === "asc" ? cmp : -cmp;
  });
}

/**
 * ソート可能なヘッダーセル
 */
function SortableHeader({
  label,
  column,
  currentSort,
  currentDirection,
  onSort,
  onHide,
  className = "",
}: {
  label: string;
  column: SortColumn;
  currentSort: SortColumn;
  currentDirection: SortDirection;
  onSort: (column: SortColumn) => void;
  /** 2-19: 右クリックで列を非表示 */
  onHide?: (column: SortColumn) => void;
  className?: string;
}) {
  const isActive = currentSort === column;

  return (
    <th
      className={`py-2 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300 ${className}`}
      onContextMenu={
        onHide
          ? (e) => {
              e.preventDefault();
              onHide(column);
            }
          : undefined
      }
      title={onHide ? "右クリックで非表示" : undefined}
    >
      <button
        type="button"
        onClick={() => onSort(column)}
        className="flex items-center gap-1 hover:text-neutral-900 dark:hover:text-neutral-100 transition-colors"
      >
        <span>{label}</span>
        <span
          className={`w-4 h-4 ${isActive ? "text-sky-600" : "text-neutral-300"}`}
        >
          {isActive ? (
            currentDirection === "asc" ? (
              <ArrowUp size={14} />
            ) : (
              <ArrowDown size={14} />
            )
          ) : (
            <ArrowUp size={14} className="opacity-30" />
          )}
        </span>
      </button>
    </th>
  );
}

/**
 * フィルター入力セル
 */
function FilterInput({
  value,
  onChange,
  placeholder,
}: {
  value: string;
  onChange: (value: string) => void;
  placeholder?: string;
}) {
  return (
    <td className="py-1 px-4">
      <input
        type="text"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full px-2 py-1 text-xs border border-gray-200 dark:border-gray-600 rounded bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300 placeholder:text-neutral-400 focus:outline-none focus:ring-1 focus:ring-sky-400 focus:border-sky-400"
      />
    </td>
  );
}

/**
 * 2-22: インラインセル編集入力
 */
function InlineEditInput({
  value,
  onSave,
  onCancel,
  placeholder,
}: {
  value: string;
  onSave: (v: string) => void;
  onCancel: () => void;
  placeholder?: string;
}) {
  const [v, setV] = useState(value);
  return (
    <input
      type="text"
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={() => onSave(v)}
      onKeyDown={(e) => {
        if (e.key === "Enter") onSave(v);
        else if (e.key === "Escape") onCancel();
      }}
      autoFocus
      placeholder={placeholder}
      className="w-full px-1 py-0.5 text-xs border border-sky-400 rounded bg-white dark:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-sky-400"
    />
  );
}

/**
 * 2-22: タグ用インラインセル編集（スペースで確定）
 */
function InlineTagEditInput({
  onAdd,
  onDone,
}: {
  onAdd: (tag: string) => void;
  onDone: () => void;
}) {
  const [v, setV] = useState("");
  const commit = () => {
    if (v.trim()) onAdd(v.trim());
    setV("");
  };
  return (
    <input
      type="text"
      value={v}
      onChange={(e) => setV(e.target.value)}
      onBlur={() => {
        commit();
        onDone();
      }}
      onKeyDown={(e) => {
        if (e.key === " ") {
          e.preventDefault();
          commit();
        } else if (e.key === "Enter") {
          commit();
          onDone();
        } else if (e.key === "Escape") {
          onDone();
        }
      }}
      autoFocus
      placeholder="タグを追加..."
      className="w-20 px-1 py-0.5 text-[11px] border border-sky-400 rounded bg-white dark:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-sky-400"
    />
  );
}

/**
 * 4-A-04: body直接編集用モーダル
 */
function InlineBodyEditor({
  value,
  onSave,
  onCancel,
}: {
  value: string;
  onSave: (v: string) => void;
  onCancel: () => void;
}) {
  const [v, setV] = useState(value);
  const textareaRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // モーダル表示時にテキストエリアにフォーカス
    textareaRef.current?.focus();
  }, []);

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/40">
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-xl border border-neutral-300 dark:border-neutral-600 w-[600px] max-w-[90vw] max-h-[80vh] flex flex-col">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-4 py-2 border-b border-neutral-200 dark:border-neutral-700">
          <div className="flex items-center gap-2 text-sm font-medium text-neutral-700 dark:text-neutral-200">
            <FileText size={16} className="text-sky-600" />
            本文を編集
          </div>
          <button
            type="button"
            onClick={onCancel}
            className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <X size={16} />
          </button>
        </div>
        {/* テキストエリア */}
        <div className="flex-1 p-4 overflow-hidden">
          <textarea
            ref={textareaRef}
            value={v}
            onChange={(e) => setV(e.target.value)}
            className="w-full h-full min-h-[300px] rounded-lg border border-neutral-300 dark:border-neutral-600 bg-neutral-50 dark:bg-neutral-800 p-3 font-mono text-sm leading-relaxed resize-none focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400"
            placeholder="本文を入力..."
          />
        </div>
        {/* フッター */}
        <div className="flex items-center justify-between px-4 py-2 border-t border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
          <span className="text-xs text-neutral-500">
            {v.length} 文字 / {v.split("\n").length} 行
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={onCancel}
              className="px-3 py-1.5 text-sm rounded-lg border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-700 transition-colors"
            >
              キャンセル
            </button>
            <button
              type="button"
              onClick={() => onSave(v)}
              className="px-3 py-1.5 text-sm rounded-lg bg-sky-600 text-white hover:bg-sky-700 transition-colors inline-flex items-center gap-1"
            >
              <Check size={14} />
              保存
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}

/**
 * 4-A-04: bodyプレビュー + ダブルクリック編集セル
 */
function BodyCell({
  body,
  onBodyChange,
}: {
  body: string;
  onBodyChange?: (body: string) => void;
}) {
  const [isEditing, setIsEditing] = useState(false);
  const preview = body.slice(0, 80).replace(/\n/g, " ");
  const hasMore = body.length > 80;

  return (
    <>
      <td
        className="py-3 px-4 text-xs text-neutral-600 dark:text-neutral-400 max-w-[200px]"
        onDoubleClick={() => {
          if (onBodyChange) setIsEditing(true);
        }}
        title={onBodyChange ? "ダブルクリックで編集" : undefined}
      >
        {body ? (
          <span className="truncate block cursor-text">
            {preview}
            {hasMore && <span className="text-neutral-400">...</span>}
          </span>
        ) : (
          <span className="text-neutral-300 dark:text-neutral-600 italic">
            （空）
          </span>
        )}
      </td>
      {isEditing && onBodyChange && (
        <InlineBodyEditor
          value={body}
          onSave={(v) => {
            onBodyChange(v);
            setIsEditing(false);
          }}
          onCancel={() => setIsEditing(false)}
        />
      )}
    </>
  );
}

/**
 * 4-A-04: マルチセル選択バー（選択されたセルの一括編集UI）
 */
function MultiCellSelectionBar({
  selectedCells,
  entities,
  onBulkEdit,
  onClear,
}: {
  selectedCells: CellId[];
  entities: StringEntity[];
  onBulkEdit: (value: string) => void;
  onClear: () => void;
}) {
  const [editValue, setEditValue] = useState("");
  const [showEditInput, setShowEditInput] = useState(false);

  // 選択されたセルのカラムタイプを判定
  const columnTypes = new Set(
    selectedCells.map((c) => {
      if (c.column === "domain") return "domain";
      if (c.column === "body") return "body";
      if (c.column.startsWith("prop:")) return "prop";
      return "other";
    }),
  );
  const isSingleType = columnTypes.size === 1;
  const columnType = isSingleType ? Array.from(columnTypes)[0] : "mixed";

  // 選択されたエンティティのID一覧
  const selectedEntityIds = new Set(selectedCells.map((c) => c.entityId));
  const selectedCount = selectedEntityIds.size;

  if (selectedCells.length === 0) return null;

  return (
    <div className="flex items-center gap-3 px-4 py-2 border-b border-sky-200 dark:border-sky-800 bg-sky-50 dark:bg-sky-900/30 text-sm">
      <div className="flex items-center gap-2 text-sky-700 dark:text-sky-300">
        <Check size={14} />
        <span className="font-medium">{selectedCells.length}セル</span>
        <span className="text-sky-600 dark:text-sky-400">
          （{selectedCount}件）を選択中
        </span>
      </div>

      {showEditInput ? (
        <div className="flex items-center gap-2 ml-auto">
          <input
            type="text"
            value={editValue}
            onChange={(e) => setEditValue(e.target.value)}
            placeholder={
              columnType === "body" ? "本文を入力..." : "値を入力..."
            }
            className="px-2 py-1 text-sm border border-sky-300 dark:border-sky-700 rounded bg-white dark:bg-neutral-900 w-48 focus:outline-none focus:ring-1 focus:ring-sky-400"
            autoFocus
            onKeyDown={(e) => {
              if (e.key === "Enter" && editValue.trim()) {
                onBulkEdit(editValue);
                setEditValue("");
                setShowEditInput(false);
              }
              if (e.key === "Escape") {
                setShowEditInput(false);
                setEditValue("");
              }
            }}
          />
          <button
            type="button"
            onClick={() => {
              if (editValue.trim()) {
                onBulkEdit(editValue);
                setEditValue("");
                setShowEditInput(false);
              }
            }}
            className="px-2 py-1 text-sm rounded bg-sky-600 text-white hover:bg-sky-700 transition-colors inline-flex items-center gap-1"
          >
            <Check size={12} />
            適用
          </button>
          <button
            type="button"
            onClick={() => {
              setShowEditInput(false);
              setEditValue("");
            }}
            className="px-2 py-1 text-sm rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
          >
            キャンセル
          </button>
        </div>
      ) : (
        <div className="flex items-center gap-2 ml-auto">
          <button
            type="button"
            onClick={() => setShowEditInput(true)}
            className="px-3 py-1 text-sm rounded bg-sky-600 text-white hover:bg-sky-700 transition-colors inline-flex items-center gap-1"
          >
            <Pencil size={12} />
            一括編集
          </button>
          <button
            type="button"
            onClick={onClear}
            className="px-2 py-1 text-sm rounded border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors inline-flex items-center gap-1"
          >
            <X size={12} />
            選択解除
          </button>
        </div>
      )}
    </div>
  );
}

/**
 * 4-A-04: 選択可能なセル（Ctrl+クリックで複数選択）
 */
function SelectableCell({
  entityId,
  column,
  isSelected,
  onSelect,
  children,
  className = "",
}: {
  entityId: string;
  column: CellId["column"];
  isSelected: boolean;
  onSelect: (cellId: CellId, addToSelection: boolean) => void;
  children: React.ReactNode;
  className?: string;
}) {
  return (
    <td
      className={`
        py-3 px-4 cursor-pointer transition-colors
        ${
          isSelected
            ? "bg-sky-100 dark:bg-sky-900/40 ring-2 ring-inset ring-sky-400"
            : "hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
        }
        ${className}
      `}
      onClick={(e) => {
        e.stopPropagation();
        onSelect({ entityId, column }, e.ctrlKey || e.metaKey);
      }}
      title="Ctrl+クリックで複数選択"
    >
      {children}
    </td>
  );
}

/**
 * エンティティ一覧からユニークなプロパティキーを収集
 */
function collectPropertyKeys(entities: StringEntity[]): string[] {
  const keys = new Set<string>();
  for (const e of entities) {
    for (const key of Object.keys(e.userProps)) {
      keys.add(key);
    }
  }
  return Array.from(keys).sort();
}

/**
 * Relation一覧からユニークなラベルを収集
 */
function collectRelationLabels(
  relations: Relation[],
  entityIds: Set<string>,
): string[] {
  const labels = new Set<string>();
  for (const r of relations) {
    if (entityIds.has(r.entity1Id) || entityIds.has(r.entity2Id)) {
      labels.add(r.label);
    }
  }
  return Array.from(labels).sort();
}

/**
 * 2-20: 全エンティティに共通するプロパティキーを収集（AND/交差）
 */
function collectCommonPropertyKeys(entities: StringEntity[]): string[] {
  if (entities.length === 0) return [];
  const common = new Set(Object.keys(entities[0].userProps));
  for (let i = 1; i < entities.length; i++) {
    const keys = new Set(Object.keys(entities[i].userProps));
    for (const k of common) {
      if (!keys.has(k)) common.delete(k);
    }
  }
  return Array.from(common).sort();
}

/**
 * 2-19: Relation先の表示名を解決
 */
function resolveRelationTarget(
  entityId: string,
  label: string,
  relations: Relation[] | undefined,
  allEntities: StringEntity[] | undefined,
): string {
  if (!relations || !allEntities) return "";
  const rel = relations.find(
    (r) =>
      r.label === label &&
      (r.entity1Id === entityId || r.entity2Id === entityId),
  );
  if (!rel) return "";
  const targetId = rel.entity1Id === entityId ? rel.entity2Id : rel.entity1Id;
  const target = allEntities.find((e) => e.id === targetId);
  return target?.name ?? "";
}

/**
 * 4-A-01: Relationから階層構造を構築
 * child/contains等のRelationを解析し、親子関係のツリーを構築
 */
function buildHierarchy(
  entities: StringEntity[],
  relations: Relation[] | undefined,
): HierarchicalEntity[] {
  if (!relations || relations.length === 0) {
    // Relationがない場合はフラットに表示
    return entities.map((e) => ({
      entity: e,
      depth: 0,
      hasChildren: false,
      parentId: null,
    }));
  }

  // 階層Relationのみ抽出（child/contains等: entity1 が親、entity2 が子）
  const hierarchyRelations = relations.filter((r) =>
    HIERARCHY_LABELS.has(r.label.toLowerCase()),
  );

  if (hierarchyRelations.length === 0) {
    return entities.map((e) => ({
      entity: e,
      depth: 0,
      hasChildren: false,
      parentId: null,
    }));
  }

  // 全Relationから「子を持つ親ID」のセットを構築（ページ外の子も含む）
  const parentsWithAnyChildren = new Set<string>();
  for (const rel of hierarchyRelations) {
    parentsWithAnyChildren.add(rel.entity1Id);
  }

  // 親→子のマップを構築（表示エンティティ内の関係のみ）
  const childrenMap = new Map<string, string[]>();
  const parentMap = new Map<string, string>();
  const entityIds = new Set(entities.map((e) => e.id));

  for (const rel of hierarchyRelations) {
    // entity1が親、entity2が子
    const parentId = rel.entity1Id;
    const childId = rel.entity2Id;

    // 両方のエンティティが現在のリストに存在する場合のみ
    if (entityIds.has(parentId) && entityIds.has(childId)) {
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(childId);
      parentMap.set(childId, parentId);
    }
  }

  // ルートエンティティを特定（親を持たないエンティティ）
  const rootIds = entities.filter((e) => !parentMap.has(e.id)).map((e) => e.id);

  // エンティティIDからエンティティへのマップ
  const entityMap = new Map(entities.map((e) => [e.id, e]));

  // DFSでツリーを構築
  const result: HierarchicalEntity[] = [];

  const traverse = (id: string, depth: number) => {
    const entity = entityMap.get(id);
    if (!entity) return;

    const children = childrenMap.get(id) || [];
    // hasChildrenは全Relation（ページ外含む）で判定
    result.push({
      entity,
      depth,
      hasChildren: parentsWithAnyChildren.has(id),
      parentId: parentMap.get(id) ?? null,
    });

    // 子を名前でソートして再帰（レポジトリ→フォルダ→ファイルの順）
    const sortedChildren = children
      .map((cid) => entityMap.get(cid))
      .filter((e): e is StringEntity => e !== undefined)
      .sort((a, b) => {
        const pri = (e: StringEntity) => {
          if (e.sysTags.includes("repository")) return 0;
          if (e.sysTags.includes("directory")) return 1;
          return 2;
        };
        const aPri = pri(a);
        const bPri = pri(b);
        if (aPri !== bPri) return aPri - bPri;
        return a.name.localeCompare(b.name, "ja");
      });

    for (const child of sortedChildren) {
      traverse(child.id, depth + 1);
    }
  };

  // ルートを名前でソートして開始（レポジトリ→フォルダ→ファイルの順）
  const sortedRoots = rootIds
    .map((id) => entityMap.get(id))
    .filter((e): e is StringEntity => e !== undefined)
    .sort((a, b) => {
      const pri = (e: StringEntity) => {
        if (e.sysTags.includes("repository")) return 0;
        if (e.sysTags.includes("directory")) return 1;
        return 2;
      };
      const aPri = pri(a);
      const bPri = pri(b);
      if (aPri !== bPri) return aPri - bPri;
      return a.name.localeCompare(b.name, "ja");
    });

  for (const root of sortedRoots) {
    traverse(root.id, 0);
  }

  return result;
}

export function EntityTable({
  entities,
  onRowClick,
  metaById,
  selectedIds,
  onToggleSelect,
  onToggleSelectAll,
  selectionMode = false,
  favoriteStateMap,
  onFavoriteChange,
  enableFiltering = false,
  editable = false,
  onEntityChange,
  editingEntityId,
  onEditEntity,
  relations,
  allEntities,
  onRelationsChange,
  enableHierarchy = false,
  enableFullTextSearch = false,
  enableBodyColumn = false,
  enableMultiCellSelect = false,
  onTagClick,
  onRelationClick,
}: EntityTableProps) {
  const [filters, setFilters] = useState<ColumnFilters>({
    name: "",
    domain: "",
    tags: "",
  });
  const [sortColumn, setSortColumn] = useState<SortColumn>(null);
  const [sortDirection, setSortDirection] = useState<SortDirection>("asc");
  // 内部管理の編集状態（editingEntityIdが外部から渡されない場合）
  const [internalEditingId, setInternalEditingId] = useState<string | null>(
    null,
  );
  const activeEditingId = editingEntityId ?? internalEditingId;

  // 2-19/2-20: 列表示/非表示制御
  const [hiddenColumns, setHiddenColumns] = useState<Set<string>>(new Set());
  const [showColumnSettings, setShowColumnSettings] = useState(false);
  // 2-19: 動的列フィルター（prop:key, rel:label → filter text）
  const [dynamicFilters, setDynamicFilters] = useState<Record<string, string>>(
    {},
  );
  // 2-21: Relationのみ表示モード
  const [relationOnlyMode, setRelationOnlyMode] = useState(false);
  // 4-A-01: 階層折りたたみ状態（折りたたまれた親エンティティIDのセット）
  // 初期状態: repository/directoryタグを持つエンティティは折り畳み済み
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => {
    if (!enableHierarchy) return new Set();
    const collapsibleIds = new Set<string>();
    for (const e of entities) {
      if (e.sysTags.includes("directory") || e.sysTags.includes("repository")) {
        collapsibleIds.add(e.id);
      }
    }
    return collapsibleIds;
  });

  // 4-A-01: エンティティ変更時に新しいdirectory/repositoryエンティティを折りたたみ済みに追加
  useEffect(() => {
    if (!enableHierarchy) return;
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      let changed = false;
      for (const e of entities) {
        if (
          (e.sysTags.includes("directory") ||
            e.sysTags.includes("repository")) &&
          !next.has(e.id)
        ) {
          next.add(e.id);
          changed = true;
        }
      }
      // 表示中のエンティティに存在しないIDを削除（古いページのゴミ掃除）
      for (const id of prev) {
        if (!entities.some((e) => e.id === id)) {
          next.delete(id);
          changed = true;
        }
      }
      return changed ? next : prev;
    });
  }, [entities, enableHierarchy]);

  // 4-A-03: 全文検索状態
  const [fullTextQuery, setFullTextQuery] = useState("");
  const [filterConditions, setFilterConditions] = useState<FilterCondition[]>(
    [],
  );
  const [savedFilters, setSavedFilters] = useState<SavedFilter[]>([]);

  // 4-A-04: マルチセル選択状態
  const [selectedCells, setSelectedCells] = useState<CellId[]>([]);

  // 4-A-04: セル選択ハンドラ
  const handleCellSelect = (cellId: CellId, addToSelection: boolean) => {
    if (!enableMultiCellSelect) return;

    setSelectedCells((prev) => {
      // 既に選択されているかチェック
      const isAlreadySelected = prev.some(
        (c) => c.entityId === cellId.entityId && c.column === cellId.column,
      );

      if (addToSelection) {
        // Ctrl+クリック: 選択をトグル
        if (isAlreadySelected) {
          return prev.filter(
            (c) =>
              !(c.entityId === cellId.entityId && c.column === cellId.column),
          );
        }
        return [...prev, cellId];
      }
      // 通常クリック: 選択を置き換え
      if (isAlreadySelected && prev.length === 1) {
        return []; // 同じセルを再度クリックで選択解除
      }
      return [cellId];
    });
  };

  // 4-A-04: 一括編集ハンドラ
  const handleBulkEdit = (value: string) => {
    if (!onEntityChange || selectedCells.length === 0) return;

    // 選択されたセルごとにエンティティを更新
    const updatedEntities = new Map<string, StringEntity>();

    for (const cell of selectedCells) {
      const entity = entities.find((e) => e.id === cell.entityId);
      if (!entity) continue;

      // 既に更新済みのエンティティがあればそれを使う
      const current = updatedEntities.get(cell.entityId) || { ...entity };

      if (cell.column === "domain") {
        current.domain = value || null;
      } else if (cell.column === "body") {
        current.body = value;
      } else if (cell.column.startsWith("prop:")) {
        const propKey = cell.column.slice(5);
        current.userProps = { ...current.userProps, [propKey]: value };
      }

      updatedEntities.set(cell.entityId, current);
    }

    // 更新を適用
    for (const updated of updatedEntities.values()) {
      onEntityChange(updated);
    }

    // 選択をクリア
    setSelectedCells([]);
  };

  // 4-A-04: セルが選択されているかチェック
  const isCellSelected = (entityId: string, column: CellId["column"]) => {
    return selectedCells.some(
      (c) => c.entityId === entityId && c.column === column,
    );
  };

  // 4-A-03: 初期化時に保存フィルターを読み込む
  useEffect(() => {
    if (enableFullTextSearch) {
      setSavedFilters(loadSavedFilters());
    }
  }, [enableFullTextSearch]);

  // 4-A-03: フィルター保存
  const handleSaveFilter = (filter: SavedFilter) => {
    const updated = [...savedFilters, filter];
    setSavedFilters(updated);
    saveSavedFilters(updated);
  };

  // 4-A-03: フィルター削除
  const handleDeleteFilter = (filterId: string) => {
    const updated = savedFilters.filter((f) => f.id !== filterId);
    setSavedFilters(updated);
    saveSavedFilters(updated);
  };

  // エンティティID集合
  const entityIds = useMemo(
    () => new Set(entities.map((e) => e.id)),
    [entities],
  );

  // 2-20: プロパティキー（editable: union全キー, normal: AND共通キー）
  const propertyKeys = useMemo(
    () =>
      editable
        ? collectPropertyKeys(entities)
        : collectCommonPropertyKeys(entities),
    [entities, editable],
  );

  // Relationラベル
  const relationLabels = useMemo(
    () =>
      relations && relations.length > 0
        ? collectRelationLabels(relations, entityIds)
        : [],
    [relations, entityIds],
  );

  // Relation先エンティティを含む全エンティティmap
  const resolvedAllEntities = useMemo(
    () => allEntities ?? entities,
    [allEntities, entities],
  );

  // 4-A-01: 階層構造を構築
  const hierarchicalEntities = useMemo(() => {
    if (!enableHierarchy) return null;
    return buildHierarchy(entities, relations);
  }, [entities, relations, enableHierarchy]);

  // 4-A-01: 折りたたみを考慮したエンティティリスト
  const visibleHierarchicalEntities = useMemo(() => {
    if (!hierarchicalEntities) return null;

    const result: HierarchicalEntity[] = [];
    const hiddenByParent = new Set<string>();

    // 折りたたまれた親の子孫を特定
    for (const item of hierarchicalEntities) {
      if (collapsedIds.has(item.entity.id)) {
        // この親の子孫をすべて非表示にする
        const collectDescendants = (parentId: string) => {
          for (const child of hierarchicalEntities) {
            if (child.parentId === parentId) {
              hiddenByParent.add(child.entity.id);
              collectDescendants(child.entity.id);
            }
          }
        };
        collectDescendants(item.entity.id);
      }
    }

    // 非表示でないアイテムのみを結果に追加
    for (const item of hierarchicalEntities) {
      if (!hiddenByParent.has(item.entity.id)) {
        result.push(item);
      }
    }

    return result;
  }, [hierarchicalEntities, collapsedIds]);

  // 4-A-01: 階層トグル
  const toggleCollapse = (entityId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) {
        next.delete(entityId);
      } else {
        next.add(entityId);
      }
      return next;
    });
  };

  // 4-A-01: すべて展開/折りたたみ
  const expandAll = () => setCollapsedIds(new Set());
  const collapseAll = () => {
    if (!hierarchicalEntities) return;
    const parentsWithChildren = hierarchicalEntities
      .filter((item) => item.hasChildren)
      .map((item) => item.entity.id);
    setCollapsedIds(new Set(parentsWithChildren));
  };

  // 2-19/2-20: 表示対象の列（非表示フィルタ適用後）
  const visiblePropertyKeys = useMemo(() => {
    if (relationOnlyMode && !editable) return [];
    return propertyKeys.filter((k) => !hiddenColumns.has(`prop:${k}`));
  }, [propertyKeys, hiddenColumns, relationOnlyMode, editable]);

  const visibleRelationLabels = useMemo(
    () => relationLabels.filter((l) => !hiddenColumns.has(`rel:${l}`)),
    [relationLabels, hiddenColumns],
  );

  // 拡張列レイアウト判定
  const useExtendedLayout =
    !editable &&
    (visiblePropertyKeys.length > 0 || visibleRelationLabels.length > 0);

  // フィルタリングとソートを適用
  const filteredAndSortedEntities = useMemo(() => {
    // 4-A-03: 全文検索フィルター（最初に適用）
    let result = enableFullTextSearch
      ? applySearchFilters(entities, fullTextQuery, filterConditions)
      : entities;

    // 列フィルター（enableFilteringが有効な場合）
    if (enableFiltering) {
      result = result.filter((entity) => {
        if (!matchesFilter(entity.name, filters.name)) return false;
        if (!relationOnlyMode) {
          if (!matchesFilter(entity.domain, filters.domain)) return false;
          if (
            !matchesTagsFilter(
              [...entity.userTags, ...entity.sysTags],
              filters.tags,
            )
          )
            return false;
        }
        // 2-19: 動的列フィルター
        for (const [key, value] of Object.entries(dynamicFilters)) {
          if (!value.trim()) continue;
          if (key.startsWith("prop:")) {
            const propKey = key.slice(5);
            if (!matchesFilter(entity.userProps[propKey], value)) return false;
          } else if (key.startsWith("rel:")) {
            const label = key.slice(4);
            const targetName = resolveRelationTarget(
              entity.id,
              label,
              relations,
              resolvedAllEntities,
            );
            if (!matchesFilter(targetName, value)) return false;
          }
        }
        return true;
      });
    }

    // ソート
    result = sortEntities(
      result,
      sortColumn,
      sortDirection,
      relations,
      resolvedAllEntities,
    );

    return result;
  }, [
    entities,
    filters,
    dynamicFilters,
    sortColumn,
    sortDirection,
    enableFiltering,
    enableFullTextSearch,
    fullTextQuery,
    filterConditions,
    relationOnlyMode,
    relations,
    resolvedAllEntities,
  ]);

  const handleSort = (column: SortColumn) => {
    if (sortColumn === column) {
      setSortDirection((prev) => (prev === "asc" ? "desc" : "asc"));
    } else {
      setSortColumn(column);
      setSortDirection("asc");
    }
  };

  const updateFilter = (key: keyof ColumnFilters, value: string) => {
    setFilters((prev) => ({ ...prev, [key]: value }));
  };

  // 2-19: 右クリックで列を非表示
  const handleHideColumn = (column: SortColumn) => {
    if (!column) return;
    const colStr = String(column);
    if (colStr.startsWith("prop:") || colStr.startsWith("rel:")) {
      setHiddenColumns((prev) => {
        const next = new Set(prev);
        next.add(colStr);
        return next;
      });
    }
  };

  // 2-19/2-20: 列表示トグル
  const toggleColumnVisibility = (columnId: string) => {
    setHiddenColumns((prev) => {
      const next = new Set(prev);
      if (next.has(columnId)) next.delete(columnId);
      else next.add(columnId);
      return next;
    });
  };

  // フィルタークリア
  const hasActiveFilters =
    filters.name ||
    filters.domain ||
    filters.tags ||
    Object.values(dynamicFilters).some((v) => v.trim());

  // 4-A-03: 全文検索のアクティブ状態
  const hasFullTextFilters =
    fullTextQuery.trim() || filterConditions.length > 0;

  const clearAllFilters = () => {
    setFilters({ name: "", domain: "", tags: "" });
    setDynamicFilters({});
    // 4-A-03: 全文検索もクリア
    setFullTextQuery("");
    setFilterConditions([]);
  };

  const handleEditToggle = (entity: StringEntity) => {
    const nextId = activeEditingId === entity.id ? null : entity.id;
    if (onEditEntity) {
      onEditEntity(nextId ? entity : null);
    } else {
      setInternalEditingId(nextId);
    }
  };

  if (entities.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        表示するデータがありません
      </div>
    );
  }

  // 4-A-01: 階層表示時は階層順のリストを使用
  const displayEntities =
    enableHierarchy && visibleHierarchicalEntities
      ? visibleHierarchicalEntities.map((item) => item.entity)
      : enableFiltering
        ? filteredAndSortedEntities
        : entities;

  // 4-A-01: 階層情報のマップ（entityId -> HierarchicalEntity）
  const hierarchyInfoMap = useMemo(() => {
    if (!enableHierarchy || !visibleHierarchicalEntities) return null;
    const map = new Map<string, HierarchicalEntity>();
    for (const item of visibleHierarchicalEntities) {
      map.set(item.entity.id, item);
    }
    return map;
  }, [enableHierarchy, visibleHierarchicalEntities]);

  const allSelected =
    selectedIds && displayEntities.length > 0
      ? displayEntities.every((entity) => selectedIds.has(entity.id))
      : false;

  // editable mode: name + property columns + relation columns + body(optional) + edit
  const editableColCount =
    (onToggleSelect ? 1 : 0) +
    1 +
    propertyKeys.length +
    relationLabels.length +
    (enableBodyColumn ? 1 : 0) +
    1;
  // normal mode column count
  const normalColCount =
    (onToggleSelect ? 1 : 0) +
    1 +
    (useExtendedLayout
      ? visiblePropertyKeys.length + visibleRelationLabels.length
      : relationOnlyMode
        ? 0
        : 5) +
    2;
  // 列設定パネル表示条件（プロパティまたはrelationが存在する場合）
  const hasColumnOptions =
    !editable && (propertyKeys.length > 0 || relationLabels.length > 0);

  // 4-A-01: 階層表示のコントロールバー表示条件
  const hasHierarchyControls =
    enableHierarchy &&
    hierarchicalEntities &&
    hierarchicalEntities.some((item) => item.hasChildren);

  return (
    <div className="space-y-3">
      {/* 4-A-03: 全文検索バー */}
      {enableFullTextSearch && (
        <FullTextSearchBar
          value={fullTextQuery}
          onChange={setFullTextQuery}
          conditions={filterConditions}
          onConditionsChange={setFilterConditions}
          savedFilters={savedFilters}
          onSaveFilter={handleSaveFilter}
          onDeleteFilter={handleDeleteFilter}
          size="md"
          className="w-full"
        />
      )}

      <div className="overflow-x-auto rounded-xl border border-gray-300 dark:border-gray-600">
        {/* 4-A-01: 階層コントロールバー */}
        {hasHierarchyControls && (
          <div className="flex items-center gap-3 px-4 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-amber-50/50 dark:bg-amber-900/20 text-xs">
            <FolderOpen size={14} className="text-amber-500" />
            <span className="text-amber-700 dark:text-amber-300 font-medium">
              階層表示
            </span>
            <div className="flex items-center gap-2 ml-2">
              <button
                type="button"
                onClick={expandAll}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
              >
                <ChevronDown size={12} />
                すべて展開
              </button>
              <button
                type="button"
                onClick={collapseAll}
                className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-amber-300 dark:border-amber-700 text-amber-700 dark:text-amber-300 hover:bg-amber-100 dark:hover:bg-amber-900/30 transition-colors"
              >
                <ChevronRight size={12} />
                すべて折りたたみ
              </button>
            </div>
            <span className="ml-auto text-amber-600 dark:text-amber-400 text-[11px]">
              {visibleHierarchicalEntities?.length ?? 0} / {entities.length}{" "}
              件表示
            </span>
          </div>
        )}
        {/* 4-A-04: マルチセル選択バー */}
        {enableMultiCellSelect && selectedCells.length > 0 && (
          <MultiCellSelectionBar
            selectedCells={selectedCells}
            entities={entities}
            onBulkEdit={handleBulkEdit}
            onClear={() => setSelectedCells([])}
          />
        )}
        {/* 2-19/2-20/2-21: 列設定バー */}
        {hasColumnOptions && (
          <div className="flex items-center gap-3 px-4 py-1.5 border-b border-gray-200 dark:border-gray-700 bg-neutral-50 dark:bg-neutral-800/50 text-xs">
            {/* 2-21: Relationのみ表示 */}
            {relationLabels.length > 0 && (
              <label className="inline-flex items-center gap-1.5 text-neutral-600 dark:text-neutral-400 cursor-pointer select-none">
                <input
                  type="checkbox"
                  checked={relationOnlyMode}
                  onChange={() => setRelationOnlyMode((prev) => !prev)}
                  className="h-3.5 w-3.5 accent-purple-500"
                />
                Relationのみ
              </label>
            )}
            <button
              type="button"
              onClick={() => setShowColumnSettings((prev) => !prev)}
              className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded transition-colors ${
                showColumnSettings
                  ? "bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300"
                  : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
              }`}
            >
              <SlidersHorizontal size={12} />
              列設定
            </button>
          </div>
        )}
        {/* 列設定パネル */}
        {showColumnSettings && hasColumnOptions && (
          <div className="px-4 py-2 border-b border-gray-200 dark:border-gray-700 bg-neutral-100/50 dark:bg-neutral-800/30 flex flex-wrap gap-4 text-xs">
            {propertyKeys.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-teal-700 dark:text-teal-300 font-medium">
                  プロパティ:
                </span>
                {propertyKeys.map((key) => (
                  <label
                    key={`col-prop-${key}`}
                    className="inline-flex items-center gap-1 text-neutral-600 dark:text-neutral-400 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={!hiddenColumns.has(`prop:${key}`)}
                      onChange={() => toggleColumnVisibility(`prop:${key}`)}
                      className="h-3 w-3 accent-teal-500"
                    />
                    {key}
                  </label>
                ))}
              </div>
            )}
            {relationLabels.length > 0 && (
              <div className="flex items-center gap-2 flex-wrap">
                <span className="text-purple-700 dark:text-purple-300 font-medium">
                  Relation:
                </span>
                {relationLabels.map((label) => (
                  <label
                    key={`col-rel-${label}`}
                    className="inline-flex items-center gap-1 text-neutral-600 dark:text-neutral-400 cursor-pointer"
                  >
                    <input
                      type="checkbox"
                      checked={!hiddenColumns.has(`rel:${label}`)}
                      onChange={() => toggleColumnVisibility(`rel:${label}`)}
                      className="h-3 w-3 accent-purple-500"
                    />
                    {label}
                  </label>
                ))}
              </div>
            )}
          </div>
        )}
        <table className="w-full text-sm [&_th+th]:border-l [&_th+th]:border-gray-200 [&_td+td]:border-l [&_td+td]:border-gray-200 dark:[&_th+th]:border-gray-700 dark:[&_td+td]:border-gray-700">
          <thead className="bg-neutral-50 dark:bg-neutral-800/50">
            {/* ヘッダー行 */}
            <tr className="border-b border-gray-300 dark:border-gray-600">
              {onToggleSelect && (
                <th className="py-2 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                  <input
                    type="checkbox"
                    checked={allSelected}
                    onChange={(event) =>
                      onToggleSelectAll?.(event.currentTarget.checked)
                    }
                    className="h-5 w-5 accent-pink-500 cursor-pointer"
                  />
                </th>
              )}
              {editable ? (
                <>
                  <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                    名前
                  </th>
                  {propertyKeys.map((key) => (
                    <th
                      key={`hdr-prop-${key}`}
                      className="py-3 px-4 text-left font-medium text-teal-700 dark:text-teal-300 text-xs whitespace-nowrap"
                    >
                      <span className="inline-flex items-center gap-1">
                        {key}
                      </span>
                    </th>
                  ))}
                  {relationLabels.map((label) => (
                    <th
                      key={`hdr-rel-${label}`}
                      className="py-3 px-4 text-left font-medium text-purple-700 dark:text-purple-300 text-xs whitespace-nowrap"
                    >
                      <span className="inline-flex items-center gap-1">
                        <Link2 size={11} />
                        {label}
                      </span>
                    </th>
                  ))}
                  {/* 4-A-04: Body列 */}
                  {enableBodyColumn && (
                    <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300 text-xs whitespace-nowrap">
                      <span className="inline-flex items-center gap-1">
                        <FileText size={11} />
                        本文
                      </span>
                    </th>
                  )}
                  <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300 w-12">
                    編集
                  </th>
                </>
              ) : enableFiltering ? (
                <>
                  <SortableHeader
                    label="名前"
                    column="name"
                    currentSort={sortColumn}
                    currentDirection={sortDirection}
                    onSort={handleSort}
                  />
                  {useExtendedLayout ? (
                    <>
                      {visiblePropertyKeys.map((key) => (
                        <SortableHeader
                          key={`hdr-prop-${key}`}
                          label={key}
                          column={`prop:${key}`}
                          currentSort={sortColumn}
                          currentDirection={sortDirection}
                          onSort={handleSort}
                          onHide={handleHideColumn}
                          className="text-xs !text-teal-700 dark:!text-teal-300"
                        />
                      ))}
                      {visibleRelationLabels.map((label) => (
                        <SortableHeader
                          key={`hdr-rel-${label}`}
                          label={label}
                          column={`rel:${label}`}
                          currentSort={sortColumn}
                          currentDirection={sortDirection}
                          onSort={handleSort}
                          onHide={handleHideColumn}
                          className="text-xs !text-purple-700 dark:!text-purple-300"
                        />
                      ))}
                    </>
                  ) : !relationOnlyMode ? (
                    <>
                      <th className="py-2 px-4 text-left font-medium text-neutral-500 dark:text-neutral-400 text-xs whitespace-nowrap">
                        拡張子
                      </th>
                      <th className="py-2 px-4 text-left font-medium text-neutral-500 dark:text-neutral-400 text-xs whitespace-nowrap">
                        タイプ
                      </th>
                      <SortableHeader
                        label="ドメイン"
                        column="domain"
                        currentSort={sortColumn}
                        currentDirection={sortDirection}
                        onSort={handleSort}
                      />
                      <SortableHeader
                        label="タグ"
                        column="tags"
                        currentSort={sortColumn}
                        currentDirection={sortDirection}
                        onSort={handleSort}
                      />
                      <SortableHeader
                        label="更新日"
                        column="updatedAt"
                        currentSort={sortColumn}
                        currentDirection={sortDirection}
                        onSort={handleSort}
                      />
                    </>
                  ) : null}
                </>
              ) : (
                <>
                  <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                    名前
                  </th>
                  {useExtendedLayout ? (
                    <>
                      {visiblePropertyKeys.map((key) => (
                        <th
                          key={`hdr-prop-${key}`}
                          className="py-3 px-4 text-left font-medium text-teal-700 dark:text-teal-300 text-xs whitespace-nowrap"
                        >
                          {key}
                        </th>
                      ))}
                      {visibleRelationLabels.map((label) => (
                        <th
                          key={`hdr-rel-${label}`}
                          className="py-3 px-4 text-left font-medium text-purple-700 dark:text-purple-300 text-xs whitespace-nowrap"
                        >
                          <span className="inline-flex items-center gap-1">
                            <Link2 size={11} />
                            {label}
                          </span>
                        </th>
                      ))}
                    </>
                  ) : !relationOnlyMode ? (
                    <>
                      <th className="py-3 px-4 text-left font-medium text-neutral-500 dark:text-neutral-400 text-xs whitespace-nowrap">
                        拡張子
                      </th>
                      <th className="py-3 px-4 text-left font-medium text-neutral-500 dark:text-neutral-400 text-xs whitespace-nowrap">
                        タイプ
                      </th>
                      <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                        ドメイン
                      </th>
                      <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                        タグ
                      </th>
                      <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                        更新日
                      </th>
                    </>
                  ) : null}
                </>
              )}
              {!editable && (
                <>
                  <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                    メタ
                  </th>
                  <th className="py-3 px-4 text-left font-medium text-neutral-600 dark:text-neutral-300">
                    アクション
                  </th>
                </>
              )}
            </tr>
            {/* 3-18: フィルター行（編集モード） */}
            {enableFiltering && editable && (
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-neutral-100/50 dark:bg-neutral-800/30">
                {onToggleSelect && <td className="py-1 px-4" />}
                <FilterInput
                  value={filters.name}
                  onChange={(v) => updateFilter("name", v)}
                  placeholder="名前..."
                />
                {propertyKeys.map((key) => (
                  <FilterInput
                    key={`filter-prop-${key}`}
                    value={dynamicFilters[`prop:${key}`] ?? ""}
                    onChange={(v) =>
                      setDynamicFilters((prev) => ({
                        ...prev,
                        [`prop:${key}`]: v,
                      }))
                    }
                    placeholder={`${key}...`}
                  />
                ))}
                {relationLabels.map((label) => (
                  <FilterInput
                    key={`filter-rel-${label}`}
                    value={dynamicFilters[`rel:${label}`] ?? ""}
                    onChange={(v) =>
                      setDynamicFilters((prev) => ({
                        ...prev,
                        [`rel:${label}`]: v,
                      }))
                    }
                    placeholder={`${label}...`}
                  />
                ))}
                <td className="py-1 px-4">
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={clearAllFilters}
                      className="text-xs text-sky-600 hover:text-sky-800 dark:hover:text-sky-400"
                    >
                      クリア
                    </button>
                  )}
                </td>
              </tr>
            )}
            {/* フィルター行（有効時のみ・非編集モード） */}
            {enableFiltering && !editable && (
              <tr className="border-b border-gray-200 dark:border-gray-700 bg-neutral-100/50 dark:bg-neutral-800/30">
                {onToggleSelect && <td className="py-1 px-4" />}
                <FilterInput
                  value={filters.name}
                  onChange={(v) => updateFilter("name", v)}
                  placeholder="名前..."
                />
                {useExtendedLayout ? (
                  <>
                    {visiblePropertyKeys.map((key) => (
                      <FilterInput
                        key={`filter-prop-${key}`}
                        value={dynamicFilters[`prop:${key}`] ?? ""}
                        onChange={(v) =>
                          setDynamicFilters((prev) => ({
                            ...prev,
                            [`prop:${key}`]: v,
                          }))
                        }
                        placeholder={`${key}...`}
                      />
                    ))}
                    {visibleRelationLabels.map((label) => (
                      <FilterInput
                        key={`filter-rel-${label}`}
                        value={dynamicFilters[`rel:${label}`] ?? ""}
                        onChange={(v) =>
                          setDynamicFilters((prev) => ({
                            ...prev,
                            [`rel:${label}`]: v,
                          }))
                        }
                        placeholder={`${label}...`}
                      />
                    ))}
                  </>
                ) : !relationOnlyMode ? (
                  <>
                    <td className="py-1 px-4" />
                    <td className="py-1 px-4" />
                    <FilterInput
                      value={filters.domain}
                      onChange={(v) => updateFilter("domain", v)}
                      placeholder="ドメイン..."
                    />
                    <FilterInput
                      value={filters.tags}
                      onChange={(v) => updateFilter("tags", v)}
                      placeholder="タグ..."
                    />
                    <td className="py-1 px-4" />
                  </>
                ) : null}
                <td className="py-1 px-4" />
                <td className="py-1 px-4">
                  {hasActiveFilters && (
                    <button
                      type="button"
                      onClick={clearAllFilters}
                      className="text-xs text-sky-600 hover:text-sky-800 dark:hover:text-sky-400"
                    >
                      クリア
                    </button>
                  )}
                </td>
              </tr>
            )}
          </thead>
          <tbody className="bg-white dark:bg-neutral-900">
            {displayEntities.length === 0 ? (
              <tr>
                <td
                  colSpan={editable ? editableColCount : normalColCount}
                  className="py-8 text-center text-neutral-500"
                >
                  {enableFiltering
                    ? "フィルター条件に一致するデータがありません"
                    : "表示するデータがありません"}
                </td>
              </tr>
            ) : editable ? (
              displayEntities.map((entity) => {
                const isEditing = activeEditingId === entity.id;
                const accent = accentFromSysTags(entity.sysTags);
                const cc = colorClasses(accent.color);
                // 4-A-01: 階層情報を取得
                const hierarchyInfo = hierarchyInfoMap?.get(entity.id);

                return (
                  <EditableTableRows
                    key={entity.id}
                    entity={entity}
                    isEditing={isEditing}
                    accent={accent}
                    cc={cc}
                    propertyKeys={propertyKeys}
                    relationLabels={relationLabels}
                    relations={relations}
                    allEntities={resolvedAllEntities}
                    colCount={editableColCount}
                    onToggleSelect={onToggleSelect}
                    selected={selectedIds?.has(entity.id)}
                    onToggleEdit={() => handleEditToggle(entity)}
                    onEntityChange={onEntityChange}
                    onRelationsChange={onRelationsChange}
                    // 4-A-01: 階層表示用props
                    hierarchyDepth={hierarchyInfo?.depth}
                    hierarchyHasChildren={hierarchyInfo?.hasChildren}
                    hierarchyCollapsed={collapsedIds.has(entity.id)}
                    onToggleCollapse={() => toggleCollapse(entity.id)}
                    // 4-A-04: Body列表示
                    enableBodyColumn={enableBodyColumn}
                    // 4-A-04: マルチセル選択
                    enableMultiCellSelect={enableMultiCellSelect}
                    onCellSelect={handleCellSelect}
                    isCellSelected={isCellSelected}
                  />
                );
              })
            ) : (
              displayEntities.map((entity) => {
                // 4-A-01: 階層情報を取得
                const hierarchyInfo = hierarchyInfoMap?.get(entity.id);
                return (
                  <TableRow
                    key={entity.id}
                    entity={entity}
                    onRowClick={onRowClick}
                    meta={metaById?.[entity.id]}
                    selected={selectedIds?.has(entity.id)}
                    onToggleSelect={onToggleSelect}
                    selectionMode={selectionMode}
                    favoriteState={favoriteStateMap?.[entity.id]}
                    onFavoriteChange={(next) =>
                      onFavoriteChange?.(entity.id, next)
                    }
                    relations={relations}
                    allEntities={resolvedAllEntities}
                    relationLabels={
                      visibleRelationLabels.length > 0
                        ? visibleRelationLabels
                        : undefined
                    }
                    propertyKeys={
                      visiblePropertyKeys.length > 0
                        ? visiblePropertyKeys
                        : undefined
                    }
                    onEntityChange={onEntityChange}
                    onRelationsChange={onRelationsChange}
                    // 4-A-01: 階層表示用props
                    hierarchyDepth={hierarchyInfo?.depth}
                    hierarchyHasChildren={hierarchyInfo?.hasChildren}
                    hierarchyCollapsed={collapsedIds.has(entity.id)}
                    onToggleCollapse={() => toggleCollapse(entity.id)}
                    onTagClick={onTagClick}
                    onRelationClick={onRelationClick}
                  />
                );
              })
            )}
          </tbody>
        </table>
        {/* フィルター結果件数表示 */}
        {(enableFiltering && hasActiveFilters) ||
        (enableFullTextSearch && hasFullTextFilters) ? (
          <div className="px-4 py-2 text-xs text-neutral-500 bg-neutral-50 dark:bg-neutral-800/50 border-t border-gray-200 dark:border-gray-700">
            {filteredAndSortedEntities.length} / {entities.length} 件を表示
            {enableFullTextSearch && hasFullTextFilters && (
              <span className="ml-2 text-sky-600 dark:text-sky-400">
                （全文検索）
              </span>
            )}
          </div>
        ) : null}
      </div>
    </div>
  );
}

/** 編集可能テーブル行（サマリー行 + 展開編集パネル行） */
function EditableTableRows({
  entity,
  isEditing,
  accent,
  cc,
  propertyKeys,
  relationLabels,
  relations,
  allEntities,
  colCount,
  onToggleSelect,
  selected,
  onToggleEdit,
  onEntityChange,
  onRelationsChange,
  // 4-A-01: 階層表示用props
  hierarchyDepth,
  hierarchyHasChildren,
  hierarchyCollapsed,
  onToggleCollapse,
  // 4-A-04: Body列表示
  enableBodyColumn,
  // 4-A-04: マルチセル選択
  enableMultiCellSelect,
  onCellSelect,
  isCellSelected,
}: {
  entity: StringEntity;
  isEditing: boolean;
  accent: { emoji: string; color: string };
  cc: { bg: string; text: string };
  propertyKeys: string[];
  relationLabels: string[];
  relations?: Relation[];
  allEntities?: StringEntity[];
  colCount: number;
  onToggleSelect?: (entityId: string) => void;
  selected?: boolean;
  onToggleEdit: () => void;
  onEntityChange?: (entity: StringEntity) => void;
  onRelationsChange?: (relations: Relation[]) => void;
  /** 4-A-01: 階層の深さ */
  hierarchyDepth?: number;
  /** 4-A-01: 子を持つかどうか */
  hierarchyHasChildren?: boolean;
  /** 4-A-01: 折りたたまれているか */
  hierarchyCollapsed?: boolean;
  /** 4-A-01: 折りたたみトグルコールバック */
  onToggleCollapse?: () => void;
  /** 4-A-04: Body列を表示 */
  enableBodyColumn?: boolean;
  /** 4-A-04: マルチセル選択を有効にする */
  enableMultiCellSelect?: boolean;
  /** 4-A-04: セル選択ハンドラ */
  onCellSelect?: (cellId: CellId, addToSelection: boolean) => void;
  /** 4-A-04: セルが選択されているかチェック */
  isCellSelected?: (entityId: string, column: CellId["column"]) => boolean;
}) {
  // relation label → target entity name
  const relationValueMap = useMemo(() => {
    if (!relations || !allEntities) return {};
    const entityMap = new Map(allEntities.map((e) => [e.id, e]));
    const map: Record<string, string> = {};
    for (const label of relationLabels) {
      const rel = relations.find(
        (r) =>
          r.label === label &&
          (r.entity1Id === entity.id || r.entity2Id === entity.id),
      );
      if (rel) {
        const targetId =
          rel.entity1Id === entity.id ? rel.entity2Id : rel.entity1Id;
        const target = entityMap.get(targetId);
        if (target) map[label] = target.name;
      }
    }
    return map;
  }, [relations, allEntities, relationLabels, entity.id]);

  return (
    <>
      {/* サマリー行 */}
      <tr
        onClick={onToggleEdit}
        className={`
          group cursor-pointer
          border-b border-gray-300 dark:border-gray-600
          ${isEditing ? "bg-sky-50/50 dark:bg-sky-900/20" : "hover:bg-neutral-50 dark:hover:bg-neutral-800/50"}
          transition-colors
        `}
      >
        {onToggleSelect && (
          <td className="py-3 px-4">
            <input
              type="checkbox"
              checked={Boolean(selected)}
              onChange={() => onToggleSelect(entity.id)}
              onClick={(e) => e.stopPropagation()}
              className="h-5 w-5 accent-pink-500 cursor-pointer"
            />
          </td>
        )}
        {/* 名前 4-A-01: 階層表示対応 */}
        <td className="py-3 px-4">
          <div
            className="flex items-center gap-2"
            style={{
              paddingLeft:
                hierarchyDepth !== undefined ? `${hierarchyDepth * 20}px` : 0,
            }}
          >
            {/* 4-A-01: 階層トグルボタン */}
            {hierarchyDepth !== undefined && (
              <button
                type="button"
                onClick={(e) => {
                  e.stopPropagation();
                  onToggleCollapse?.();
                }}
                className={`inline-flex items-center justify-center h-5 w-5 rounded transition-colors ${
                  hierarchyHasChildren
                    ? "hover:bg-neutral-200 dark:hover:bg-neutral-700 cursor-pointer"
                    : ""
                }`}
                disabled={!hierarchyHasChildren}
              >
                {hierarchyHasChildren ? (
                  hierarchyCollapsed ? (
                    <ChevronRight size={14} className="text-amber-500" />
                  ) : (
                    <ChevronDown size={14} className="text-amber-500" />
                  )
                ) : (
                  <span className="w-3.5" />
                )}
              </button>
            )}
            {/* 4-A-01: フォルダ/ファイルアイコン */}
            {hierarchyDepth !== undefined ? (
              entity.sysTags.includes("directory") ? (
                hierarchyCollapsed ? (
                  <FolderClosed
                    size={16}
                    className="text-amber-500 dark:text-amber-400 flex-shrink-0"
                  />
                ) : (
                  <FolderOpen
                    size={16}
                    className="text-amber-500 dark:text-amber-400 flex-shrink-0"
                  />
                )
              ) : (
                <span
                  className={`inline-flex items-center justify-center h-5 w-5 rounded text-xs ${cc.bg} ${cc.text}`}
                >
                  {accent.emoji}
                </span>
              )
            ) : (
              <span
                className={`inline-flex items-center justify-center h-5 w-5 rounded text-xs ${cc.bg} ${cc.text}`}
              >
                {accent.emoji}
              </span>
            )}
            <span
              className="font-medium truncate max-w-[200px]"
              title={entity.name}
            >
              {entity.name}
            </span>
          </div>
        </td>

        {/* プロパティ列（4-A-04: マルチセル選択対応） */}
        {propertyKeys.map((key) =>
          enableMultiCellSelect && onCellSelect && isCellSelected ? (
            <SelectableCell
              key={`prop-${key}`}
              entityId={entity.id}
              column={`prop:${key}`}
              isSelected={isCellSelected(entity.id, `prop:${key}`)}
              onSelect={onCellSelect}
              className="text-sm text-neutral-600 dark:text-neutral-400"
            >
              {entity.userProps[key] ? (
                <span
                  className={`${chip} text-[11px] border-teal-300/80 bg-teal-50/70 text-teal-900 dark:bg-teal-900/40 dark:text-teal-200 dark:border-teal-700/80`}
                >
                  {entity.userProps[key]}
                </span>
              ) : (
                <span className="text-neutral-300 dark:text-neutral-600">
                  -
                </span>
              )}
            </SelectableCell>
          ) : (
            <td
              key={`prop-${key}`}
              className="py-3 px-4 text-sm text-neutral-600 dark:text-neutral-400"
            >
              {entity.userProps[key] ? (
                <span
                  className={`${chip} text-[11px] border-teal-300/80 bg-teal-50/70 text-teal-900 dark:bg-teal-900/40 dark:text-teal-200 dark:border-teal-700/80`}
                >
                  {entity.userProps[key]}
                </span>
              ) : (
                <span className="text-neutral-300 dark:text-neutral-600">
                  -
                </span>
              )}
            </td>
          ),
        )}

        {/* Relation列 */}
        {relationLabels.map((label) => (
          <td key={`rel-${label}`} className="py-3 px-4 text-sm">
            {relationValueMap[label] ? (
              <span
                className={`${chip} text-[11px] border-purple-300/80 bg-purple-50/70 text-purple-900 dark:bg-purple-900/40 dark:text-purple-200 dark:border-purple-700/80`}
              >
                <Link2 size={10} className="inline mr-0.5 opacity-60" />
                {relationValueMap[label]}
              </span>
            ) : (
              <span className="text-neutral-300 dark:text-neutral-600">-</span>
            )}
          </td>
        ))}

        {/* 4-A-04: Body列 */}
        {enableBodyColumn && (
          <BodyCell
            body={entity.body}
            onBodyChange={
              onEntityChange
                ? (body) => onEntityChange({ ...entity, body })
                : undefined
            }
          />
        )}

        {/* 編集トグル */}
        <td className="py-3 px-4">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleEdit();
            }}
            className={`h-7 w-7 inline-flex items-center justify-center rounded-md border transition-colors ${
              isEditing
                ? "border-sky-400 bg-sky-100 text-sky-700 dark:bg-sky-900/50 dark:text-sky-300"
                : "border-gray-300 dark:border-gray-600 hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500"
            }`}
            title={isEditing ? "閉じる" : "編集"}
          >
            {isEditing ? <ChevronUp size={14} /> : <Pencil size={14} />}
          </button>
        </td>
      </tr>
      {/* 展開された編集パネル行 */}
      {isEditing && onEntityChange && (
        <tr className="border-b border-gray-300 dark:border-gray-600 bg-sky-50/30 dark:bg-sky-950/20">
          <td colSpan={colCount} className="px-6 py-4">
            <EntityEditPanel
              entity={entity}
              onChange={onEntityChange}
              bodyCollapsed
              relations={relations}
              allEntities={allEntities}
              onRelationsChange={onRelationsChange}
            />
          </td>
        </tr>
      )}
    </>
  );
}
