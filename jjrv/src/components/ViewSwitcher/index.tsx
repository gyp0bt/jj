"use client";

import { GitFork, LayoutGrid, Network, Table } from "lucide-react";

export type ViewType = "card" | "table" | "graph" | "diagram";

type ViewSwitcherProps = {
  value: ViewType;
  onChange: (view: ViewType) => void;
  disabled?: boolean;
  size?: "sm" | "md";
  views?: ViewType[];
};

const VIEW_DEFS: Record<
  ViewType,
  { type: ViewType; icon: typeof LayoutGrid; label: string }
> = {
  card: { type: "card", icon: LayoutGrid, label: "カード" },
  table: { type: "table", icon: Table, label: "テーブル" },
  graph: { type: "graph", icon: Network, label: "グラフ" },
  diagram: { type: "diagram", icon: GitFork, label: "ダイアグラム" },
};

const DEFAULT_VIEWS: ViewType[] = ["table", "diagram", "graph", "card"];

export function ViewSwitcher({
  value,
  onChange,
  disabled = false,
  size = "md",
  views: viewOrder,
}: ViewSwitcherProps) {
  const iconSize = size === "sm" ? 14 : 18;
  const padding = size === "sm" ? "p-1.5" : "p-2";
  const resolvedViews =
    viewOrder && viewOrder.length > 0 ? viewOrder : DEFAULT_VIEWS;
  const resolvedDefs = resolvedViews
    .map((type) => VIEW_DEFS[type])
    .filter(Boolean);

  return (
    <div className="inline-flex rounded-lg border border-gray-300 dark:border-gray-600 overflow-hidden">
      {resolvedDefs.map(({ type, icon: Icon, label }) => {
        const isSelected = value === type;
        return (
          <button
            key={type}
            type="button"
            title={label}
            aria-label={label}
            aria-pressed={isSelected}
            disabled={disabled}
            onClick={() => onChange(type)}
            className={`
              ${padding} transition-colors
              ${
                isSelected
                  ? "bg-neutral-200 dark:bg-neutral-700 text-neutral-900 dark:text-neutral-100"
                  : "bg-white dark:bg-neutral-900 text-neutral-700 dark:text-neutral-300 hover:bg-neutral-100 dark:hover:bg-neutral-800"
              }
              ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}
              border-r border-gray-300 dark:border-gray-600 last:border-r-0
            `}
          >
            <Icon size={iconSize} />
          </button>
        );
      })}
    </div>
  );
}
