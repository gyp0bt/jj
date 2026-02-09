"use client";

import { CheckSquare, Edit3, Tag } from "lucide-react";
import { useId, useMemo, useState } from "react";

export type BatchEditItem = {
  id: string;
  name: string;
  body: string;
  sourcePath: string;
  tags: string[];
  props: Record<string, string>;
  selected: boolean;
};

type BatchEntityEditorProps = {
  items: BatchEditItem[];
  onChange: (items: BatchEditItem[]) => void;
  onApplyTags: (tags: string[]) => void;
  onApplyProps: (props: Record<string, string>) => void;
  className?: string;
};

const parseTags = (value: string) =>
  value
    .split(/[\s,]+/)
    .map((tag) => tag.trim())
    .filter(Boolean);

const parseProps = (value: string) => {
  const result: Record<string, string> = {};
  value
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean)
    .forEach((line) => {
      const [key, ...rest] = line.split("=");
      if (!key) return;
      const val = rest.join("=").trim();
      result[key.trim()] = val;
    });
  return result;
};

export function BatchEntityEditor({
  items,
  onChange,
  onApplyTags,
  onApplyProps,
  className = "",
}: BatchEntityEditorProps) {
  const [bulkTags, setBulkTags] = useState("");
  const [bulkProps, setBulkProps] = useState("");
  const bulkTagsId = useId();
  const bulkPropsId = useId();

  const selectedCount = useMemo(
    () => items.filter((item) => item.selected).length,
    [items],
  );

  const updateItem = (id: string, partial: Partial<BatchEditItem>) => {
    onChange(
      items.map((item) => (item.id === id ? { ...item, ...partial } : item)),
    );
  };

  const toggleAll = (next: boolean) => {
    onChange(items.map((item) => ({ ...item, selected: next })));
  };

  return (
    <div
      className={`rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/60 p-4 ${className}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex items-center gap-2 text-sm font-semibold text-neutral-600 dark:text-neutral-300">
          <Edit3 size={16} />
          一括編集
        </div>
        <button
          type="button"
          onClick={() => toggleAll(true)}
          className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
        >
          全選択
        </button>
        <button
          type="button"
          onClick={() => toggleAll(false)}
          className="text-xs text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
        >
          全解除
        </button>
        <span className="text-xs text-neutral-500">選択: {selectedCount}</span>
      </div>

      <div className="mt-4 grid gap-3 md:grid-cols-2">
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
          <label
            htmlFor={bulkTagsId}
            className="flex items-center gap-2 text-xs text-neutral-500 mb-2"
          >
            <Tag size={12} />
            一括タグ（空白/カンマ区切り）
          </label>
          <input
            id={bulkTagsId}
            type="text"
            value={bulkTags}
            onChange={(e) => setBulkTags(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => onApplyTags(parseTags(bulkTags))}
            className="mt-2 inline-flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            <CheckSquare size={12} />
            選択へ適用
          </button>
        </div>
        <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
          <label
            htmlFor={bulkPropsId}
            className="flex items-center gap-2 text-xs text-neutral-500 mb-2"
          >
            プロパティ一括（key=value）
          </label>
          <textarea
            id={bulkPropsId}
            rows={3}
            value={bulkProps}
            onChange={(e) => setBulkProps(e.target.value)}
            className="w-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-2 text-sm"
          />
          <button
            type="button"
            onClick={() => onApplyProps(parseProps(bulkProps))}
            className="mt-2 inline-flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-50 dark:hover:bg-neutral-800"
          >
            <CheckSquare size={12} />
            選択へ適用
          </button>
        </div>
      </div>

      <div className="mt-4 space-y-3">
        {items.map((item) => (
          <div
            key={item.id}
            className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3"
          >
            <div className="flex flex-wrap items-center gap-3">
              <label className="inline-flex items-center gap-2 text-xs text-neutral-500">
                <input
                  type="checkbox"
                  checked={item.selected}
                  onChange={(e) =>
                    updateItem(item.id, { selected: e.target.checked })
                  }
                />
                選択
              </label>
              <span className="text-xs text-neutral-500 truncate">
                {item.sourcePath}
              </span>
            </div>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <input
                type="text"
                value={item.name}
                onChange={(e) => updateItem(item.id, { name: e.target.value })}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-2 text-sm"
                placeholder="材料名"
              />
              <input
                type="text"
                value={item.tags.join(" ")}
                onChange={(e) =>
                  updateItem(item.id, { tags: parseTags(e.target.value) })
                }
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-2 text-sm"
                placeholder="タグ"
              />
            </div>
            <textarea
              rows={4}
              value={item.body}
              onChange={(e) => updateItem(item.id, { body: e.target.value })}
              className="mt-2 w-full rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-2 text-xs"
            />
          </div>
        ))}
      </div>
    </div>
  );
}
