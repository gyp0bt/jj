"use client";

import {
  ChevronDown,
  ChevronUp,
  Filter,
  Plus,
  Save,
  Settings,
  Trash2,
  X,
} from "lucide-react";
import { useCallback, useMemo, useState } from "react";
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

type HierarchySettingsModalProps = {
  isOpen: boolean;
  onClose: () => void;
  levels: HierarchyLevel[];
  onLevelsChange: (levels: HierarchyLevel[]) => void;
  entities?: StringEntity[];
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
  "#6366f1",
  "#8b5cf6",
  "#a855f7",
  "#d946ef",
  "#ec4899",
  "#f43f5e",
  "#f97316",
  "#eab308",
  "#84cc16",
  "#22c55e",
  "#14b8a6",
  "#06b6d4",
  "#0ea5e9",
  "#3b82f6",
  "#64748b",
];

/**
 * 階層レベル設定項目
 */
function LevelItem({
  level,
  index,
  totalCount,
  entities,
  userMap,
  onUpdate,
  onRemove,
  onMoveUp,
  onMoveDown,
}: {
  level: HierarchyLevel;
  index: number;
  totalCount: number;
  entities?: StringEntity[];
  userMap?: Record<string, string>;
  onUpdate: (updates: Partial<HierarchyLevel>) => void;
  onRemove: () => void;
  onMoveUp: () => void;
  onMoveDown: () => void;
}) {
  const [showColorPicker, setShowColorPicker] = useState(false);
  const [showValueFilter, setShowValueFilter] = useState(false);

  // このレベルの全ての値を取得
  const availableValues = useMemo(() => {
    if (!entities) return [];
    const values = new Set<string>();
    for (const entity of entities) {
      let value = getFieldValue(entity, level.field);
      if (value) {
        if (level.field === "createdBy" && userMap) {
          value = userMap[value] ?? value;
        }
        values.add(value);
      }
    }
    return Array.from(values).sort((a, b) => a.localeCompare(b, "ja"));
  }, [entities, level.field, userMap]);

  const currentFilter = level.valueFilter ?? [];
  const hasFilter = currentFilter.length > 0;

  const toggleValue = (value: string) => {
    const newFilter = currentFilter.includes(value)
      ? currentFilter.filter((v) => v !== value)
      : [...currentFilter, value];
    onUpdate({ valueFilter: newFilter.length > 0 ? newFilter : undefined });
  };

  return (
    <div className="border border-neutral-200 dark:border-neutral-700 rounded-lg p-3 bg-white dark:bg-neutral-800">
      <div className="flex items-center gap-3">
        {/* 順序変更ボタン */}
        <div className="flex flex-col gap-0.5">
          <button
            type="button"
            onClick={onMoveUp}
            disabled={index === 0}
            className="p-0.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded disabled:opacity-30"
            title="上に移動"
          >
            <ChevronUp size={14} />
          </button>
          <button
            type="button"
            onClick={onMoveDown}
            disabled={index === totalCount - 1}
            className="p-0.5 hover:bg-neutral-100 dark:hover:bg-neutral-700 rounded disabled:opacity-30"
            title="下に移動"
          >
            <ChevronDown size={14} />
          </button>
        </div>

        {/* 色インジケーター */}
        <div className="relative">
          <button
            type="button"
            onClick={() => setShowColorPicker(!showColorPicker)}
            className="w-6 h-6 rounded-full border-2 border-white shadow-sm"
            style={{ backgroundColor: level.color }}
            title="色を変更"
          />
          {showColorPicker && (
            <div className="absolute top-8 left-0 z-20 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 p-2">
              <div className="flex flex-wrap gap-1 w-40">
                {COLOR_PALETTE.map((color) => (
                  <button
                    key={color}
                    type="button"
                    onClick={() => {
                      onUpdate({ color });
                      setShowColorPicker(false);
                    }}
                    className={`w-5 h-5 rounded-full border-2 transition-transform hover:scale-110 ${
                      level.color === color
                        ? "border-white ring-2 ring-offset-1 ring-neutral-400"
                        : "border-transparent"
                    }`}
                    style={{ backgroundColor: color }}
                  />
                ))}
              </div>
            </div>
          )}
        </div>

        {/* ラベル編集 */}
        <input
          type="text"
          value={level.label}
          onChange={(e) => onUpdate({ label: e.target.value })}
          className="flex-1 px-2 py-1 text-sm border border-neutral-200 dark:border-neutral-600 rounded bg-transparent focus:outline-none focus:ring-1 focus:ring-sky-400"
        />

        {/* フィールド表示 */}
        <span className="text-xs text-neutral-500 dark:text-neutral-400 bg-neutral-100 dark:bg-neutral-700 px-2 py-1 rounded">
          {level.field}
        </span>

        {/* フィルターボタン */}
        {availableValues.length > 0 && (
          <button
            type="button"
            onClick={() => setShowValueFilter(!showValueFilter)}
            className={`p-1.5 rounded ${
              hasFilter
                ? "bg-sky-100 text-sky-600 dark:bg-sky-900/40 dark:text-sky-400"
                : "hover:bg-neutral-100 dark:hover:bg-neutral-700"
            }`}
            title="値フィルター"
          >
            <Filter size={14} />
          </button>
        )}

        {/* 削除ボタン */}
        <button
          type="button"
          onClick={onRemove}
          className="p-1.5 text-red-500 hover:bg-red-50 dark:hover:bg-red-900/20 rounded"
          title="削除"
        >
          <Trash2 size={14} />
        </button>
      </div>

      {/* 値フィルター */}
      {showValueFilter && availableValues.length > 0 && (
        <div className="mt-3 pt-3 border-t border-neutral-200 dark:border-neutral-700">
          <div className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 mb-2 flex items-center justify-between">
            <span>値でフィルター</span>
            <span className="text-neutral-400">
              {currentFilter.length === 0
                ? `全${availableValues.length}件`
                : `${currentFilter.length}/${availableValues.length}件`}
            </span>
          </div>
          <div className="flex gap-1 mb-2">
            <button
              type="button"
              onClick={() => onUpdate({ valueFilter: undefined })}
              className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            >
              全選択
            </button>
            <button
              type="button"
              onClick={() => onUpdate({ valueFilter: [] })}
              className="text-xs px-2 py-0.5 rounded bg-neutral-100 dark:bg-neutral-700 hover:bg-neutral-200 dark:hover:bg-neutral-600 text-neutral-600 dark:text-neutral-300"
            >
              全解除
            </button>
          </div>
          <div className="max-h-32 overflow-y-auto space-y-1">
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
    </div>
  );
}

export function HierarchySettingsModal({
  isOpen,
  onClose,
  levels,
  onLevelsChange,
  entities,
  userMap,
  relations,
}: HierarchySettingsModalProps) {
  const [showAddMenu, setShowAddMenu] = useState(false);
  const [showSavePreset, setShowSavePreset] = useState(false);
  const [presetName, setPresetName] = useState("");
  const { customPresets, savePreset, deletePreset } = useHierarchyPresets();

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
    },
    [levels, onLevelsChange],
  );

  const handleRemoveLevel = useCallback(
    (index: number) => {
      onLevelsChange(levels.filter((_, i) => i !== index));
    },
    [levels, onLevelsChange],
  );

  const handleUpdateLevel = useCallback(
    (index: number, updates: Partial<HierarchyLevel>) => {
      onLevelsChange(
        levels.map((level, i) =>
          i === index ? { ...level, ...updates } : level,
        ),
      );
    },
    [levels, onLevelsChange],
  );

  const handleMoveUp = useCallback(
    (index: number) => {
      if (index === 0) return;
      const newLevels = [...levels];
      [newLevels[index - 1], newLevels[index]] = [
        newLevels[index],
        newLevels[index - 1],
      ];
      onLevelsChange(newLevels);
    },
    [levels, onLevelsChange],
  );

  const handleMoveDown = useCallback(
    (index: number) => {
      if (index === levels.length - 1) return;
      const newLevels = [...levels];
      [newLevels[index], newLevels[index + 1]] = [
        newLevels[index + 1],
        newLevels[index],
      ];
      onLevelsChange(newLevels);
    },
    [levels, onLevelsChange],
  );

  const handleApplyPreset = useCallback(
    (presetId: string) => {
      // まずデフォルトプリセットを検索
      const defaultPreset = DEFAULT_HIERARCHY_PRESETS.find(
        (p) => p.id === presetId,
      );
      if (defaultPreset) {
        onLevelsChange([...defaultPreset.levels]);
        return;
      }
      // カスタムプリセットを検索
      const custom = customPresets.find((p) => p.id === presetId);
      if (custom) {
        onLevelsChange([...custom.levels]);
      }
    },
    [onLevelsChange, customPresets],
  );

  const handleSavePreset = useCallback(() => {
    if (!presetName.trim() || levels.length === 0) return;
    savePreset(presetName.trim(), "", levels);
    setPresetName("");
    setShowSavePreset(false);
  }, [presetName, levels, savePreset]);

  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      {/* オーバーレイ */}
      {/* biome-ignore lint/a11y/useKeyWithClickEvents lint/a11y/noStaticElementInteractions: click-outside handler */}
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />

      {/* モーダル */}
      <div className="relative bg-white dark:bg-neutral-900 rounded-2xl shadow-2xl w-full max-w-lg max-h-[80vh] overflow-hidden flex flex-col mx-4">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-900 dark:text-neutral-100 flex items-center gap-2">
            <Settings size={20} />
            グループ化設定
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
          >
            <X size={20} />
          </button>
        </div>

        {/* コンテンツ */}
        <div className="flex-1 overflow-y-auto p-6 space-y-4">
          {/* プリセット選択 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                プリセット
              </span>
              {levels.length > 0 && (
                <button
                  type="button"
                  onClick={() => setShowSavePreset(!showSavePreset)}
                  className="flex items-center gap-1 text-xs text-sky-600 hover:text-sky-700 dark:text-sky-400"
                >
                  <Save size={12} />
                  現在の設定を保存
                </button>
              )}
            </div>

            {/* プリセット保存フォーム */}
            {showSavePreset && (
              <div className="mb-2 flex gap-2">
                <input
                  type="text"
                  value={presetName}
                  onChange={(e) => setPresetName(e.target.value)}
                  placeholder="プリセット名を入力..."
                  className="flex-1 px-3 py-1.5 text-sm border border-neutral-200 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 focus:outline-none focus:ring-1 focus:ring-sky-400"
                  onKeyDown={(e) => {
                    if (e.key === "Enter") handleSavePreset();
                  }}
                />
                <button
                  type="button"
                  onClick={handleSavePreset}
                  disabled={!presetName.trim()}
                  className="px-3 py-1.5 text-sm bg-sky-500 hover:bg-sky-600 disabled:bg-neutral-300 text-white rounded-lg disabled:cursor-not-allowed"
                >
                  保存
                </button>
              </div>
            )}

            <select
              onChange={(e) => handleApplyPreset(e.target.value)}
              className="w-full px-3 py-2 text-sm border border-neutral-200 dark:border-neutral-600 rounded-lg bg-white dark:bg-neutral-800 focus:outline-none focus:ring-2 focus:ring-sky-400"
              defaultValue=""
            >
              <option value="" disabled>
                プリセットを選択...
              </option>
              <optgroup label="デフォルト">
                {DEFAULT_HIERARCHY_PRESETS.map((preset) => (
                  <option key={preset.id} value={preset.id}>
                    {preset.name}
                  </option>
                ))}
              </optgroup>
              {customPresets.length > 0 && (
                <optgroup label="カスタム">
                  {customPresets.map((preset) => (
                    <option key={preset.id} value={preset.id}>
                      {preset.name}
                    </option>
                  ))}
                </optgroup>
              )}
            </select>

            {/* カスタムプリセット管理 */}
            {customPresets.length > 0 && (
              <div className="mt-2 space-y-1">
                {customPresets.map((preset) => (
                  <div
                    key={preset.id}
                    className="flex items-center justify-between px-2 py-1 bg-neutral-50 dark:bg-neutral-800 rounded text-sm"
                  >
                    <button
                      type="button"
                      onClick={() => handleApplyPreset(preset.id)}
                      className="text-neutral-700 dark:text-neutral-300 hover:text-sky-600 dark:hover:text-sky-400 truncate"
                    >
                      {preset.name}
                    </button>
                    <button
                      type="button"
                      onClick={() => deletePreset(preset.id)}
                      className="p-1 text-red-400 hover:text-red-600"
                      title="削除"
                    >
                      <Trash2 size={12} />
                    </button>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* 階層レベル一覧 */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <span className="block text-sm font-medium text-neutral-700 dark:text-neutral-300">
                階層レベル ({levels.length})
              </span>
              {levels.length > 0 && (
                <button
                  type="button"
                  onClick={() => onLevelsChange([])}
                  className="text-xs text-red-500 hover:text-red-600"
                >
                  すべてクリア
                </button>
              )}
            </div>

            {levels.length === 0 ? (
              <div className="text-center py-8 text-neutral-500 bg-neutral-50 dark:bg-neutral-800/50 rounded-lg">
                階層が設定されていません
              </div>
            ) : (
              <div className="space-y-2">
                {levels.map((level, index) => (
                  <LevelItem
                    key={level.id}
                    level={level}
                    index={index}
                    totalCount={levels.length}
                    entities={entities}
                    userMap={userMap}
                    onUpdate={(updates) => handleUpdateLevel(index, updates)}
                    onRemove={() => handleRemoveLevel(index)}
                    onMoveUp={() => handleMoveUp(index)}
                    onMoveDown={() => handleMoveDown(index)}
                  />
                ))}
              </div>
            )}
          </div>

          {/* 階層追加 */}
          <div className="relative">
            <button
              type="button"
              onClick={() => setShowAddMenu(!showAddMenu)}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 text-sm border-2 border-dashed border-neutral-300 dark:border-neutral-600 rounded-lg text-neutral-600 dark:text-neutral-400 hover:border-sky-400 hover:text-sky-600 dark:hover:text-sky-400 transition-colors"
            >
              <Plus size={16} />
              階層を追加
            </button>

            {showAddMenu && (
              <div className="absolute top-full left-0 right-0 mt-1 bg-white dark:bg-neutral-800 rounded-lg shadow-lg border border-neutral-200 dark:border-neutral-600 z-20 max-h-60 overflow-y-auto">
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
                    <div className="px-3 py-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 border-b border-neutral-100 dark:border-neutral-700">
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
                    <div className="px-3 py-1.5 text-xs font-semibold text-neutral-500 dark:text-neutral-400 border-b border-neutral-100 dark:border-neutral-700">
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
                {unusedFields.length === 0 && (
                  <div className="px-3 py-2 text-sm text-neutral-500 dark:text-neutral-400">
                    利用可能なフィールドがありません
                  </div>
                )}
              </div>
            )}
          </div>
        </div>

        {/* フッター */}
        <div className="px-6 py-4 border-t border-neutral-200 dark:border-neutral-700 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 text-sm font-medium text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded-lg transition-colors"
          >
            閉じる
          </button>
        </div>
      </div>
    </div>
  );
}
