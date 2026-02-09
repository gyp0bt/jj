"use client";
import { Bookmark, Filter, Globe, Layers, Search, Tag, X } from "lucide-react";
import { useCallback, useEffect, useId, useRef, useState } from "react";
import type { EntityType } from "@/lib/types";

/* ==============================================
 * 4-A-03: 高度なフィルター・保存フィルター型定義
 * ============================================== */

export type SavedFilter = {
  id: string;
  name: string;
  query: string;
  conditions: FilterCondition[];
  createdAt: string;
};

export type FilterCondition = {
  id: string;
  field: "name" | "domain" | "tags" | "body" | "props" | "all";
  operator: "contains" | "equals" | "startsWith" | "endsWith" | "notContains";
  value: string;
  logic: "AND" | "OR";
};

const FIELD_LABELS: Record<FilterCondition["field"], string> = {
  all: "すべて",
  name: "名前",
  domain: "ドメイン",
  tags: "タグ",
  body: "本文",
  props: "プロパティ",
};

const OPERATOR_LABELS: Record<FilterCondition["operator"], string> = {
  contains: "含む",
  equals: "一致",
  startsWith: "前方一致",
  endsWith: "後方一致",
  notContains: "含まない",
};

type SearchBarProps = {
  nameQuery: string;
  onNameQueryChange: (value: string) => void;
  tags: string[];
  onTagsChange: (tags: string[]) => void;
  entityType: EntityType | "";
  onEntityTypeChange: (value: EntityType | "") => void;
  domain: string;
  onDomainChange: (value: string) => void;
  availableDomains?: string[];
  availableEntityTypes?: string[];
  className?: string;
};

export function SearchBar({
  nameQuery,
  onNameQueryChange,
  tags,
  onTagsChange,
  entityType,
  onEntityTypeChange,
  domain,
  onDomainChange,
  availableDomains = [],
  availableEntityTypes = [],
  className = "",
}: SearchBarProps) {
  const [tagInput, setTagInput] = useState("");
  const nameInputId = useId();
  const tagInputId = useId();
  const entityTypeId = useId();
  const domainInputId = useId();
  const domainListId = "searchbar-domain-suggestions";

  const addTags = (rawInput: string) => {
    const candidates = rawInput
      .split(/[\s,]+/)
      .map((tag) => tag.trim())
      .filter(Boolean);
    if (candidates.length === 0) return;
    const existing = new Set(tags.map((tag) => tag.toLowerCase()));
    const next = [...tags];
    candidates.forEach((tag) => {
      const key = tag.toLowerCase();
      if (!existing.has(key)) {
        existing.add(key);
        next.push(tag);
      }
    });
    onTagsChange(next);
  };

  return (
    <div
      className={`rounded-2xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-900 p-4 sm:p-5 shadow-sm ${className}`}
    >
      <div className="grid gap-4 md:grid-cols-4">
        <div className="space-y-2">
          <label
            htmlFor={entityTypeId}
            className="flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300"
          >
            <Layers size={14} />
            タイプ
          </label>
          <select
            id={entityTypeId}
            value={entityType ?? ""}
            onChange={(e) =>
              onEntityTypeChange((e.target.value as EntityType) || "")
            }
            className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
          >
            <option value="">すべて</option>
            {availableEntityTypes.map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-2">
          <label
            htmlFor={nameInputId}
            className="flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300"
          >
            <Search size={14} />
            キーワード
          </label>
          <input
            id={nameInputId}
            type="text"
            value={nameQuery}
            onChange={(e) => onNameQueryChange(e.target.value)}
            placeholder="キーワードを部分一致で検索"
            className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
          />
        </div>
        <div className="space-y-2">
          <label
            htmlFor={tagInputId}
            className="flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300"
          >
            <Tag size={14} />
            タグ
          </label>
          <div className="rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-950 px-3 py-2">
            <div className="flex flex-wrap items-center gap-2">
              {tags.map((tag) => (
                <span
                  key={tag}
                  className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1 text-[12.5px] font-medium border-sky-300/80 dark:border-sky-700/80 bg-sky-50/80 dark:bg-sky-800/60 text-sky-900 dark:text-sky-100"
                >
                  <Tag size={12} /> {tag}
                  <button
                    type="button"
                    onClick={() =>
                      onTagsChange(tags.filter((current) => current !== tag))
                    }
                    className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded hover:bg-sky-200/60 dark:hover:bg-sky-700"
                  >
                    <X size={10} />
                  </button>
                </span>
              ))}
              <input
                id={tagInputId}
                type="text"
                value={tagInput}
                onChange={(e) => setTagInput(e.target.value)}
                onKeyDown={(e) => {
                  if ((e.key === "Enter" || e.key === " ") && tagInput.trim()) {
                    e.preventDefault();
                    addTags(tagInput);
                    setTagInput("");
                  }
                  if (e.key === "Backspace" && !tagInput && tags.length > 0) {
                    onTagsChange(tags.slice(0, -1));
                  }
                }}
                placeholder="スペースで確定（例: abaqus 密度）"
                className="flex-1 min-w-[140px] bg-transparent outline-none py-1 text-sm"
              />
            </div>
          </div>
        </div>
        <div className="space-y-2">
          <label
            htmlFor={domainInputId}
            className="flex items-center gap-2 text-xs font-semibold text-neutral-600 dark:text-neutral-300"
          >
            <Globe size={14} />
            ドメイン
          </label>
          <div className="relative">
            <input
              id={domainInputId}
              type="text"
              value={domain}
              onChange={(e) => onDomainChange(e.target.value)}
              placeholder="部分一致で検索"
              list={availableDomains.length ? domainListId : undefined}
              className="w-full rounded-xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
            />
            {domain && (
              <button
                type="button"
                onClick={() => onDomainChange("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 inline-flex h-5 w-5 items-center justify-center rounded-full text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 hover:text-neutral-600 dark:hover:text-neutral-200"
              >
                <X size={12} />
              </button>
            )}
          </div>
          {availableDomains.length > 0 && (
            <datalist id={domainListId}>
              {availableDomains.map((domainOption) => (
                <option key={domainOption} value={domainOption} />
              ))}
            </datalist>
          )}
        </div>
      </div>
      <div className="mt-3 text-xs text-neutral-500 dark:text-neutral-400">
        タグはスペース区切りで完全一致の検索になります。ドメインは部分一致です。
      </div>
    </div>
  );
}

/* ==============================================
 * 4-A-03: 全文検索バーコンポーネント（FullTextSearchBar）
 * - 全文検索（body含む全フィールド横断）
 * - 高度なフィルター条件（AND/OR複合）
 * - 保存フィルター機能
 * ============================================== */

type FullTextSearchBarProps = {
  /** 検索クエリ */
  value: string;
  /** クエリ変更時コールバック */
  onChange: (value: string) => void;
  /** プレースホルダー */
  placeholder?: string;
  /** 高度なフィルター条件 */
  conditions?: FilterCondition[];
  /** 条件変更時コールバック */
  onConditionsChange?: (conditions: FilterCondition[]) => void;
  /** 保存フィルター一覧 */
  savedFilters?: SavedFilter[];
  /** フィルター保存コールバック */
  onSaveFilter?: (filter: SavedFilter) => void;
  /** フィルター削除コールバック */
  onDeleteFilter?: (filterId: string) => void;
  /** フィルター適用コールバック */
  onApplyFilter?: (filter: SavedFilter) => void;
  /** 高度なフィルターを有効にする（デフォルト: true） */
  enableAdvanced?: boolean;
  /** 保存フィルターを有効にする（デフォルト: true） */
  enableSavedFilters?: boolean;
  /** サイズ（デフォルト: md） */
  size?: "sm" | "md" | "lg";
  /** クラス名 */
  className?: string;
};

export function FullTextSearchBar({
  value,
  onChange,
  placeholder = "全文検索（名前・ドメイン・タグ・本文）...",
  conditions = [],
  onConditionsChange,
  savedFilters = [],
  onSaveFilter,
  onDeleteFilter,
  onApplyFilter,
  enableAdvanced = true,
  enableSavedFilters = true,
  size = "md",
  className = "",
}: FullTextSearchBarProps) {
  const [showAdvanced, setShowAdvanced] = useState(false);
  const [showSaved, setShowSaved] = useState(false);
  const [filterName, setFilterName] = useState("");
  const panelRef = useRef<HTMLDivElement>(null);

  const sizeClasses = {
    sm: "h-8 text-xs",
    md: "h-10 text-sm",
    lg: "h-12 text-base",
  };

  // 外側クリックでパネルを閉じる
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (panelRef.current && !panelRef.current.contains(e.target as Node)) {
        setShowAdvanced(false);
        setShowSaved(false);
      }
    };
    if (showAdvanced || showSaved) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, [showAdvanced, showSaved]);

  // 新しい条件を追加
  const addCondition = useCallback(() => {
    if (!onConditionsChange) return;
    const newCondition: FilterCondition = {
      id: crypto.randomUUID(),
      field: "all",
      operator: "contains",
      value: "",
      logic: "AND",
    };
    onConditionsChange([...conditions, newCondition]);
  }, [conditions, onConditionsChange]);

  // 条件を更新
  const updateCondition = useCallback(
    (id: string, updates: Partial<FilterCondition>) => {
      if (!onConditionsChange) return;
      onConditionsChange(
        conditions.map((c) => (c.id === id ? { ...c, ...updates } : c)),
      );
    },
    [conditions, onConditionsChange],
  );

  // 条件を削除
  const removeCondition = useCallback(
    (id: string) => {
      if (!onConditionsChange) return;
      onConditionsChange(conditions.filter((c) => c.id !== id));
    },
    [conditions, onConditionsChange],
  );

  // フィルターを保存
  const handleSaveFilter = useCallback(() => {
    if (!onSaveFilter || (!value.trim() && conditions.length === 0)) return;
    const name = filterName.trim() || `フィルター ${savedFilters.length + 1}`;
    const filter: SavedFilter = {
      id: crypto.randomUUID(),
      name,
      query: value,
      conditions: [...conditions],
      createdAt: new Date().toISOString(),
    };
    onSaveFilter(filter);
    setFilterName("");
    setShowAdvanced(false);
  }, [value, conditions, filterName, savedFilters.length, onSaveFilter]);

  // フィルターを適用
  const handleApplyFilter = useCallback(
    (filter: SavedFilter) => {
      onChange(filter.query);
      onConditionsChange?.(filter.conditions);
      onApplyFilter?.(filter);
      setShowSaved(false);
    },
    [onChange, onConditionsChange, onApplyFilter],
  );

  // クリア
  const handleClear = useCallback(() => {
    onChange("");
    onConditionsChange?.([]);
  }, [onChange, onConditionsChange]);

  const hasFilters = value.trim() || conditions.length > 0;

  return (
    <div ref={panelRef} className={`relative ${className}`}>
      {/* 検索入力 */}
      <div className="relative flex items-center">
        <Search
          size={size === "sm" ? 14 : size === "lg" ? 20 : 16}
          className="absolute left-3 text-neutral-400"
        />
        <input
          type="text"
          value={value}
          onChange={(e) => onChange(e.target.value)}
          placeholder={placeholder}
          className={`
            w-full pl-9 pr-24 rounded-xl border border-neutral-200 dark:border-neutral-700
            bg-white dark:bg-neutral-900
            focus:outline-none focus:ring-2 focus:ring-sky-400 focus:border-sky-400
            ${sizeClasses[size]}
            ${conditions.length > 0 ? "border-sky-400 dark:border-sky-600" : ""}
          `}
        />
        <div className="absolute right-2 flex items-center gap-1">
          {/* アクティブ条件バッジ */}
          {conditions.length > 0 && (
            <span className="px-1.5 py-0.5 text-[10px] rounded-full bg-sky-100 dark:bg-sky-900 text-sky-700 dark:text-sky-300">
              {conditions.length}
            </span>
          )}
          {/* クリアボタン */}
          {hasFilters && (
            <button
              type="button"
              onClick={handleClear}
              className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400 hover:text-neutral-600"
              title="クリア"
            >
              <X size={14} />
            </button>
          )}
          {/* 高度なフィルターボタン */}
          {enableAdvanced && onConditionsChange && (
            <button
              type="button"
              onClick={() => {
                setShowAdvanced(!showAdvanced);
                setShowSaved(false);
              }}
              className={`p-1.5 rounded transition-colors ${
                showAdvanced
                  ? "bg-sky-100 dark:bg-sky-900 text-sky-700 dark:text-sky-300"
                  : "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400"
              }`}
              title="高度なフィルター"
            >
              <Filter size={14} />
            </button>
          )}
          {/* 保存フィルターボタン */}
          {enableSavedFilters && savedFilters.length > 0 && (
            <button
              type="button"
              onClick={() => {
                setShowSaved(!showSaved);
                setShowAdvanced(false);
              }}
              className={`p-1.5 rounded transition-colors ${
                showSaved
                  ? "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300"
                  : "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400"
              }`}
              title="保存フィルター"
            >
              <Bookmark size={14} />
            </button>
          )}
        </div>
      </div>

      {/* 高度なフィルターパネル */}
      {showAdvanced && enableAdvanced && (
        <div className="absolute z-20 top-full left-0 right-0 mt-1 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg p-4">
          <div className="flex items-center justify-between mb-3">
            <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              高度なフィルター条件
            </h4>
            <button
              type="button"
              onClick={() => setShowAdvanced(false)}
              className="text-neutral-400 hover:text-neutral-600"
            >
              <X size={16} />
            </button>
          </div>

          {/* 条件リスト */}
          <div className="space-y-2 mb-3">
            {conditions.map((condition, index) => (
              <div
                key={condition.id}
                className="flex items-center gap-2 text-xs"
              >
                {/* AND/OR トグル（2番目以降） */}
                {index > 0 && (
                  <button
                    type="button"
                    onClick={() =>
                      updateCondition(condition.id, {
                        logic: condition.logic === "AND" ? "OR" : "AND",
                      })
                    }
                    className={`w-10 px-1.5 py-1 rounded text-[10px] font-medium ${
                      condition.logic === "AND"
                        ? "bg-sky-100 dark:bg-sky-900 text-sky-700 dark:text-sky-300"
                        : "bg-amber-100 dark:bg-amber-900 text-amber-700 dark:text-amber-300"
                    }`}
                  >
                    {condition.logic}
                  </button>
                )}
                {index === 0 && <div className="w-10" />}

                {/* フィールド選択 */}
                <select
                  value={condition.field}
                  onChange={(e) =>
                    updateCondition(condition.id, {
                      field: e.target.value as FilterCondition["field"],
                    })
                  }
                  className="flex-shrink-0 w-24 px-2 py-1.5 rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300"
                >
                  {Object.entries(FIELD_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>

                {/* 演算子選択 */}
                <select
                  value={condition.operator}
                  onChange={(e) =>
                    updateCondition(condition.id, {
                      operator: e.target.value as FilterCondition["operator"],
                    })
                  }
                  className="flex-shrink-0 w-24 px-2 py-1.5 rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300"
                >
                  {Object.entries(OPERATOR_LABELS).map(([key, label]) => (
                    <option key={key} value={key}>
                      {label}
                    </option>
                  ))}
                </select>

                {/* 値入力 */}
                <input
                  type="text"
                  value={condition.value}
                  onChange={(e) =>
                    updateCondition(condition.id, { value: e.target.value })
                  }
                  placeholder="検索値..."
                  className="flex-1 px-2 py-1.5 rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-300"
                />

                {/* 削除ボタン */}
                <button
                  type="button"
                  onClick={() => removeCondition(condition.id)}
                  className="p-1 rounded hover:bg-red-50 dark:hover:bg-red-900/30 text-neutral-400 hover:text-red-500"
                >
                  <X size={14} />
                </button>
              </div>
            ))}
          </div>

          {/* 条件追加ボタン */}
          <button
            type="button"
            onClick={addCondition}
            className="w-full py-1.5 text-xs text-sky-600 dark:text-sky-400 border border-dashed border-sky-300 dark:border-sky-700 rounded hover:bg-sky-50 dark:hover:bg-sky-900/30 transition-colors"
          >
            + 条件を追加
          </button>

          {/* フィルター保存 */}
          {onSaveFilter && hasFilters && (
            <div className="mt-4 pt-3 border-t border-neutral-200 dark:border-neutral-700">
              <div className="flex items-center gap-2">
                <input
                  type="text"
                  value={filterName}
                  onChange={(e) => setFilterName(e.target.value)}
                  placeholder="フィルター名（任意）"
                  className="flex-1 px-2 py-1.5 text-xs rounded border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-800"
                />
                <button
                  type="button"
                  onClick={handleSaveFilter}
                  className="inline-flex items-center gap-1 px-3 py-1.5 text-xs rounded bg-sky-600 text-white hover:bg-sky-700 transition-colors"
                >
                  <Bookmark size={12} />
                  保存
                </button>
              </div>
            </div>
          )}
        </div>
      )}

      {/* 保存フィルター一覧パネル */}
      {showSaved && enableSavedFilters && savedFilters.length > 0 && (
        <div className="absolute z-20 top-full left-0 right-0 mt-1 rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 shadow-lg p-3">
          <div className="flex items-center justify-between mb-2">
            <h4 className="text-sm font-medium text-neutral-700 dark:text-neutral-300">
              保存フィルター
            </h4>
            <button
              type="button"
              onClick={() => setShowSaved(false)}
              className="text-neutral-400 hover:text-neutral-600"
            >
              <X size={16} />
            </button>
          </div>
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {savedFilters.map((filter) => (
              <div
                key={filter.id}
                className="flex items-center gap-2 p-2 rounded hover:bg-neutral-50 dark:hover:bg-neutral-800 group"
              >
                <button
                  type="button"
                  onClick={() => handleApplyFilter(filter)}
                  className="flex-1 text-left"
                >
                  <div className="text-xs font-medium text-neutral-700 dark:text-neutral-300">
                    {filter.name}
                  </div>
                  {(filter.query || filter.conditions.length > 0) && (
                    <div className="text-[10px] text-neutral-400 truncate">
                      {filter.query && `"${filter.query}"`}
                      {filter.conditions.length > 0 &&
                        ` +${filter.conditions.length}条件`}
                    </div>
                  )}
                </button>
                {onDeleteFilter && (
                  <button
                    type="button"
                    onClick={() => onDeleteFilter(filter.id)}
                    className="p-1 rounded opacity-0 group-hover:opacity-100 hover:bg-red-50 dark:hover:bg-red-900/30 text-neutral-400 hover:text-red-500 transition-opacity"
                    title="削除"
                  >
                    <X size={12} />
                  </button>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ==============================================
 * 4-A-03: フィルターユーティリティ関数
 * ============================================== */

/**
 * フィルター条件を適用してエンティティをフィルタリング
 */
export function applySearchFilters<
  T extends {
    name: string;
    domain?: string | null;
    userTags?: string[];
    sysTags?: string[];
    body: string;
    userProps?: Record<string, string>;
  },
>(items: T[], query: string, conditions: FilterCondition[]): T[] {
  let result = items;

  // クエリによる全文検索
  if (query.trim()) {
    const keywords = query.toLowerCase().split(/\s+/).filter(Boolean);
    result = result.filter((item) => {
      const searchText = [
        item.name,
        item.domain ?? "",
        ...(item.userTags ?? []),
        ...(item.sysTags ?? []),
        item.body,
        ...Object.values(item.userProps ?? {}),
      ]
        .join(" ")
        .toLowerCase();
      return keywords.every((kw) => searchText.includes(kw));
    });
  }

  // 条件による詳細フィルター
  if (conditions.length > 0) {
    result = result.filter((item) => {
      // 最初の条件は必ず評価
      let matches = evaluateCondition(item, conditions[0]);

      for (let i = 1; i < conditions.length; i++) {
        const cond = conditions[i];
        const condMatches = evaluateCondition(item, cond);

        if (cond.logic === "AND") {
          matches = matches && condMatches;
        } else {
          matches = matches || condMatches;
        }
      }

      return matches;
    });
  }

  return result;
}

function evaluateCondition<
  T extends {
    name: string;
    domain?: string | null;
    userTags?: string[];
    sysTags?: string[];
    body: string;
    userProps?: Record<string, string>;
  },
>(item: T, condition: FilterCondition): boolean {
  if (!condition.value.trim()) return true;

  const getValue = (): string => {
    switch (condition.field) {
      case "name":
        return item.name;
      case "domain":
        return item.domain ?? "";
      case "tags":
        return [...(item.userTags ?? []), ...(item.sysTags ?? [])].join(" ");
      case "body":
        return item.body;
      case "props":
        return Object.values(item.userProps ?? {}).join(" ");
      case "all":
        return [
          item.name,
          item.domain ?? "",
          ...(item.userTags ?? []),
          ...(item.sysTags ?? []),
          item.body,
          ...Object.values(item.userProps ?? {}),
        ].join(" ");
    }
  };

  const fieldValue = getValue().toLowerCase();
  const searchValue = condition.value.toLowerCase();

  switch (condition.operator) {
    case "contains":
      return fieldValue.includes(searchValue);
    case "equals":
      return fieldValue === searchValue;
    case "startsWith":
      return fieldValue.startsWith(searchValue);
    case "endsWith":
      return fieldValue.endsWith(searchValue);
    case "notContains":
      return !fieldValue.includes(searchValue);
  }
}

/**
 * localStorageのキー
 */
export const SAVED_FILTERS_STORAGE_KEY = "mat-db-saved-filters";

/**
 * 保存フィルターをlocalStorageから読み込む
 */
export function loadSavedFilters(): SavedFilter[] {
  if (typeof window === "undefined") return [];
  try {
    const stored = localStorage.getItem(SAVED_FILTERS_STORAGE_KEY);
    if (!stored) return [];
    return JSON.parse(stored) as SavedFilter[];
  } catch {
    return [];
  }
}

/**
 * 保存フィルターをlocalStorageに保存
 */
export function saveSavedFilters(filters: SavedFilter[]): void {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(SAVED_FILTERS_STORAGE_KEY, JSON.stringify(filters));
  } catch {
    // ignore
  }
}
