"use client";

import { useCallback, useEffect, useState } from "react";
import { DEFAULT_HIERARCHY_PRESETS } from "@/lib/hierarchy-builder";
import type { HierarchyLevel } from "@/lib/types";

const STORAGE_KEY = "mat-db:hierarchy-levels";
const PRESETS_STORAGE_KEY = "mat-db:hierarchy-presets";

type StoredPreset = {
  id: string;
  name: string;
  description?: string;
  levels: HierarchyLevel[];
};

/**
 * 階層設定をlocalStorageに永続化するフック
 */
export function useHierarchyStorage(defaultLevels?: HierarchyLevel[]) {
  const [levels, setLevels] = useState<HierarchyLevel[]>(
    defaultLevels ?? DEFAULT_HIERARCHY_PRESETS[0].levels,
  );
  const [initialized, setInitialized] = useState(false);

  // localStorageから復元
  useEffect(() => {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setLevels(parsed);
        }
      }
    } catch {
      // localStorageが使えない場合は無視
    }
    setInitialized(true);
  }, []);

  // 変更時にlocalStorageに保存
  const updateLevels = useCallback((newLevels: HierarchyLevel[]) => {
    setLevels(newLevels);
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(newLevels));
    } catch {
      // localStorageが使えない場合は無視
    }
  }, []);

  return { levels, setLevels: updateLevels, initialized };
}

/**
 * カスタムプリセットをlocalStorageに保存・読み込みするフック
 */
export function useHierarchyPresets() {
  const [customPresets, setCustomPresets] = useState<StoredPreset[]>([]);

  // localStorageから復元
  useEffect(() => {
    try {
      const stored = localStorage.getItem(PRESETS_STORAGE_KEY);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          setCustomPresets(parsed);
        }
      }
    } catch {
      // localStorageが使えない場合は無視
    }
  }, []);

  const savePreset = useCallback(
    (name: string, description: string, levels: HierarchyLevel[]) => {
      const newPreset: StoredPreset = {
        id: `custom-${Date.now()}`,
        name,
        description: description || undefined,
        levels: [...levels],
      };
      const updated = [...customPresets, newPreset];
      setCustomPresets(updated);
      try {
        localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // localStorageが使えない場合は無視
      }
      return newPreset;
    },
    [customPresets],
  );

  const deletePreset = useCallback(
    (presetId: string) => {
      const updated = customPresets.filter((p) => p.id !== presetId);
      setCustomPresets(updated);
      try {
        localStorage.setItem(PRESETS_STORAGE_KEY, JSON.stringify(updated));
      } catch {
        // localStorageが使えない場合は無視
      }
    },
    [customPresets],
  );

  return { customPresets, savePreset, deletePreset };
}
