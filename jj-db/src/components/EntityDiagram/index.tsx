"use client";

import {
  ChevronDown,
  ChevronRight,
  FolderClosed,
  FolderOpen,
} from "lucide-react";
import { useCallback, useMemo, useRef, useState } from "react";
import { accentFromSysTags } from "@/components/EntityCard";
import { EntityEditPanel } from "@/components/EntityEditPanel";
import type { Relation, StringEntity } from "@/lib/types";

/** 階層ラベル（テーブルビューと同じ） */
const HIERARCHY_LABELS = new Set([
  "child",
  "contains",
  "parent_of",
  "belongs_to",
]);

const ACCENT_COLORS: Record<string, string> = {
  sky: "#0ea5e9",
  teal: "#14b8a6",
  slate: "#64748b",
  zinc: "#71717a",
  amber: "#f59e0b",
  violet: "#8b5cf6",
};
const ENTITY_COLOR = "#64748b";
const DIR_COLOR = "#f59e0b";
const REPO_COLOR = "#8b5cf6";

const NODE_MIN_HEIGHT = 32;
const NODE_PADDING_X = 14;
const NODE_PADDING_Y = 8;
const COLUMN_GAP = 80;
const ROW_GAP = 8;
const MARGIN = 40;
const MAX_NODE_WIDTH = 220;
const LINE_HEIGHT = 16;
const CHAR_WIDTH_ASCII = 7;
const CHAR_WIDTH_CJK = 14;

type EntityDiagramProps = {
  entities: StringEntity[];
  onNodeClick?: (entity: StringEntity) => void;
  onToggleSelect?: (entityId: string) => void;
  selectionMode?: boolean;
  selectedIds?: Set<string>;
  height?: number;
  /** Relation情報（directory階層の構築に使用） */
  relations?: Relation[];
  /** 編集モード */
  editable?: boolean;
  onEntityChange?: (entity: StringEntity) => void;
  editingEntityId?: string | null;
  onEditEntity?: (entity: StringEntity | null) => void;
  /** フォーカス対象のエンティティID（中心表示用） */
  focusEntityId?: string | null;
  /** 不要になったprops（後方互換性のために保持、使用しない） */
  hierarchyConfig?: unknown;
  onHierarchyChange?: unknown;
  showHierarchyBar?: boolean;
  userMap?: Record<string, string>;
};

type NodeData = {
  id: string;
  label: string;
  lines: string[];
  type: "repository" | "directory" | "entity";
  depth: number;
  color: string;
  entity?: StringEntity;
  x: number;
  y: number;
  width: number;
  height: number;
  hasChildren: boolean;
  childCount: number;
};

type EdgeData = {
  from: string;
  to: string;
};

/** directory階層構造のツリーノード */
type HierarchyTreeNode = {
  entity: StringEntity;
  children: HierarchyTreeNode[];
  depth: number;
};

function measureTextWidth(text: string): number {
  let width = 0;
  for (const char of text) {
    const code = char.charCodeAt(0);
    if (code > 0x2e80) {
      width += CHAR_WIDTH_CJK;
    } else {
      width += CHAR_WIDTH_ASCII;
    }
  }
  return width;
}

function wrapText(text: string, maxWidth: number): string[] {
  const words: string[] = [];
  let currentWord = "";
  for (const char of text) {
    const code = char.charCodeAt(0);
    if (code > 0x2e80) {
      if (currentWord) {
        words.push(currentWord);
        currentWord = "";
      }
      words.push(char);
    } else if (char === " " || char === "_" || char === "-") {
      if (currentWord) {
        words.push(currentWord + char);
        currentWord = "";
      } else {
        words.push(char);
      }
    } else {
      currentWord += char;
    }
  }
  if (currentWord) words.push(currentWord);

  const lines: string[] = [];
  let currentLine = "";
  let currentWidth = 0;

  for (const word of words) {
    const wordWidth = measureTextWidth(word);
    if (currentWidth + wordWidth > maxWidth && currentLine) {
      lines.push(currentLine.trim());
      currentLine = word;
      currentWidth = wordWidth;
    } else {
      currentLine += word;
      currentWidth += wordWidth;
    }
  }
  if (currentLine) lines.push(currentLine.trim());

  return lines.length > 0 ? lines : [text];
}

function calcNodeSize(
  label: string,
  isDir: boolean,
): {
  lines: string[];
  width: number;
  height: number;
} {
  const contentMaxWidth = MAX_NODE_WIDTH - NODE_PADDING_X * 2;
  // ディレクトリにはフォルダアイコン分の幅を追加
  const iconWidth = isDir ? 20 : 0;
  const textWidth = measureTextWidth(label) + iconWidth;

  if (textWidth <= contentMaxWidth) {
    const width = Math.max(80, textWidth + NODE_PADDING_X * 2);
    return { lines: [label], width, height: NODE_MIN_HEIGHT };
  }

  const lines = wrapText(label, contentMaxWidth - iconWidth);
  let maxLineWidth = 0;
  for (const line of lines) {
    maxLineWidth = Math.max(maxLineWidth, measureTextWidth(line));
  }
  const width = Math.min(
    MAX_NODE_WIDTH,
    maxLineWidth + iconWidth + NODE_PADDING_X * 2,
  );
  const height = Math.max(
    NODE_MIN_HEIGHT,
    lines.length * LINE_HEIGHT + NODE_PADDING_Y * 2,
  );
  return { lines, width, height };
}

/**
 * Relationからdirectory階層ツリーを構築（テーブルビューと同じロジック）
 */
function buildDirectoryTree(
  entities: StringEntity[],
  relations: Relation[] | undefined,
): HierarchyTreeNode[] {
  const entityMap = new Map(entities.map((e) => [e.id, e]));
  const entityIds = new Set(entities.map((e) => e.id));

  if (!relations || relations.length === 0) {
    // Relationなし→全てルートレベル
    return entities.map((e) => ({ entity: e, children: [], depth: 0 }));
  }

  const hierarchyRelations = relations.filter((r) =>
    HIERARCHY_LABELS.has(r.label.toLowerCase()),
  );

  if (hierarchyRelations.length === 0) {
    return entities.map((e) => ({ entity: e, children: [], depth: 0 }));
  }

  // 親→子のマップを構築
  const childrenMap = new Map<string, string[]>();
  const parentMap = new Map<string, string>();

  for (const rel of hierarchyRelations) {
    const parentId = rel.entity1Id;
    const childId = rel.entity2Id;
    if (entityIds.has(parentId) && entityIds.has(childId)) {
      if (!childrenMap.has(parentId)) {
        childrenMap.set(parentId, []);
      }
      childrenMap.get(parentId)!.push(childId);
      parentMap.set(childId, parentId);
    }
  }

  // ルートエンティティを特定
  const rootIds = entities.filter((e) => !parentMap.has(e.id)).map((e) => e.id);

  // 再帰的にツリーを構築
  const buildNode = (id: string, depth: number): HierarchyTreeNode | null => {
    const entity = entityMap.get(id);
    if (!entity) return null;

    const childIds = childrenMap.get(id) || [];
    const children = childIds
      .map((cid) => buildNode(cid, depth + 1))
      .filter((n): n is HierarchyTreeNode => n !== null)
      .sort((a, b) => {
        const pri = (e: StringEntity) => {
          if (e.sysTags.includes("repository")) return 0;
          if (e.sysTags.includes("directory")) return 1;
          return 2;
        };
        const aPri = pri(a.entity);
        const bPri = pri(b.entity);
        if (aPri !== bPri) return aPri - bPri;
        return a.entity.name.localeCompare(b.entity.name, "ja");
      });

    return { entity, children, depth };
  };

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

  return sortedRoots
    .map((e) => buildNode(e.id, 0))
    .filter((n): n is HierarchyTreeNode => n !== null);
}

/**
 * ダイアグラム用ノード・エッジを構築
 */
function buildDiagram(
  tree: HierarchyTreeNode[],
  collapsedIds: Set<string>,
): {
  nodes: NodeData[];
  edges: EdgeData[];
  width: number;
  height: number;
} {
  const nodes: NodeData[] = [];
  const edges: EdgeData[] = [];

  if (tree.length === 0) {
    return { nodes, edges, width: 300, height: 200 };
  }

  // 各列（depth）の最大幅を先に計算
  const columnMaxWidths: number[] = [];

  const measureTree = (nodeList: HierarchyTreeNode[]) => {
    for (const node of nodeList) {
      const isDir =
        node.entity.sysTags.includes("directory") ||
        node.entity.sysTags.includes("repository");
      const { width } = calcNodeSize(node.entity.name, isDir);
      while (columnMaxWidths.length <= node.depth) {
        columnMaxWidths.push(80);
      }
      columnMaxWidths[node.depth] = Math.max(
        columnMaxWidths[node.depth],
        width,
      );
      if (!collapsedIds.has(node.entity.id) && node.children.length > 0) {
        measureTree(node.children);
      }
    }
  };
  measureTree(tree);

  // 列のX座標
  const columnXPositions: number[] = [];
  let currentX = MARGIN;
  for (let i = 0; i < columnMaxWidths.length; i++) {
    columnXPositions.push(currentX);
    currentX += columnMaxWidths[i] + COLUMN_GAP;
  }

  // ノード配置
  let globalY = MARGIN;

  const countDescendants = (node: HierarchyTreeNode): number => {
    if (collapsedIds.has(node.entity.id)) return 0;
    let count = 0;
    for (const child of node.children) {
      count += 1 + countDescendants(child);
    }
    return count;
  };

  const layoutNodes = (
    nodeList: HierarchyTreeNode[],
    parentId: string | null,
  ): { minY: number; maxY: number } => {
    const groupMinY = globalY;
    let groupMaxY = globalY;

    for (const treeNode of nodeList) {
      const isRepo = treeNode.entity.sysTags.includes("repository");
      const isDir = isRepo || treeNode.entity.sysTags.includes("directory");
      const { lines, width, height } = calcNodeSize(
        treeNode.entity.name,
        isDir,
      );
      const colX = columnXPositions[treeNode.depth] ?? MARGIN;
      const isCollapsed = collapsedIds.has(treeNode.entity.id);
      const visibleChildren =
        isCollapsed || treeNode.children.length === 0 ? [] : treeNode.children;

      const nodeType: NodeData["type"] = isRepo
        ? "repository"
        : isDir
          ? "directory"
          : "entity";

      if (visibleChildren.length === 0) {
        // リーフまたは折り畳み済み
        const accent = accentFromSysTags(treeNode.entity.sysTags);
        const color = isRepo
          ? REPO_COLOR
          : isDir
            ? DIR_COLOR
            : (ACCENT_COLORS[accent.color] ?? ENTITY_COLOR);
        const nodeData: NodeData = {
          id: `entity:${treeNode.entity.id}`,
          label: treeNode.entity.name,
          lines,
          type: nodeType,
          depth: treeNode.depth,
          color,
          entity: treeNode.entity,
          x: colX,
          y: globalY,
          width,
          height,
          hasChildren: treeNode.children.length > 0,
          childCount: countDescendants(treeNode),
        };
        nodes.push(nodeData);

        if (parentId) {
          edges.push({ from: parentId, to: nodeData.id });
        }

        globalY += height + ROW_GAP;
        groupMaxY = globalY;
      } else {
        // 中間ノード（子を展開中）
        const childResult = layoutNodes(
          visibleChildren,
          `entity:${treeNode.entity.id}`,
        );

        const centerY = (childResult.minY + childResult.maxY - height) / 2;
        const accent = accentFromSysTags(treeNode.entity.sysTags);
        const color = isRepo
          ? REPO_COLOR
          : isDir
            ? DIR_COLOR
            : (ACCENT_COLORS[accent.color] ?? ENTITY_COLOR);
        const nodeData: NodeData = {
          id: `entity:${treeNode.entity.id}`,
          label: treeNode.entity.name,
          lines,
          type: nodeType,
          depth: treeNode.depth,
          color,
          entity: treeNode.entity,
          x: colX,
          y: Math.max(groupMinY, centerY),
          width,
          height,
          hasChildren: true,
          childCount: treeNode.children.length,
        };
        nodes.push(nodeData);

        if (parentId) {
          edges.push({ from: parentId, to: nodeData.id });
        }

        groupMaxY = Math.max(groupMaxY, childResult.maxY);
      }
    }

    return { minY: groupMinY, maxY: groupMaxY };
  };

  layoutNodes(tree, null);

  const svgWidth = currentX + MARGIN;
  const svgHeight = Math.max(globalY + MARGIN, 300);

  return { nodes, edges, width: svgWidth, height: svgHeight };
}

export function EntityDiagram({
  entities,
  onNodeClick,
  onToggleSelect,
  selectionMode = false,
  selectedIds,
  height = 800,
  relations,
  editable = false,
  onEntityChange,
  editingEntityId,
  onEditEntity,
  focusEntityId,
}: EntityDiagramProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const [hoveredNode, setHoveredNode] = useState<string | null>(null);

  // 折り畳み状態: 初期状態はdirectory/repositoryを全て折り畳み
  const [collapsedIds, setCollapsedIds] = useState<Set<string>>(() => {
    const collapsibleIds = new Set<string>();
    for (const e of entities) {
      if (e.sysTags.includes("directory") || e.sysTags.includes("repository")) {
        collapsibleIds.add(e.id);
      }
    }
    return collapsibleIds;
  });

  // エリア選択 + 中クリックパン
  const [selectionRect, setSelectionRect] = useState<{
    x: number;
    y: number;
    w: number;
    h: number;
  } | null>(null);
  const dragStartRef = useRef<{ x: number; y: number } | null>(null);
  const panRef = useRef<{
    startX: number;
    startY: number;
    scrollX: number;
    scrollY: number;
  } | null>(null);

  const handleSvgMouseDown = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (e.button === 1) {
        e.preventDefault();
        const container = containerRef.current;
        if (!container) return;
        panRef.current = {
          startX: e.clientX,
          startY: e.clientY,
          scrollX: container.scrollLeft,
          scrollY: container.scrollTop,
        };
        return;
      }
      if (e.button !== 0 || !selectionMode || !onToggleSelect) return;
      const target = e.target as SVGElement;
      if (target.closest("[role='button']")) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const container = containerRef.current;
      const scrollLeft = container?.scrollLeft ?? 0;
      const scrollTop = container?.scrollTop ?? 0;
      const x = e.clientX - rect.left + scrollLeft;
      const y = e.clientY - rect.top + scrollTop;
      dragStartRef.current = { x, y };
      setSelectionRect({ x, y, w: 0, h: 0 });
    },
    [selectionMode, onToggleSelect],
  );

  const handleSvgMouseMove = useCallback(
    (e: React.MouseEvent<SVGSVGElement>) => {
      if (panRef.current) {
        const container = containerRef.current;
        if (!container) return;
        container.scrollLeft =
          panRef.current.scrollX - (e.clientX - panRef.current.startX);
        container.scrollTop =
          panRef.current.scrollY - (e.clientY - panRef.current.startY);
        return;
      }
      if (!dragStartRef.current) return;
      const svg = svgRef.current;
      if (!svg) return;
      const rect = svg.getBoundingClientRect();
      const container = containerRef.current;
      const scrollLeft = container?.scrollLeft ?? 0;
      const scrollTop = container?.scrollTop ?? 0;
      const cx = e.clientX - rect.left + scrollLeft;
      const cy = e.clientY - rect.top + scrollTop;
      const x = Math.min(dragStartRef.current.x, cx);
      const y = Math.min(dragStartRef.current.y, cy);
      const w = Math.abs(cx - dragStartRef.current.x);
      const h = Math.abs(cy - dragStartRef.current.y);
      setSelectionRect({ x, y, w, h });
    },
    [],
  );

  // directory階層ツリーを構築
  const tree = useMemo(
    () => buildDirectoryTree(entities, relations),
    [entities, relations],
  );

  // ダイアグラム構築
  const {
    nodes,
    edges,
    width: svgWidth,
    height: svgHeight,
  } = useMemo(() => buildDiagram(tree, collapsedIds), [tree, collapsedIds]);

  const nodeMap = useMemo(
    () => Object.fromEntries(nodes.map((n) => [n.id, n])),
    [nodes],
  );

  // エリア選択完了
  const handleSvgMouseUp = useCallback(() => {
    if (panRef.current) {
      panRef.current = null;
      return;
    }
    if (!dragStartRef.current || !selectionRect) {
      dragStartRef.current = null;
      setSelectionRect(null);
      return;
    }
    if (selectionRect.w > 5 && selectionRect.h > 5 && onToggleSelect) {
      const rx = selectionRect.x;
      const ry = selectionRect.y;
      const rw = selectionRect.w;
      const rh = selectionRect.h;
      for (const node of nodes) {
        if (!node.entity) continue;
        const ncx = node.x + node.width / 2;
        const ncy = node.y + node.height / 2;
        if (ncx >= rx && ncx <= rx + rw && ncy >= ry && ncy <= ry + rh) {
          onToggleSelect(node.entity.id);
        }
      }
    }
    dragStartRef.current = null;
    setSelectionRect(null);
  }, [selectionRect, nodes, onToggleSelect]);

  // 編集中のエンティティ
  const editingEntity =
    editable && editingEntityId
      ? (entities.find((e) => e.id === editingEntityId) ?? null)
      : null;

  const handleNodeClick = useCallback(
    (node: NodeData) => {
      if (!node.entity) return;
      if (editable && onEditEntity) {
        const nextEntity =
          editingEntityId === node.entity.id ? null : node.entity;
        onEditEntity(nextEntity);
        return;
      }
      if (selectionMode && onToggleSelect) {
        onToggleSelect(node.entity.id);
        return;
      }
      onNodeClick?.(node.entity);
    },
    [
      onNodeClick,
      onToggleSelect,
      selectionMode,
      editable,
      onEditEntity,
      editingEntityId,
    ],
  );

  // 折り畳みトグル
  const toggleCollapse = useCallback((entityId: string) => {
    setCollapsedIds((prev) => {
      const next = new Set(prev);
      if (next.has(entityId)) {
        next.delete(entityId);
      } else {
        next.add(entityId);
      }
      return next;
    });
  }, []);

  const expandAll = () => setCollapsedIds(new Set());
  const collapseAll = () => {
    const collapsibleIds = new Set<string>();
    for (const e of entities) {
      if (e.sysTags.includes("directory") || e.sysTags.includes("repository")) {
        collapsibleIds.add(e.id);
      }
    }
    setCollapsedIds(collapsibleIds);
  };

  // directory/repository数のカウント
  const dirCount = useMemo(
    () =>
      entities.filter(
        (e) =>
          e.sysTags.includes("directory") || e.sysTags.includes("repository"),
      ).length,
    [entities],
  );

  if (entities.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        表示するデータがありません
      </div>
    );
  }

  return (
    <div className="flex flex-col gap-2">
      {/* 階層コントロールバー */}
      {dirCount > 0 && (
        <div className="flex items-center gap-3 px-4 py-1.5 border border-gray-300 dark:border-gray-600 rounded-lg bg-amber-50/50 dark:bg-amber-900/20 text-xs">
          <FolderOpen size={14} className="text-amber-500" />
          <span className="text-amber-700 dark:text-amber-300 font-medium">
            ディレクトリ階層ダイアグラム
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
            {nodes.length} / {entities.length} 件表示
          </span>
        </div>
      )}
      <div
        ref={containerRef}
        className="rounded-xl border border-gray-300 dark:border-gray-600 overflow-auto bg-neutral-50 dark:bg-neutral-900"
        style={{ height: `${height}px` }}
      >
        <svg
          ref={svgRef}
          width={svgWidth}
          height={svgHeight}
          className="min-w-full"
          style={{ minHeight: svgHeight }}
          role="img"
          aria-label="ディレクトリ階層ダイアグラム"
          onMouseDown={handleSvgMouseDown}
          onMouseMove={handleSvgMouseMove}
          onMouseUp={handleSvgMouseUp}
          onMouseLeave={handleSvgMouseUp}
        >
          <defs>
            <marker
              id="arrowhead-dir"
              markerWidth="10"
              markerHeight="7"
              refX="9"
              refY="3.5"
              orient="auto"
            >
              <polygon points="0 0, 10 3.5, 0 7" fill="#94a3b8" />
            </marker>
          </defs>

          {/* Hierarchy Edges */}
          {edges.map((edge) => {
            const from = nodeMap[edge.from];
            const to = nodeMap[edge.to];
            if (!from || !to) return null;

            const x1 = from.x + from.width;
            const y1 = from.y + from.height / 2;
            const x2 = to.x;
            const y2 = to.y + to.height / 2;
            const midX = (x1 + x2) / 2;

            return (
              <path
                key={`${edge.from}-${edge.to}`}
                d={`M ${x1} ${y1} C ${midX} ${y1}, ${midX} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke="#cbd5e1"
                strokeWidth={1.5}
                markerEnd="url(#arrowhead-dir)"
              />
            );
          })}

          {/* Nodes */}
          {nodes.map((node) => {
            const isSelected = node.entity && selectedIds?.has(node.entity.id);
            const isEditTarget =
              editable && node.entity && editingEntityId === node.entity.id;
            const isFocused =
              focusEntityId && node.entity?.id === focusEntityId;
            const isHovered = hoveredNode === node.id;
            const isDir =
              node.type === "directory" || node.type === "repository";
            const isCollapsed = node.entity
              ? collapsedIds.has(node.entity.id)
              : false;

            return (
              // biome-ignore lint/a11y/noStaticElementInteractions: hover effect for all nodes
              <g
                key={node.id}
                role="button"
                tabIndex={0}
                onClick={() => handleNodeClick(node)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    handleNodeClick(node);
                  }
                }}
                onMouseEnter={() => setHoveredNode(node.id)}
                onMouseLeave={() => setHoveredNode(null)}
                style={{ cursor: "pointer" }}
              >
                <rect
                  x={node.x}
                  y={node.y}
                  width={node.width}
                  height={node.height}
                  rx={isDir ? 8 : 6}
                  fill={node.color}
                  stroke={
                    isFocused
                      ? "#f43f5e"
                      : isEditTarget
                        ? "#0ea5e9"
                        : isSelected
                          ? "#f472b6"
                          : isHovered
                            ? "#fff"
                            : "none"
                  }
                  strokeWidth={
                    isFocused
                      ? 3
                      : isEditTarget
                        ? 3
                        : isSelected
                          ? 3
                          : isHovered
                            ? 2
                            : 0
                  }
                  opacity={isHovered ? 0.9 : 1}
                />
                {/* ディレクトリの折り畳みアイコン */}
                {isDir && node.hasChildren && (
                  <g
                    onClick={(e) => {
                      e.stopPropagation();
                      if (node.entity) toggleCollapse(node.entity.id);
                    }}
                  >
                    {isCollapsed ? (
                      <text
                        x={node.x + 8}
                        y={node.y + node.height / 2 + 1}
                        dominantBaseline="central"
                        fill="#fff"
                        fontSize={12}
                        fontWeight={700}
                      >
                        ▶
                      </text>
                    ) : (
                      <text
                        x={node.x + 8}
                        y={node.y + node.height / 2 + 1}
                        dominantBaseline="central"
                        fill="#fff"
                        fontSize={12}
                        fontWeight={700}
                      >
                        ▼
                      </text>
                    )}
                  </g>
                )}
                {/* ノード名テキスト */}
                {node.lines.length === 1 ? (
                  <text
                    x={
                      isDir && node.hasChildren
                        ? node.x + 24
                        : node.x + node.width / 2
                    }
                    y={node.y + node.height / 2}
                    textAnchor={isDir && node.hasChildren ? "start" : "middle"}
                    dominantBaseline="central"
                    fill="#fff"
                    fontSize={isDir ? 13 : 12}
                    fontWeight={isDir ? 600 : 500}
                  >
                    {node.lines[0]}
                  </text>
                ) : (
                  <text
                    x={
                      isDir && node.hasChildren
                        ? node.x + 24
                        : node.x + node.width / 2
                    }
                    textAnchor={isDir && node.hasChildren ? "start" : "middle"}
                    fill="#fff"
                    fontSize={isDir ? 13 : 12}
                    fontWeight={isDir ? 600 : 500}
                  >
                    {node.lines.map((line, idx) => (
                      <tspan
                        key={`${node.id}-line-${idx}`}
                        x={
                          isDir && node.hasChildren
                            ? node.x + 24
                            : node.x + node.width / 2
                        }
                        y={
                          node.y +
                          NODE_PADDING_Y +
                          LINE_HEIGHT / 2 +
                          idx * LINE_HEIGHT
                        }
                      >
                        {line}
                      </tspan>
                    ))}
                  </text>
                )}
                {/* 折り畳み時の子数バッジ */}
                {isCollapsed && node.hasChildren && (
                  <g>
                    <rect
                      x={node.x + node.width - 28}
                      y={node.y + 2}
                      width={26}
                      height={16}
                      rx={8}
                      fill="#0f172a"
                      opacity={0.7}
                    />
                    <text
                      x={node.x + node.width - 15}
                      y={node.y + 13}
                      textAnchor="middle"
                      fill="#fbbf24"
                      fontSize={10}
                      fontWeight={600}
                    >
                      {node.childCount}
                    </text>
                  </g>
                )}
                {/* hover時にtype属性を表示 */}
                {isHovered && node.entity?.entityType && (
                  <g>
                    <rect
                      x={node.x + node.width + 4}
                      y={node.y}
                      width={measureTextWidth(node.entity.entityType) + 12}
                      height={20}
                      rx={4}
                      fill="#0f172a"
                      opacity={0.85}
                    />
                    <text
                      x={node.x + node.width + 10}
                      y={node.y + 14}
                      fill="#38bdf8"
                      fontSize={11}
                      fontWeight={500}
                    >
                      {node.entity.entityType}
                    </text>
                  </g>
                )}
              </g>
            );
          })}
          {/* エリア選択矩形 */}
          {selectionRect && selectionRect.w > 0 && selectionRect.h > 0 && (
            <rect
              x={selectionRect.x}
              y={selectionRect.y}
              width={selectionRect.w}
              height={selectionRect.h}
              fill="rgba(59, 130, 246, 0.15)"
              stroke="#3b82f6"
              strokeWidth={1}
              strokeDasharray="4 2"
              pointerEvents="none"
            />
          )}
        </svg>
        {/* 凡例 */}
        <div className="px-4 py-2 border-t border-gray-300 dark:border-gray-600 text-xs text-neutral-500 flex gap-4 flex-wrap bg-neutral-50 dark:bg-neutral-900 sticky bottom-0">
          <span className="inline-flex items-center gap-1">
            <span
              className="w-3 h-3 rounded"
              style={{ backgroundColor: REPO_COLOR }}
            />
            レポジトリ
          </span>
          <span className="inline-flex items-center gap-1">
            <span
              className="w-3 h-3 rounded"
              style={{ backgroundColor: DIR_COLOR }}
            />
            ディレクトリ
          </span>
          <span className="inline-flex items-center gap-1">
            <span
              className="w-3 h-3 rounded"
              style={{ backgroundColor: ENTITY_COLOR }}
            />
            エンティティ
          </span>
          <span className="text-neutral-400 ml-2">
            ▶ クリックで展開/折り畳み | 中クリックでパン
          </span>
        </div>
      </div>
      {/* 編集パネル */}
      {editable && editingEntity && onEntityChange && (
        <div className="rounded-xl border border-sky-300 dark:border-sky-700 bg-white dark:bg-neutral-900 p-4 shadow-sm">
          <EntityEditPanel
            entity={editingEntity}
            onChange={onEntityChange}
            onClose={() => onEditEntity?.(null)}
          />
        </div>
      )}
    </div>
  );
}
