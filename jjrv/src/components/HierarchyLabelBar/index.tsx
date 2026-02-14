"use client";

import {
  ChevronDown,
  Filter,
  GripVertical,
  Palette,
  Plus,
  Settings,
  X,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { HierarchySettingsModal } from "@/components/HierarchySettingsModal";
import {
  DEFAULT_HIERARCHY_PRESETS,
  getAvailableHierarchyFields,
  getFieldValue,
} from "@/lib/hierarchy-builder";
import type {
  HierarchyFieldPath,
  HierarchyLevel,
  Relation,
  StringEntity,
} from "@/lib/types";
import { useHierarchyPresets } from "@/lib/use-hierarchy-storage";

type HierarchyLabelBarProps = {
  levels: HierarchyLevel[];
  onLevelsChange: (levels: HierarchyLevel[]) => void;
  showEntityLabel?: boolean;
  /** エンティティを渡すと動的にプロパティを検出してフィールド選択肢に追加 */
  entities?: StringEntity[];
  /** ユーザーIDから表示名へのマッピング（createdByフィールド用） */
  userMap?: Record<string, string>;
  /** Relation情報（relation labelを階層フィールド候補に追加） */
  relations?: Relation[];
};

const DEFAULT_LEVEL_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#d946ef", // fuchsia
  "#ec4899", // pink
  "#f97316", // orange
];

const COLOR_PALETTE = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#d946ef", // fuchsia
  "#ec4899", // pink
  "#f43f5e", // rose
  "#f97316", // orange
  "#eab308", // yellow
  "#84cc16", // lime
  "#22c55e", // green
  "#14b8a6", // teal
  "#06b6d4", // cyan
  "#0ea5e9", // sky
  "#3b82f6", // blue
  "#64748b", // slate
];

/**
 * 階層レベル設定のポップオーバー
 */
function LevelSettingsPopover({
  level,
  entities,
  onUpdate,
  onClose,
  userMap,
}: {
  level: HierarchyLevel;
  entities?: StringEntity[];
  onUpdate: (updates: Partial<HierarchyLevel>) => void;
  onClose: () => void;
  userMap?: Record<string, string>;
}) {
  // このレベルの全ての値を取得（createdByの場合はuserMapで表示名に変換）
  const availableValues = useMemo(() => {
    if (!entities) return [];
    const values = new Set<string>();
    for (const entity of entities) {
      let value = getFieldValue(entity, level.field);
      if (value) {
        // createdByフィールドの場合はuserMapで表示名に変換
        if (level.field === "createdBy" && userMap) {
          value = userMap[value] ?? value;
        }
        values.add(value);
      }
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b, "ja"));
  }, [entities, level.field, userMap]);

  const currentFilter = level.valueFilter ?? [];

  const toggleValue = (value: string) => {
    const newFilter = currentFilter.includes(value)
      ? currentFilter.filter((v) => v !== value)
      : [...currentFilter, value];
    onUpdate({ valueFilter: newFilter.length > 0 ? newFilter : undefined });
  };

  const selectAll = () => {
    onUpdate({ valueFilter: undefined });
  };

  const selectNone = () => {
    onUpdate({ valueFilter: [] });
  };

  return (
    <div className="absolute top-full left-0 mt-1 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 z-30 min-w-[220px]">
      {/* 色設定 */}
      <div className="p-3 border-b border-neutral-100 dark:border-neutral-700">
        <div className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-2">
          <Palette size={12} className="inline mr-1" />
          色の選択
        </div>
        <div className="flex flex-wrap gap-1">
          {COLOR_PALETTE.map((color) => (
            <button
              key={color}
              type="button"
              onClick={() => onUpdate({ color })}
              className={`w-5 h-5 rounded-full border-2 transition-transform hover:scale-110 ${
                level.color === color
                  ? "border-white ring-2 ring-offset-1 ring-neutral-400"
                  : "border-transparent"
              }`}
              style={{ backgroundColor: color }}
              title={color}
            />
          ))}
        </div>
      </div>

      {/* 値フィルター */}
      {availableValues.length > 0 && (
        <div className="p-3">
          <div className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-2 flex items-center justify-between">
            <span>
              <Filter size={12} className="inline mr-1" />
              値でフィルター
            </span>
            <span className="text-neutral-400">
              {currentFilter.length === 0
                ? `全${availableValues.length}件`
                : `${currentFilter.length}/${availableValues.length}件`}
            </span>
          </div>
          <div className="flex gap-1 mb-2">
            <button
              type="button"
              onClick={selectAll}
              className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            >
              全選択
            </button>
            <button
              type="button"
              onClick={selectNone}
              className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            >
              全解除
            </button>
          </div>
          <div className="max-h-40 overflow-y-auto space-y-1">
            {availableValues.map((value) => {
              const isSelected =
                currentFilter.length === 0 || currentFilter.includes(value);
              return (
                <label
                  key={value}
                  className="flex items-center gap-2 px-1 py-0.5 rounded hover:bg-neutral-50 dark:hover:bg-neutral-700 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    checked={isSelected}
                    onChange={() => toggleValue(value)}
                    className="h-3.5 w-3.5 accent-sky-500"
                  />
                  <span className="text-sm text-neutral-700 dark:text-neutral-200 truncate">
                    {value}
                  </span>
                </label>
              );
            })}
          </div>
        </div>
      )}

      {/* 閉じるボタン */}
      <div className="p-2 border-t border-neutral-100 dark:border-neutral-700">
        <button
          type="button"
          onClick={onClose}
          className="w-full text-xs py-1 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
        >
          閉じる
        </button>
      </div>
    </div>
  );
}

/**
 * カスタムプロパティ追加ダイアログ
 */
function CustomFieldDialog({
  onAdd,
  onClose,
}: {
  onAdd: (field: HierarchyFieldPath, label: string) => void;
  onClose: () => void;
}) {
  const [propType, setPropType] = useState<"sysProps" | "userProps">(
    "userProps",
  );
  const [propKey, setPropKey] = useState("");
  const [label, setLabel] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!propKey.trim()) return;
    const field = `${propType}.${propKey.trim()}` as HierarchyFieldPath;
    const displayLabel = label.trim() || propKey.trim();
    onAdd(field, displayLabel);
    onClose();
  };

  return (
    <div className="p-3 space-y-3">
      <div className="text-xs font-semibold text-neutral-500 dark:text-neutral-400">
        カスタムプロパティを追加
      </div>
      <form onSubmit={handleSubmit} className="space-y-2">
        <div className="flex gap-2">
          <select
            value={propType}
            onChange={(e) =>
              setPropType(e.target.value as "sysProps" | "userProps")
            }
            className="text-xs px-2 py-1 rounded border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200"
          >
            <option value="userProps">userProps</option>
            <option value="sysProps">sysProps</option>
          </select>
          <input
            type="text"
            value={propKey}
            onChange={(e) => setPropKey(e.target.value)}
            placeholder="プロパティキー"
            className="flex-1 text-xs px-2 py-1 rounded border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 placeholder:text-neutral-400"
          />
        </div>
        <input
          type="text"
          value={label}
          onChange={(e) => setLabel(e.target.value)}
          placeholder="表示ラベル（省略時はキー名）"
          className="w-full text-xs px-2 py-1 rounded border border-neutral-200 dark:border-neutral-600 bg-white dark:bg-neutral-800 text-neutral-700 dark:text-neutral-200 placeholder:text-neutral-400"
        />
        <div className="flex gap-2 justify-end">
          <button
            type="button"
            onClick={onClose}
            className="text-xs px-3 py-1 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
          >
            キャンセル
          </button>
          <button
            type="submit"
            disabled={!propKey.trim()}
            className="text-xs px-3 py-1 rounded bg-sky-500 hover:bg-sky-600 disabled:bg-neutral-300 disabled:dark:bg-neutral-600 text-white disabled:cursor-not-allowed"
          >
            追加
          </button>
        </div>
      </form>
    </div>
  );
}

export function HierarchyLabelBar({
  levels,
  onLevelsChange,
  showEntityLabel = true,
  entities,
  userMap,
  relations,
}: HierarchyLabelBarProps) {
  const [draggedIndex, setDraggedIndex] = useState<number | null>(null);
  const [dragOverIndex, setDragOverIndex] = useState<number | null>(null);
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showPresetMenu, setShowPresetMenu] = useState(false);
  const [showCustomDialog, setShowCustomDialog] = useState(false);
  const [settingsLevelIndex, setSettingsLevelIndex] = useState<number | null>(
    null,
  );
  const [showSettingsModal, setShowSettingsModal] = useState(false);
  const addButtonRef = useRef<HTMLButtonElement>(null);
  const presetButtonRef = useRef<HTMLButtonElement>(null);
  const { customPresets } = useHierarchyPresets();

  // エンティティとrelationから動的にフィールドを検出 (2-12)
  const availableFields = useMemo(
    () => getAvailableHierarchyFields(entities, relations),
    [entities, relations],
  );

  // 既に使用されているフィールドを除外
  const unusedFields = useMemo(
    () =>
      availableFields.filter((f) => !levels.some((l) => l.field === f.field)),
    [availableFields, levels],
  );

  // グループ別に分類
  const groupedUnusedFields = useMemo(() => {
    const base = unusedFields.filter((f) => f.group === "base");
    const sysProps = unusedFields.filter((f) => f.group === "sysProps");
    const userProps = unusedFields.filter((f) => f.group === "userProps");
    return { base, sysProps, userProps };
  }, [unusedFields]);

  const handleDragStart = useCallback((e: React.DragEvent, index: number) => {
    setDraggedIndex(index);
    e.dataTransfer.effectAllowed = "move";
    e.dataTransfer.setData("text/plain", String(index));
  }, []);

  const handleDragOver = useCallback(
    (e: React.DragEvent, index: number) => {
      e.preventDefault();
      e.dataTransfer.dropEffect = "move";
      if (draggedIndex !== null && draggedIndex !== index) {
        setDragOverIndex(index);
      }
    },
    [draggedIndex],
  );

  const handleDragLeave = useCallback(() => {
    setDragOverIndex(null);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent, dropIndex: number) => {
      e.preventDefault();
      if (draggedIndex === null || draggedIndex === dropIndex) {
        setDraggedIndex(null);
        setDragOverIndex(null);
        return;
      }

      const newLevels = [...levels];
      const [removed] = newLevels.splice(draggedIndex, 1);
      newLevels.splice(dropIndex, 0, removed);
      onLevelsChange(newLevels);

      setDraggedIndex(null);
      setDragOverIndex(null);
    },
    [draggedIndex, levels, onLevelsChange],
  );

  const handleDragEnd = useCallback(() => {
    setDraggedIndex(null);
    setDragOverIndex(null);
  }, []);

  const handleRemoveLevel = useCallback(
    (index: number) => {
      const newLevels = levels.filter((_, i) => i !== index);
      onLevelsChange(newLevels);
    },
    [levels, onLevelsChange],
  );

  const handleAddLevel = useCallback(
    (field: HierarchyFieldPath, label: string) => {
      const newLevel: HierarchyLevel = {
        id: field,
        label,
        field,
        color:
          DEFAULT_LEVEL_COLORS[levels.length % DEFAULT_LEVEL_COLORS.length],
      };
      onLevelsChange([...levels, newLevel]);
      setShowAddMenu(false);
      setShowCustomDialog(false);
    },
    [levels, onLevelsChange],
  );

  const handleApplyPreset = useCallback(
    (presetId: string) => {
      const defaultPreset = DEFAULT_HIERARCHY_PRESETS.find(
        (p) => p.id === presetId,
      );
      if (defaultPreset) {
        onLevelsChange([...defaultPreset.levels]);
        setShowPresetMenu(false);
        return;
      }
      const custom = customPresets.find((p) => p.id === presetId);
      if (custom) {
        onLevelsChange([...custom.levels]);
      }
      setShowPresetMenu(false);
    },
    [onLevelsChange, customPresets],
  );

  const handleUpdateLevel = useCallback(
    (index: number, updates: Partial<HierarchyLevel>) => {
      const newLevels = levels.map((level, i) =>
        i === index ? { ...level, ...updates } : level,
      );
      onLevelsChange(newLevels);
    },
    [levels, onLevelsChange],
  );

  const closeAllMenus = useCallback(() => {
    setShowAddMenu(false);
    setShowPresetMenu(false);
    setShowCustomDialog(false);
    setSettingsLevelIndex(null);
  }, []);

  return (
    <div className="relative flex items-center gap-1 px-3 py-2 bg-neutral-100 dark:bg-neutral-800 rounded-lg border border-neutral-200 dark:border-neutral-700">
      {/* プリセット選択 */}
      <div className="relative">
        <button
          ref={presetButtonRef}
          type="button"
          onClick={() => {
            setShowPresetMenu(!showPresetMenu);
            setShowAddMenu(false);
          }}
          className="px-2 py-1 text-xs rounded bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300 transition-colors"
          title="プリセット選択"
        >
          プリセット
        </button>
        {showPresetMenu && (
          <div className="absolute top-full left-0 mt-1 py-1 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 z-20 min-w-[180px]">
            {DEFAULT_HIERARCHY_PRESETS.map((preset) => (
              <button
                key={preset.id}
                type="button"
                onClick={() => handleApplyPreset(preset.id)}
                className="w-full px-3 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
              >
                <div className="font-medium">{preset.name}</div>
                {preset.description && (
                  <div className="text-xs text-neutral-500 dark:text-neutral-400">
                    {preset.description}
                  </div>
                )}
              </button>
            ))}
            {customPresets.length > 0 && (
              <>
                <div className="border-t border-neutral-100 dark:border-neutral-700 my-1" />
                <div className="px-3 py-1 text-xs font-semibold text-neutral-500 dark:text-neutral-400">
                  カスタム
                </div>
                {customPresets.map((preset) => (
                  <button
                    key={preset.id}
                    type="button"
                    onClick={() => handleApplyPreset(preset.id)}
                    className="w-full px-3 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
                  >
                    <div className="font-medium">{preset.name}</div>
                    {preset.description && (
                      <div className="text-xs text-neutral-500 dark:text-neutral-400">
                        {preset.description}
                      </div>
                    )}
                  </button>
                ))}
              </>
            )}
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-neutral-300 dark:bg-neutral-600 mx-1" />

      {/* 階層ラベル */}
      <div className="flex items-center gap-1 flex-wrap">
        {levels.map((level, index) => {
          const hasFilter = level.valueFilter && level.valueFilter.length > 0;
          return (
            <div key={level.id} className="relative">
              {/* biome-ignore lint/a11y/noStaticElementInteractions: draggable element for reordering */}
              <div
                draggable
                onDragStart={(e) => handleDragStart(e, index)}
                onDragOver={(e) => handleDragOver(e, index)}
                onDragLeave={handleDragLeave}
                onDrop={(e) => handleDrop(e, index)}
                onDragEnd={handleDragEnd}
                className={`
                  flex items-center gap-1 px-2 py-1 rounded-md text-white text-xs font-medium
                  cursor-grab active:cursor-grabbing select-none transition-all
                  ${draggedIndex === index ? "opacity-50 scale-95" : ""}
                  ${dragOverIndex === index ? "ring-2 ring-white ring-offset-1" : ""}
                `}
                style={{ backgroundColor: level.color }}
              >
                <GripVertical className="w-3 h-3 opacity-60" />
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    setSettingsLevelIndex(
                      settingsLevelIndex === index ? null : index,
                    );
                    setShowAddMenu(false);
                    setShowPresetMenu(false);
                  }}
                  className="flex items-center gap-1 hover:bg-white/10 rounded px-0.5 transition-colors"
                  title="設定を開く"
                >
                  <span>{level.label}</span>
                  {hasFilter && <Filter className="w-3 h-3 opacity-80" />}
                  <ChevronDown className="w-3 h-3 opacity-60" />
                </button>
                <button
                  type="button"
                  onClick={(e) => {
                    e.stopPropagation();
                    handleRemoveLevel(index);
                  }}
                  className="ml-0.5 p-0.5 rounded hover:bg-white/20 transition-colors"
                  title={`${level.label}を削除`}
                >
                  <X className="w-3 h-3" />
                </button>
              </div>
              {/* 設定ポップオーバー */}
              {settingsLevelIndex === index && (
                <LevelSettingsPopover
                  level={level}
                  entities={entities}
                  onUpdate={(updates) => handleUpdateLevel(index, updates)}
                  onClose={() => setSettingsLevelIndex(null)}
                  userMap={userMap}
                />
              )}
            </div>
          );
        })}

        {levels.length > 0 && (
          <span className="text-neutral-400 dark:text-neutral-500 mx-1">→</span>
        )}

        {/* エンティティラベル（固定） */}
        {showEntityLabel && (
          <div className="flex items-center gap-1 px-2 py-1 rounded-md bg-slate-500 text-white text-xs font-medium">
            <span>エンティティ</span>
          </div>
        )}
      </div>

      <div className="w-px h-5 bg-neutral-300 dark:bg-neutral-600 mx-1" />

      {/* 追加ボタン */}
      <div className="relative">
        <button
          ref={addButtonRef}
          type="button"
          onClick={() => {
            setShowAddMenu(!showAddMenu);
            setShowPresetMenu(false);
            setShowCustomDialog(false);
            setSettingsLevelIndex(null);
          }}
          className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-blue-500 hover:bg-blue-600 text-white transition-colors"
          title="階層を追加"
        >
          <Plus className="w-3 h-3" />
          追加
        </button>
        {showAddMenu && (
          <div className="absolute top-full right-0 mt-1 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 z-20 min-w-[200px] max-h-[400px] overflow-y-auto">
            {showCustomDialog ? (
              <CustomFieldDialog
                onAdd={handleAddLevel}
                onClose={() => setShowCustomDialog(false)}
              />
            ) : (
              <div className="py-1">
                {/* カスタムフィールド追加ボタン */}
                <button
                  type="button"
                  onClick={() => setShowCustomDialog(true)}
                  className="w-full px-3 py-2 text-left text-sm hover:bg-sky-50 dark:hover:bg-sky-900/30 text-sky-600 dark:text-sky-400 border-b border-neutral-100 dark:border-neutral-700 flex items-center gap-2"
                >
                  <Plus className="w-4 h-4" />
                  カスタムプロパティを追加...
                </button>

                {/* 基本フィールド */}
                {groupedUnusedFields.base.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 border-b border-neutral-100 dark:border-neutral-700">
                      基本フィールド
                    </div>
                    {groupedUnusedFields.base.map((item) => (
                      <button
                        key={item.field}
                        type="button"
                        onClick={() => handleAddLevel(item.field, item.label)}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
                      >
                        {item.label}
                      </button>
                    ))}
                  </>
                )}
                {/* システムプロパティ */}
                {groupedUnusedFields.sysProps.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 border-b border-neutral-100 dark:border-neutral-700 mt-1">
                      システムプロパティ
                    </div>
                    {groupedUnusedFields.sysProps.map((item) => (
                      <button
                        key={item.field}
                        type="button"
                        onClick={() => handleAddLevel(item.field, item.label)}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
                      >
                        {item.label}
                      </button>
                    ))}
                  </>
                )}
                {/* ユーザープロパティ */}
                {groupedUnusedFields.userProps.length > 0 && (
                  <>
                    <div className="px-3 py-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 border-b border-neutral-100 dark:border-neutral-700 mt-1">
                      ユーザープロパティ
                    </div>
                    {groupedUnusedFields.userProps.map((item) => (
                      <button
                        key={item.field}
                        type="button"
                        onClick={() => handleAddLevel(item.field, item.label)}
                        className="w-full px-3 py-2 text-left text-sm hover:bg-neutral-100 dark:hover:bg-neutral-700 text-neutral-700 dark:text-neutral-200"
                      >
                        {item.label}
                      </button>
                    ))}
                  </>
                )}

                {/* フィールドがない場合 */}
                {unusedFields.length === 0 && (
                  <div className="px-3 py-2 text-sm text-neutral-500 dark:text-neutral-400">
                    全てのフィールドが使用中です
                  </div>
                )}
              </div>
            )}
          </div>
        )}
      </div>

      {/* 設定ボタン */}
      <button
        type="button"
        onClick={() => {
          closeAllMenus();
          setShowSettingsModal(true);
        }}
        className="flex items-center gap-1 px-2 py-1 text-xs rounded bg-neutral-200 dark:bg-neutral-700 hover:bg-neutral-300 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300 transition-colors"
        title="グループ化設定"
      >
        <Settings className="w-3 h-3" />
      </button>

      {/* 設定モーダル */}
      <HierarchySettingsModal
        isOpen={showSettingsModal}
        onClose={() => setShowSettingsModal(false)}
        levels={levels}
        onLevelsChange={onLevelsChange}
        entities={entities}
        userMap={userMap}
      />

      {/* クリックアウトで閉じる */}
      {(showAddMenu || showPresetMenu || settingsLevelIndex !== null) && (
        // biome-ignore lint/a11y/useKeyWithClickEvents lint/a11y/noStaticElementInteractions: click-outside handler
        <div className="fixed inset-0 z-10" onClick={closeAllMenus} />
      )}
    </div>
  );
}
