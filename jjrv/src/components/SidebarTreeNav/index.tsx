"use client";

import {
  ChevronDown,
  ChevronRight,
  File,
  Folder,
  FolderGit2,
  PanelLeftClose,
  PanelLeftOpen,
  User,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useCallback, useEffect, useMemo, useState } from "react";
import { USER_NAMESPACE_TAG } from "@/lib/constants";
import type { Relation, StringEntity } from "@/lib/types";

// ========================================
// ツリーノード型
// ========================================

type TreeNode = {
  entity: StringEntity;
  children: TreeNode[];
};

// ========================================
// ツリー構築
// ========================================

function buildTree(
  entities: StringEntity[],
  relations: Relation[],
): TreeNode[] {
  const entityMap = new Map<string, StringEntity>();
  for (const e of entities) {
    entityMap.set(e.id, e);
  }

  // 親→子のマップを構築（child/contains リレーション）
  const childrenMap = new Map<string, string[]>();
  const hasParent = new Set<string>();

  for (const rel of relations) {
    if (rel.label !== "child" && rel.label !== "contains") continue;
    const parentId = rel.entity1Id;
    const childId = rel.entity2Id;
    if (!childrenMap.has(parentId)) {
      childrenMap.set(parentId, []);
    }
    childrenMap.get(parentId)?.push(childId);
    hasParent.add(childId);
  }

  function buildNode(entityId: string): TreeNode | null {
    const entity = entityMap.get(entityId);
    if (!entity) return null;

    const childIds = childrenMap.get(entityId) ?? [];
    const children: TreeNode[] = [];
    for (const childId of childIds) {
      const childNode = buildNode(childId);
      if (childNode) {
        children.push(childNode);
      }
    }

    // ソート: ディレクトリ/レポジトリ優先、名前順
    children.sort((a, b) => {
      const aIsContainer =
        a.entity.sysTags.includes("repository") ||
        a.entity.sysTags.includes("directory") ||
        a.entity.sysTags.includes(USER_NAMESPACE_TAG);
      const bIsContainer =
        b.entity.sysTags.includes("repository") ||
        b.entity.sysTags.includes("directory") ||
        b.entity.sysTags.includes(USER_NAMESPACE_TAG);
      if (aIsContainer && !bIsContainer) return -1;
      if (!aIsContainer && bIsContainer) return 1;
      return a.entity.name.localeCompare(b.entity.name, "ja");
    });

    return { entity, children };
  }

  // rootノードから構築
  const rootNode = buildNode("root");
  if (rootNode) {
    return rootNode.children;
  }

  // rootが見つからない場合、親のないノードをトップレベルに
  const topLevel: TreeNode[] = [];
  for (const e of entities) {
    if (!hasParent.has(e.id) && e.id !== "root") {
      const node = buildNode(e.id);
      if (node) topLevel.push(node);
    }
  }
  return topLevel;
}

// ========================================
// アイコン選択
// ========================================

function NodeIcon({
  entity,
  isExpanded,
}: {
  entity: StringEntity;
  isExpanded: boolean;
}) {
  if (entity.sysTags.includes(USER_NAMESPACE_TAG)) {
    return <User size={14} className="text-indigo-500 flex-shrink-0" />;
  }
  if (entity.sysTags.includes("repository")) {
    return <FolderGit2 size={14} className="text-violet-500 flex-shrink-0" />;
  }
  if (entity.sysTags.includes("directory")) {
    return (
      <Folder
        size={14}
        className={`flex-shrink-0 ${isExpanded ? "text-amber-500" : "text-amber-400"}`}
      />
    );
  }
  return <File size={14} className="text-neutral-400 flex-shrink-0" />;
}

// ========================================
// ツリーノードコンポーネント
// ========================================

function TreeNodeItem({
  node,
  depth,
  expandedIds,
  onToggleExpand,
  selectedId,
  onSelect,
}: {
  node: TreeNode;
  depth: number;
  expandedIds: Set<string>;
  onToggleExpand: (id: string) => void;
  selectedId?: string;
  onSelect: (entity: StringEntity) => void;
}) {
  const hasChildren = node.children.length > 0;
  const isExpanded = expandedIds.has(node.entity.id);
  const isSelected = selectedId === node.entity.id;

  return (
    <div>
      <div
        className={`flex items-center gap-1 py-0.5 px-1 rounded cursor-pointer text-sm transition-colors group ${
          isSelected
            ? "bg-blue-100 dark:bg-blue-900/40 text-blue-800 dark:text-blue-200"
            : "hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-700 dark:text-neutral-300"
        }`}
        style={{ paddingLeft: `${depth * 16 + 4}px` }}
      >
        {/* 展開/折りたたみボタン */}
        {hasChildren ? (
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand(node.entity.id);
            }}
            className="flex-shrink-0 p-0.5 rounded hover:bg-neutral-200 dark:hover:bg-neutral-700"
            aria-label={isExpanded ? "折りたたむ" : "展開する"}
          >
            {isExpanded ? (
              <ChevronDown size={12} />
            ) : (
              <ChevronRight size={12} />
            )}
          </button>
        ) : (
          <span className="w-[18px] flex-shrink-0" />
        )}

        {/* ノード本体（クリックで選択） */}
        <button
          type="button"
          onClick={() => onSelect(node.entity)}
          className="flex items-center gap-1.5 min-w-0 flex-1 text-left"
          title={node.entity.name}
        >
          <NodeIcon entity={node.entity} isExpanded={isExpanded} />
          <span className="truncate text-[13px]">{node.entity.name}</span>
        </button>
      </div>

      {/* 子ノード */}
      {hasChildren && isExpanded && (
        <div>
          {node.children.map((child) => (
            <TreeNodeItem
              key={child.entity.id}
              node={child}
              depth={depth + 1}
              expandedIds={expandedIds}
              onToggleExpand={onToggleExpand}
              selectedId={selectedId}
              onSelect={onSelect}
            />
          ))}
        </div>
      )}
    </div>
  );
}

// ========================================
// SidebarTreeNav 本体
// ========================================

type SidebarTreeNavProps = {
  entities: StringEntity[];
  relations: Relation[];
  selectedId?: string;
  onSelectEntity?: (entity: StringEntity) => void;
  className?: string;
};

export function SidebarTreeNav({
  entities,
  relations,
  selectedId,
  onSelectEntity,
  className = "",
}: SidebarTreeNavProps) {
  const router = useRouter();
  const [collapsed, setCollapsed] = useState(false);
  const [expandedIds, setExpandedIds] = useState<Set<string>>(new Set());

  // ツリー構築
  const tree = useMemo(
    () => buildTree(entities, relations),
    [entities, relations],
  );

  // 初回にuser_namespaceを自動展開
  useEffect(() => {
    if (tree.length > 0 && expandedIds.size === 0) {
      const initialExpanded = new Set<string>();
      for (const node of tree) {
        if (node.entity.sysTags.includes(USER_NAMESPACE_TAG)) {
          initialExpanded.add(node.entity.id);
        }
      }
      if (initialExpanded.size > 0) {
        setExpandedIds(initialExpanded);
      }
    }
  }, [tree, expandedIds.size]);

  const handleToggleExpand = useCallback((id: string) => {
    setExpandedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const handleSelect = useCallback(
    (entity: StringEntity) => {
      if (onSelectEntity) {
        onSelectEntity(entity);
      } else {
        router.push(`/view?id=${encodeURIComponent(entity.id)}`);
      }
    },
    [onSelectEntity, router],
  );

  if (collapsed) {
    return (
      <div className={`flex flex-col items-center py-2 ${className}`}>
        <button
          type="button"
          onClick={() => setCollapsed(false)}
          className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-500"
          title="サイドバーを開く"
          aria-label="サイドバーを開く"
        >
          <PanelLeftOpen size={18} />
        </button>
      </div>
    );
  }

  return (
    <div
      className={`flex flex-col border-r border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-950 ${className}`}
    >
      {/* ヘッダー */}
      <div className="flex items-center justify-between px-3 py-2 border-b border-neutral-200 dark:border-neutral-700">
        <span className="text-xs font-semibold text-neutral-500 dark:text-neutral-400 uppercase tracking-wider">
          Explorer
        </span>
        <button
          type="button"
          onClick={() => setCollapsed(true)}
          className="p-1 rounded hover:bg-neutral-100 dark:hover:bg-neutral-800 text-neutral-400"
          title="サイドバーを閉じる"
          aria-label="サイドバーを閉じる"
        >
          <PanelLeftClose size={16} />
        </button>
      </div>

      {/* ツリー */}
      <div className="flex-1 overflow-y-auto overflow-x-hidden py-1">
        {tree.length === 0 ? (
          <div className="px-3 py-4 text-xs text-neutral-400">
            ツリーデータなし
          </div>
        ) : (
          tree.map((node) => (
            <TreeNodeItem
              key={node.entity.id}
              node={node}
              depth={0}
              expandedIds={expandedIds}
              onToggleExpand={handleToggleExpand}
              selectedId={selectedId}
              onSelect={handleSelect}
            />
          ))
        )}
      </div>
    </div>
  );
}
