"use client";

import { ChevronDown, ChevronUp, Link2, Tag, X } from "lucide-react";
import { useMemo, useState } from "react";
import {
  BodyRenderer,
  detectFormat,
  formatLabel,
} from "@/components/BodyRenderer";
import type { Relation, StringEntity } from "@/lib/types";

type EntityEditPanelProps = {
  entity: StringEntity;
  onChange: (entity: StringEntity) => void;
  onClose?: () => void;
  /** body 表示を初期時に閉じる */
  bodyCollapsed?: boolean;
  /** Relation一覧 */
  relations?: Relation[];
  /** 全エンティティ（relation先のnameを解決するために使用） */
  allEntities?: StringEntity[];
  /** Relation変更コールバック */
  onRelationsChange?: (relations: Relation[]) => void;
};

export function EntityEditPanel({
  entity,
  onChange,
  onClose,
  bodyCollapsed = false,
  relations,
  allEntities,
  onRelationsChange,
}: EntityEditPanelProps) {
  const [tagInput, setTagInput] = useState("");
  const [propInput, setPropInput] = useState("");
  const [showBody, setShowBody] = useState(!bodyCollapsed);
  const [relationInput, setRelationInput] = useState("");

  const detectedFormat = useMemo(() => detectFormat(entity), [entity]);

  // このエンティティに関連するRelation
  const entityRelations = useMemo(() => {
    if (!relations) return [];
    return relations.filter(
      (r) => r.entity1Id === entity.id || r.entity2Id === entity.id,
    );
  }, [relations, entity.id]);

  // 全エンティティのマップ
  const entityMap = useMemo(() => {
    if (!allEntities) return new Map<string, StringEntity>();
    return new Map(allEntities.map((e) => [e.id, e]));
  }, [allEntities]);

  const update = <K extends keyof StringEntity>(
    key: K,
    value: StringEntity[K],
  ) => {
    onChange({ ...entity, [key]: value });
  };

  /* ---- tag helpers ---- */
  const addTag = () => {
    const v = tagInput.trim();
    if (!v) return;
    setTagInput("");
    // key:value はプロパティとして追加
    if (v.includes(":")) {
      const idx = v.indexOf(":");
      const k = v.slice(0, idx).trim();
      const val = v.slice(idx + 1).trim();
      if (k && val) {
        update("userProps", { ...entity.userProps, [k]: val });
        return;
      }
    }
    const key = v.toLowerCase();
    if (!entity.userTags.some((t) => t.toLowerCase() === key)) {
      update("userTags", [...entity.userTags, v]);
    }
  };

  const removeTag = (tag: string) => {
    update(
      "userTags",
      entity.userTags.filter((t) => t !== tag),
    );
  };

  /* ---- prop helpers ---- */
  const addProp = () => {
    const raw = propInput.trim();
    if (!raw) return;
    const idx = raw.indexOf(":");
    if (idx < 1) return;
    const k = raw.slice(0, idx).trim();
    const v = raw.slice(idx + 1).trim();
    if (!k || !v) return;
    update("userProps", { ...entity.userProps, [k]: v });
    setPropInput("");
  };

  const removeProp = (key: string) => {
    const next = { ...entity.userProps };
    delete next[key];
    update("userProps", next);
  };

  /* ---- relation helpers ---- */
  const addRelation = () => {
    if (!onRelationsChange || !relations || !allEntities) return;
    const raw = relationInput.trim();
    if (!raw) return;
    // フォーマット: label:entityName
    const idx = raw.indexOf(":");
    if (idx < 1) return;
    const label = raw.slice(0, idx).trim();
    const targetName = raw.slice(idx + 1).trim();
    if (!label || !targetName) return;

    // ターゲットエンティティを名前で検索
    const target = allEntities.find(
      (e) =>
        e.id !== entity.id && e.name.toLowerCase() === targetName.toLowerCase(),
    );
    if (!target) {
      // 新しいエンティティを作成してrelationを追加（StringEntity）
      const newEntity: StringEntity = {
        id: crypto.randomUUID(),
        name: targetName,
        body: `${label}: ${targetName}`,
        sysTags: [label.toLowerCase()],
        userTags: [],
        sysProps: { type: label },
        userProps: {},
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      // allEntitiesに新しいエンティティを追加（コールバックは親で管理）
      const newRelation: Relation = {
        id: crypto.randomUUID(),
        label,
        entity1Id: entity.id,
        entity2Id: newEntity.id,
        createdAt: new Date().toISOString(),
      };
      onRelationsChange([...relations, newRelation]);
      setRelationInput("");
      return;
    }

    const newRelation: Relation = {
      id: crypto.randomUUID(),
      label,
      entity1Id: entity.id,
      entity2Id: target.id,
      createdAt: new Date().toISOString(),
    };
    onRelationsChange([...relations, newRelation]);
    setRelationInput("");
  };

  const removeRelation = (relationId: string) => {
    if (!onRelationsChange || !relations) return;
    onRelationsChange(relations.filter((r) => r.id !== relationId));
  };

  return (
    <div className="space-y-3 text-sm">
      {/* Header */}
      {onClose && (
        <div className="flex items-center justify-between pb-2 border-b border-neutral-200 dark:border-neutral-700">
          <span className="font-medium text-neutral-700 dark:text-neutral-200 truncate text-base">
            {entity.name || "無題"}
          </span>
          <button
            type="button"
            onClick={onClose}
            className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800"
          >
            <X size={16} />
          </button>
        </div>
      )}

      {/* Name */}
      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
          名前
        </label>
        <input
          value={entity.name}
          onChange={(e) => update("name", e.target.value)}
          className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2 text-sm"
          placeholder="表示名"
        />
      </div>

      {/* Tags */}
      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
          タグ（space/enterで追加）
        </label>
        <div className="rounded-xl border border-neutral-300 dark:border-neutral-700 px-2 py-1.5 bg-white dark:bg-neutral-900">
          <div className="flex flex-wrap items-center gap-1.5">
            {entity.userTags.map((t) => (
              <span
                key={t}
                className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium border-sky-300/80 dark:border-sky-700/80 bg-sky-50/80 dark:bg-sky-800/60 text-sky-900 dark:text-sky-100"
              >
                <Tag size={10} /> {t}
                <button
                  type="button"
                  onClick={() => removeTag(t)}
                  className="ml-0.5 hover:text-red-500"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            <input
              value={tagInput}
              onChange={(e) => setTagInput(e.target.value)}
              onKeyDown={(e) => {
                if ((e.key === "Enter" || e.key === " ") && tagInput.trim()) {
                  e.preventDefault();
                  addTag();
                }
                if (
                  e.key === "Backspace" &&
                  !tagInput &&
                  entity.userTags.length
                ) {
                  update("userTags", entity.userTags.slice(0, -1));
                }
              }}
              placeholder="#タグ名 または key:value"
              className="flex-1 min-w-[100px] bg-transparent outline-none py-0.5 text-xs"
            />
          </div>
        </div>
      </div>

      {/* Properties */}
      <div>
        <label className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1">
          プロパティ（key:value／space・enterで追加）
        </label>
        <div className="rounded-xl border border-neutral-300 dark:border-neutral-700 px-2 py-1.5 bg-white dark:bg-neutral-900">
          <div className="flex flex-wrap items-center gap-1.5">
            {Object.entries(entity.userProps).map(([k, v]) => (
              <span
                key={k}
                className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium border-teal-300/80 dark:border-teal-700/80 bg-teal-50/80 dark:bg-teal-800/60 text-teal-900 dark:text-teal-100"
              >
                {k}:{v}
                <button
                  type="button"
                  onClick={() => removeProp(k)}
                  className="ml-0.5 hover:text-red-500"
                >
                  <X size={10} />
                </button>
              </span>
            ))}
            <input
              value={propInput}
              onChange={(e) => setPropInput(e.target.value)}
              onKeyDown={(e) => {
                if (
                  (e.key === "Enter" || e.key === " ") &&
                  propInput.includes(":")
                ) {
                  e.preventDefault();
                  addProp();
                }
                if (
                  e.key === "Backspace" &&
                  !propInput &&
                  Object.keys(entity.userProps).length
                ) {
                  const keys = Object.keys(entity.userProps);
                  const last = keys[keys.length - 1];
                  if (last) removeProp(last);
                }
              }}
              placeholder="例: project:PRJ-1234"
              className="flex-1 min-w-[120px] bg-transparent outline-none py-0.5 text-xs"
            />
          </div>
        </div>
      </div>

      {/* Relations */}
      {onRelationsChange && relations && (
        <div>
          <label className="block text-xs font-medium text-purple-600 dark:text-purple-400 mb-1">
            <span className="inline-flex items-center gap-1">
              <Link2 size={11} />
              Relation（label:対象名／enterで追加）
            </span>
          </label>
          <div className="rounded-xl border border-purple-300/80 dark:border-purple-700/80 px-2 py-1.5 bg-white dark:bg-neutral-900">
            <div className="flex flex-wrap items-center gap-1.5">
              {entityRelations.map((rel) => {
                const targetId =
                  rel.entity1Id === entity.id ? rel.entity2Id : rel.entity1Id;
                const target = entityMap.get(targetId);
                return (
                  <span
                    key={rel.id}
                    className="inline-flex items-center gap-1 whitespace-nowrap rounded-full border px-2 py-0.5 text-[11px] font-medium border-purple-300/80 dark:border-purple-700/80 bg-purple-50/80 dark:bg-purple-800/60 text-purple-900 dark:text-purple-100"
                  >
                    <Link2 size={10} />
                    {rel.label}:{target?.name ?? targetId}
                    <button
                      type="button"
                      onClick={() => removeRelation(rel.id)}
                      className="ml-0.5 hover:text-red-500"
                    >
                      <X size={10} />
                    </button>
                  </span>
                );
              })}
              <input
                value={relationInput}
                onChange={(e) => setRelationInput(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && relationInput.includes(":")) {
                    e.preventDefault();
                    addRelation();
                  }
                }}
                placeholder="例: カテゴリ:金属"
                className="flex-1 min-w-[140px] bg-transparent outline-none py-0.5 text-xs"
              />
            </div>
          </div>
        </div>
      )}

      {/* Body */}
      <div>
        <button
          type="button"
          onClick={() => setShowBody(!showBody)}
          className="flex items-center gap-1 text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1 hover:text-neutral-700 dark:hover:text-neutral-200"
        >
          本文
          {detectedFormat && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800">
              {formatLabel(detectedFormat)}
            </span>
          )}
          {showBody ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
        </button>
        {showBody && (
          <div className="space-y-2">
            <textarea
              value={entity.body}
              onChange={(e) => update("body", e.target.value)}
              rows={6}
              className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-2 font-mono text-[11px] leading-snug"
            />
            {entity.body.trim() && (
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-2 max-h-32 overflow-y-auto">
                <BodyRenderer entity={entity} maxLines={8} />
              </div>
            )}
          </div>
        )}
      </div>

      {/* System properties (read-only) */}
      {Object.keys(entity.sysProps).length > 0 && (
        <div className="pt-2 border-t border-neutral-200 dark:border-neutral-700">
          <div className="text-[10px] text-neutral-400 flex flex-wrap gap-x-3 gap-y-0.5">
            {Object.entries(entity.sysProps).map(([k, v]) => (
              <span key={k}>
                {k}: {v}
              </span>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
