"use client";

import { forceCenter, forceCollide } from "d3-force";
import { Settings } from "lucide-react";
import dynamic from "next/dynamic";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import type { ForceGraphMethods, NodeObject } from "react-force-graph-2d";
import { accentFromSysTags } from "@/components/EntityCard";
import { EntityEditPanel } from "@/components/EntityEditPanel";
import { HierarchyLabelBar } from "@/components/HierarchyLabelBar";
import {
  DEFAULT_HIERARCHY_PRESETS,
  getFieldValue,
} from "@/lib/hierarchy-builder";
import type {
  DynamicHierarchyConfig,
  HierarchyLevel,
  Relation,
  StringEntity,
} from "@/lib/types";
import { useHierarchyStorage } from "@/lib/use-hierarchy-storage";

const ForceGraph2D = dynamic(
  () => import("react-force-graph-2d").then((mod) => mod.default),
  { ssr: false },
);

const RELATION_COLORS: Record<string, string> = {
  similar_to: "#f59e0b",
  tagged_with: "#8b5cf6",
  uses_template: "#06b6d4",
  references: "#10b981",
  data_source: "#f43f5e",
  applies_to: "#3b82f6",
  related_to: "#ec4899",
};
const DEFAULT_RELATION_COLOR = "#a855f7";

type EntityGraphProps = {
  entities: StringEntity[];
  onNodeClick?: (entity: StringEntity) => void;
  onToggleSelect?: (entityId: string) => void;
  selectionMode?: boolean;
  selectedIds?: Set<string>;
  width?: number;
  height?: number;
  hierarchyConfig?: DynamicHierarchyConfig;
  onHierarchyChange?: (config: DynamicHierarchyConfig) => void;
  showHierarchyBar?: boolean;
  /** ユーザーIDから表示名へのマッピング（createdByフィールド用） */
  userMap?: Record<string, string>;
  /** Relation情報（エンティティ間の関係エッジを描画） */
  relations?: Relation[];
  /** 編集モード: ノードクリックで編集パネルを表示 */
  editable?: boolean;
  /** 編集モードでエンティティが変更された時のコールバック */
  onEntityChange?: (entity: StringEntity) => void;
  /** 現在編集中のエンティティID */
  editingEntityId?: string | null;
  /** 編集対象エンティティが選択/解除された時のコールバック */
  onEditEntity?: (entity: StringEntity | null) => void;
};

type NodeType = "level" | "entity";

type GraphNode = {
  id: string;
  name: string;
  type: NodeType;
  levelIndex: number;
  color: string;
  size: number;
  entity?: StringEntity;
  /** 4-A+-02: このノードに接続されるリンク数 */
  linkCount?: number;
  x?: number;
  y?: number;
};

type GraphLink = {
  source: string;
  target: string;
  isRelation?: boolean;
  relationLabel?: string;
};

type GraphNodeObject = NodeObject<GraphNode>;

const DEFAULT_LEVEL_COLORS = [
  "#6366f1", // indigo
  "#8b5cf6", // violet
  "#a855f7", // purple
  "#d946ef", // fuchsia
  "#ec4899", // pink
  "#f97316", // orange
];

const ACCENT_COLORS = {
  sky: "#0ea5e9",
  teal: "#14b8a6",
  slate: "#64748b",
  zinc: "#71717a",
  amber: "#f59e0b",
  violet: "#8b5cf6",
};

const ENTITY_COLOR = "#64748b";

function buildDynamicGraphData(
  entities: StringEntity[],
  config: DynamicHierarchyConfig,
  userMap?: Record<string, string>,
): { nodes: GraphNode[]; links: GraphLink[] } {
  const { levels } = config;
  const nodes: GraphNode[] = [];
  const links: GraphLink[] = [];
  const nodeIds = new Set<string>();

  if (levels.length === 0) {
    // 階層なし：エンティティのみ
    for (const entity of entities) {
      const accent = accentFromSysTags(entity.sysTags);
      const color =
        ACCENT_COLORS[accent.color as keyof typeof ACCENT_COLORS] ??
        ENTITY_COLOR;
      const entityId = `entity:${entity.id}`;
      nodes.push({
        id: entityId,
        name: entity.name,
        type: "entity",
        levelIndex: 0,
        color,
        size: 6,
        entity,
      });
    }
    return { nodes, links };
  }

  // 再帰的にグループ化してノード・リンクを構築
  function buildLevel(
    levelEntities: StringEntity[],
    levelIndex: number,
    parentPath: string,
    parentNodeId: string | null,
  ): void {
    if (levelIndex >= levels.length) {
      // エンティティレベル
      for (const entity of levelEntities) {
        const accent = accentFromSysTags(entity.sysTags);
        const color =
          ACCENT_COLORS[accent.color as keyof typeof ACCENT_COLORS] ??
          ENTITY_COLOR;
        const entityId = `entity:${entity.id}`;

        if (!nodeIds.has(entityId)) {
          nodeIds.add(entityId);
          nodes.push({
            id: entityId,
            name: entity.name,
            type: "entity",
            levelIndex: levels.length,
            color,
            size: 6,
            entity,
          });
        }

        if (parentNodeId) {
          links.push({ source: parentNodeId, target: entityId });
        }
      }
      return;
    }

    const level = levels[levelIndex];
    const groups = new Map<string, StringEntity[]>();

    // 現在のレベルでグループ化
    for (const entity of levelEntities) {
      let value = getFieldValue(entity, level.field) ?? "未分類";
      // createdByフィールドの場合はuserMapで表示名に変換
      if (level.field === "createdBy" && userMap && value !== "未分類") {
        value = userMap[value] ?? value;
      }
      if (!groups.has(value)) {
        groups.set(value, []);
      }
      groups.get(value)?.push(entity);
    }

    // ノードサイズは階層によって変化
    const sizeByLevel = Math.max(8, 18 - levelIndex * 3);
    const color =
      level.color ??
      DEFAULT_LEVEL_COLORS[levelIndex % DEFAULT_LEVEL_COLORS.length];

    // 各グループを処理
    for (const [groupName, groupEntities] of groups) {
      const nodeId = `${parentPath}:${level.id}:${groupName}`;

      if (!nodeIds.has(nodeId)) {
        nodeIds.add(nodeId);
        nodes.push({
          id: nodeId,
          name: groupName,
          type: "level",
          levelIndex,
          color,
          size: sizeByLevel,
        });
      }

      if (parentNodeId) {
        links.push({ source: parentNodeId, target: nodeId });
      }

      // 次の階層へ再帰
      buildLevel(groupEntities, levelIndex + 1, nodeId, nodeId);
    }
  }

  buildLevel(entities, 0, "root", null);

  // 4-A+-02: リンク数をカウントしてノードサイズに反映
  const linkCountMap = new Map<string, number>();
  for (const link of links) {
    linkCountMap.set(link.source, (linkCountMap.get(link.source) ?? 0) + 1);
    linkCountMap.set(link.target, (linkCountMap.get(link.target) ?? 0) + 1);
  }
  for (const node of nodes) {
    const count = linkCountMap.get(node.id) ?? 0;
    node.linkCount = count;
    if (node.type === "entity") {
      // エンティティ: リンク数に比例してサイズを拡大 (base 5, max 14)
      node.size = Math.min(14, 5 + Math.sqrt(count) * 2);
    }
  }

  return { nodes, links };
}

// ========================================
// 2-17: グラフビュー設定オプション
// ========================================

type ForceSettings = {
  centerForce: number; // 0-1
  repulsion: number; // 0-500
  linkForce: number; // 0-1
  linkDistance: number; // 10-300
  showArrows: boolean; // 2-18: 矢印表示
  showRelationLabels: boolean; // 2-18: ラベル表示
};

const DEFAULT_FORCE_SETTINGS: ForceSettings = {
  centerForce: 0.3,
  repulsion: 200,
  linkForce: 0.5,
  linkDistance: 80,
  showArrows: false,
  showRelationLabels: true,
};

function ForceSlider({
  label,
  value,
  min,
  max,
  step,
  onChange,
}: {
  label: string;
  value: number;
  min: number;
  max: number;
  step: number;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="text-xs text-neutral-500 w-20 shrink-0">{label}</span>
      <input
        type="range"
        min={min}
        max={max}
        step={step}
        value={value}
        onChange={(e) => onChange(Number(e.target.value))}
        className="flex-1 h-1 accent-sky-500"
      />
      <span className="text-xs text-neutral-400 w-10 text-right tabular-nums">
        {value}
      </span>
    </div>
  );
}

function GraphSettingsPanel({
  settings,
  onChange,
}: {
  settings: ForceSettings;
  onChange: (s: ForceSettings) => void;
}) {
  return (
    <div className="bg-white dark:bg-neutral-900 border border-gray-200 dark:border-gray-700 rounded-lg p-3 space-y-2 shadow-sm">
      <ForceSlider
        label="中心力"
        value={settings.centerForce}
        min={0}
        max={1}
        step={0.05}
        onChange={(v) => onChange({ ...settings, centerForce: v })}
      />
      <ForceSlider
        label="反発力"
        value={settings.repulsion}
        min={0}
        max={500}
        step={10}
        onChange={(v) => onChange({ ...settings, repulsion: v })}
      />
      <ForceSlider
        label="リンク力"
        value={settings.linkForce}
        min={0}
        max={1}
        step={0.05}
        onChange={(v) => onChange({ ...settings, linkForce: v })}
      />
      <ForceSlider
        label="リンク距離"
        value={settings.linkDistance}
        min={10}
        max={300}
        step={5}
        onChange={(v) => onChange({ ...settings, linkDistance: v })}
      />
      <div className="flex items-center gap-3 pt-1 border-t border-gray-100 dark:border-gray-800">
        <label className="flex items-center gap-1.5 text-xs text-neutral-500 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.showArrows}
            onChange={(e) =>
              onChange({ ...settings, showArrows: e.target.checked })
            }
            className="accent-sky-500"
          />
          矢印
        </label>
        <label className="flex items-center gap-1.5 text-xs text-neutral-500 cursor-pointer">
          <input
            type="checkbox"
            checked={settings.showRelationLabels}
            onChange={(e) =>
              onChange({ ...settings, showRelationLabels: e.target.checked })
            }
            className="accent-sky-500"
          />
          ラベル
        </label>
      </div>
    </div>
  );
}

export function EntityGraph({
  entities,
  onNodeClick,
  onToggleSelect,
  selectionMode = false,
  selectedIds,
  width,
  height = 520,
  hierarchyConfig,
  onHierarchyChange,
  showHierarchyBar = true,
  userMap,
  relations,
  editable = false,
  onEntityChange,
  editingEntityId,
  onEditEntity,
}: EntityGraphProps) {
  // デフォルトの階層設定（ローカルストレージから復元）
  const { levels: storedLevels, setLevels: setStoredLevels } =
    useHierarchyStorage(DEFAULT_HIERARCHY_PRESETS[0].levels);

  const currentLevels = hierarchyConfig?.levels ?? storedLevels;

  const handleLevelsChange = useCallback(
    (newLevels: HierarchyLevel[]) => {
      if (onHierarchyChange) {
        onHierarchyChange({ levels: newLevels });
      } else {
        setStoredLevels(newLevels);
      }
    },
    [onHierarchyChange, setStoredLevels],
  );

  const config: DynamicHierarchyConfig = useMemo(
    () => ({ levels: currentLevels }),
    [currentLevels],
  );

  const baseGraphData = useMemo(
    () => buildDynamicGraphData(entities, config, userMap),
    [entities, config, userMap],
  );

  // Relation リンクをマージ + 4-A+-02: リンク数でエンティティノードサイズを再計算
  const graphData = useMemo(() => {
    if (!relations || relations.length === 0) return baseGraphData;
    const nodeIds = new Set(baseGraphData.nodes.map((n) => n.id));
    const relationLinks: GraphLink[] = [];
    for (const rel of relations) {
      const fromId = `entity:${rel.entity1Id}`;
      const toId = `entity:${rel.entity2Id}`;
      if (nodeIds.has(fromId) && nodeIds.has(toId)) {
        relationLinks.push({
          source: fromId,
          target: toId,
          isRelation: true,
          relationLabel: rel.label,
        });
      }
    }
    const allLinks = [...baseGraphData.links, ...relationLinks];
    // リンク数を再カウントしてエンティティノードサイズに反映
    const linkCountMap = new Map<string, number>();
    for (const link of allLinks) {
      const src =
        typeof link.source === "string"
          ? link.source
          : (link.source as GraphNode).id;
      const tgt =
        typeof link.target === "string"
          ? link.target
          : (link.target as GraphNode).id;
      linkCountMap.set(src, (linkCountMap.get(src) ?? 0) + 1);
      linkCountMap.set(tgt, (linkCountMap.get(tgt) ?? 0) + 1);
    }
    const nodes = baseGraphData.nodes.map((node) => {
      const count = linkCountMap.get(node.id) ?? 0;
      if (node.type === "entity") {
        return {
          ...node,
          linkCount: count,
          size: Math.min(14, 5 + Math.sqrt(count) * 2),
        };
      }
      return { ...node, linkCount: count };
    });
    return { nodes, links: allLinks };
  }, [baseGraphData, relations]);

  const relationLabels = useMemo(() => {
    const labels = new Set<string>();
    for (const link of graphData.links) {
      if (link.isRelation && link.relationLabel) labels.add(link.relationLabel);
    }
    return Array.from(labels);
  }, [graphData.links]);

  // 2-17: グラフ設定
  const [forceSettings, setForceSettings] = useState<ForceSettings>(
    DEFAULT_FORCE_SETTINGS,
  );
  const [showSettings, setShowSettings] = useState(false);
  const forceSettingsRef = useRef(forceSettings);
  useEffect(() => {
    forceSettingsRef.current = forceSettings;
  }, [forceSettings]);

  const fgRef = useRef<ForceGraphMethods<GraphNode, GraphLink> | undefined>(
    undefined,
  );
  const containerRef = useRef<HTMLDivElement>(null);
  const [canvasSize, setCanvasSize] = useState({ width: 0, height: 0 });
  const selectedIdsRef = useRef(selectedIds);

  useEffect(() => {
    selectedIdsRef.current = selectedIds;
  }, [selectedIds]);

  // 編集中のエンティティを解決
  const editingEntity =
    editable && editingEntityId
      ? (entities.find((e) => e.id === editingEntityId) ?? null)
      : null;
  const editingEntityIdRef = useRef(editingEntityId);
  useEffect(() => {
    editingEntityIdRef.current = editingEntityId;
  }, [editingEntityId]);

  const handleNodeClick = useCallback(
    (node: GraphNodeObject) => {
      if (node.type !== "entity" || !node.entity) return;
      if (editable && onEditEntity) {
        const nextEntity =
          editingEntityIdRef.current === node.entity.id ? null : node.entity;
        onEditEntity(nextEntity);
        return;
      }
      if (selectionMode && onToggleSelect) {
        onToggleSelect(node.entity.id);
        return;
      }
      onNodeClick?.(node.entity);
    },
    [onNodeClick, onToggleSelect, selectionMode, editable, onEditEntity],
  );

  const nodeCanvasObject = useCallback(
    (
      node: GraphNodeObject,
      ctx: CanvasRenderingContext2D,
      globalScale: number,
    ) => {
      const x = node.x ?? 0;
      const y = node.y ?? 0;
      // 階層レベルによってフォントサイズを変化
      const baseFontSize =
        node.type === "entity" ? 9 : Math.max(10, 14 - node.levelIndex * 2);
      const fontSize = baseFontSize / globalScale;
      const label =
        node.name.length > 14 ? `${node.name.slice(0, 14)}...` : node.name;

      // 4-A+-01: ズームレベルに応じたラベル透明度
      // globalScale < 0.8 でフェードアウト開始、< 0.3 で完全非表示
      const labelOpacity =
        node.type === "level"
          ? Math.min(1, Math.max(0, (globalScale - 0.2) / 0.6))
          : Math.min(1, Math.max(0, (globalScale - 0.3) / 0.8));

      // ノード本体の描画
      ctx.beginPath();
      ctx.arc(x, y, node.size, 0, 2 * Math.PI);
      ctx.fillStyle = node.color;
      ctx.fill();

      if (node.type === "entity") {
        ctx.strokeStyle = "rgba(255,255,255,0.55)";
        ctx.lineWidth = 1;
        ctx.stroke();
      }

      // 選択・編集リング
      if (
        node.type === "entity" &&
        node.entity &&
        editingEntityIdRef.current === node.entity.id
      ) {
        ctx.beginPath();
        ctx.arc(x, y, node.size + 4, 0, 2 * Math.PI);
        ctx.strokeStyle = "#0ea5e9";
        ctx.lineWidth = Math.max(2, 3 / globalScale);
        ctx.stroke();
      } else if (
        node.type === "entity" &&
        node.entity &&
        selectedIdsRef.current?.has(node.entity.id)
      ) {
        ctx.beginPath();
        ctx.arc(x, y, node.size + 3, 0, 2 * Math.PI);
        ctx.strokeStyle = "#f472b6";
        ctx.lineWidth = Math.max(2, 3 / globalScale);
        ctx.stroke();
      }

      // 4-A+-01: ラベルはズームレベルに応じてフェード表示
      if (labelOpacity > 0.05) {
        ctx.save();
        ctx.globalAlpha = labelOpacity;
        ctx.font = `${fontSize}px sans-serif`;
        ctx.textAlign = "center";
        ctx.textBaseline = "top";

        // 4-A+-06: ラベル品質改善 - 白塗り背景を廃止、テキストシャドウで可読性確保
        if (node.type !== "entity") {
          // レベルノード: 濃い色のテキスト + 薄い背景ハロー
          const textY = y + node.size + 4;
          ctx.strokeStyle = "rgba(255,255,255,0.7)";
          ctx.lineWidth = 3 / globalScale;
          ctx.lineJoin = "round";
          ctx.strokeText(label, x, textY);
          ctx.fillStyle = "#1e293b";
          ctx.fillText(label, x, textY);
        } else {
          // エンティティノード: 白テキスト + ダークハロー
          const textY = y + node.size + 3;
          ctx.strokeStyle = "rgba(0,0,0,0.5)";
          ctx.lineWidth = 2.5 / globalScale;
          ctx.lineJoin = "round";
          ctx.strokeText(label, x, textY);
          ctx.fillStyle = "#f8fafc";
          ctx.fillText(label, x, textY);
        }
        ctx.restore();
      }
    },
    [],
  );

  useEffect(() => {
    if (width && height) {
      setCanvasSize({ width, height });
      return;
    }
    const target = containerRef.current;
    if (!target) return;
    const updateSize = () => {
      const rect = target.getBoundingClientRect();
      setCanvasSize({
        width: Math.max(0, Math.floor(rect.width)),
        height: Math.max(0, Math.floor(rect.height)),
      });
    };
    updateSize();
    const observer = new ResizeObserver(() => updateSize());
    observer.observe(target);
    return () => observer.disconnect();
  }, [width, height]);

  // 2-17: フォース設定の適用
  useEffect(() => {
    if (!fgRef.current) return;
    const { width: canvasWidth, height: canvasHeight } = canvasSize;
    if (!canvasWidth || !canvasHeight) return;

    const fs = forceSettings;
    const fg = fgRef.current;

    // リンク力・距離
    const linkForce = fg.d3Force("link");
    if (linkForce?.distance) {
      linkForce.distance((link: { target?: GraphNode }) => {
        const targetLevelIndex = link?.target?.levelIndex ?? 0;
        const factor = Math.max(0.5, 1 - targetLevelIndex * 0.1);
        return fs.linkDistance * factor;
      });
    }
    if (linkForce?.strength) {
      linkForce.strength(fs.linkForce);
    }

    // 反発力
    const chargeForce = fg.d3Force("charge");
    if (chargeForce?.strength) {
      chargeForce.strength(-fs.repulsion);
    }

    // 中心力
    fg.d3Force(
      "center",
      forceCenter(canvasWidth / 2, canvasHeight / 2).strength(fs.centerForce),
    );

    fg.d3Force(
      "collide",
      forceCollide((node) => {
        const typed = node as GraphNode;
        const base =
          typed.type === "level" ? Math.max(16, 32 - typed.levelIndex * 4) : 12;
        return Math.max(typed.size * 2.2, base);
      }).iterations(2),
    );
    fg.d3ReheatSimulation();
  }, [canvasSize, graphData.nodes.length, forceSettings]);

  if (entities.length === 0) {
    return (
      <div className="text-center py-12 text-neutral-500">
        表示するデータがありません
      </div>
    );
  }

  const resolvedWidth = width ?? canvasSize.width;
  const resolvedHeight = height ?? canvasSize.height;
  const ready = resolvedWidth > 0 && resolvedHeight > 0;

  return (
    <div className="flex flex-col gap-2">
      {showHierarchyBar && (
        <HierarchyLabelBar
          levels={currentLevels}
          onLevelsChange={handleLevelsChange}
          entities={entities}
          userMap={userMap}
        />
      )}
      <div
        ref={containerRef}
        role="img"
        aria-label="エンティティグラフ"
        className="rounded-xl border border-gray-300 dark:border-gray-600 overflow-hidden bg-neutral-50 dark:bg-neutral-900"
        style={{
          width: width ? `${width}px` : "100%",
          height: height ? `${height}px` : "520px",
        }}
      >
        {ready && (
          <ForceGraph2D
            // biome-ignore lint/suspicious/noExplicitAny: ForceGraph2D's type definition requires flexible typing
            ref={fgRef as any}
            graphData={graphData}
            width={resolvedWidth}
            height={resolvedHeight}
            nodeRelSize={1}
            nodeVal={(node) => (node as GraphNodeObject).size}
            nodeColor={(node) => (node as GraphNodeObject).color}
            nodeCanvasObject={
              nodeCanvasObject as (
                node: object,
                ctx: CanvasRenderingContext2D,
                globalScale: number,
              ) => void
            }
            nodePointerAreaPaint={(
              node,
              color: string,
              ctx: CanvasRenderingContext2D,
            ) => {
              const gn = node as GraphNodeObject;
              const x = gn.x ?? 0;
              const y = gn.y ?? 0;
              ctx.beginPath();
              ctx.arc(x, y, gn.size + 6, 0, 2 * Math.PI);
              ctx.fillStyle = color;
              ctx.fill();
            }}
            linkColor={(link) => {
              const typed = link as GraphLink;
              // 2-18: relationは灰色実線
              if (typed.isRelation) return "#9ca3af";
              return "rgba(148,163,184,0.5)";
            }}
            linkWidth={(link) => {
              const typed = link as GraphLink;
              if (typed.isRelation) return 1.5;
              const source = (link as { source?: GraphNode }).source;
              if (source?.type === "level") {
                return Math.max(1, 2 - (source.levelIndex ?? 0) * 0.3);
              }
              return 1;
            }}
            linkLineDash={() => []}
            linkDirectionalArrowLength={(link) => {
              const typed = link as GraphLink;
              return typed.isRelation && forceSettingsRef.current.showArrows
                ? 6
                : 0;
            }}
            linkDirectionalArrowRelPos={1}
            linkDirectionalArrowColor={(link) => {
              const typed = link as GraphLink;
              return typed.isRelation ? "#9ca3af" : "rgba(148,163,184,0.5)";
            }}
            linkCanvasObjectMode={() => "after"}
            linkCanvasObject={(link, ctx, globalScale) => {
              // 2-18: relationラベルをエッジ中点に表示
              // 4-A+-06: 白塗り背景を廃止、テキストハローで可読性確保
              const typed = link as GraphLink & {
                source: GraphNode;
                target: GraphNode;
              };
              if (!typed.isRelation || !typed.relationLabel) return;
              if (!forceSettingsRef.current.showRelationLabels) return;
              // 4-A+-01: ズームアウト時はエッジラベルもフェード
              const edgeLabelOpacity = Math.min(
                1,
                Math.max(0, (globalScale - 0.4) / 0.8),
              );
              if (edgeLabelOpacity < 0.05) return;
              const sx = typed.source.x ?? 0;
              const sy = typed.source.y ?? 0;
              const tx = typed.target.x ?? 0;
              const ty = typed.target.y ?? 0;
              const midX = (sx + tx) / 2;
              const midY = (sy + ty) / 2;
              const fontSize = Math.max(8, 10 / globalScale);
              ctx.save();
              ctx.globalAlpha = edgeLabelOpacity;
              ctx.font = `${fontSize}px sans-serif`;
              ctx.textAlign = "center";
              ctx.textBaseline = "middle";
              const text = typed.relationLabel;
              ctx.strokeStyle = "rgba(255,255,255,0.7)";
              ctx.lineWidth = 2.5 / globalScale;
              ctx.lineJoin = "round";
              ctx.strokeText(text, midX, midY);
              ctx.fillStyle = "#6b7280";
              ctx.fillText(text, midX, midY);
              ctx.restore();
            }}
            nodeLabel={(node) => {
              const gn = node as GraphNodeObject;
              if (gn.type === "entity" && gn.entity?.entityType) {
                return `${gn.name} [${gn.entity.entityType}]`;
              }
              return gn.name;
            }}
            onNodeClick={(node) => handleNodeClick(node as GraphNodeObject)}
            cooldownTicks={120}
            onEngineStop={() => {
              if (fgRef.current) {
                fgRef.current.zoomToFit(400, 50);
              }
            }}
          />
        )}
        <div className="px-4 py-2 border-t border-gray-300 dark:border-gray-600 text-xs text-neutral-500 flex items-center gap-4 flex-wrap">
          {currentLevels.map((level, idx) => (
            <span key={level.id} className="inline-flex items-center gap-1">
              <span
                className="w-3 h-3 rounded-full"
                style={{
                  backgroundColor:
                    level.color ??
                    DEFAULT_LEVEL_COLORS[idx % DEFAULT_LEVEL_COLORS.length],
                }}
              />
              {level.label}
            </span>
          ))}
          <span className="inline-flex items-center gap-1">
            <span
              className="w-3 h-3 rounded-full"
              style={{ backgroundColor: ENTITY_COLOR }}
            />
            エンティティ
          </span>
          {relationLabels.map((label) => (
            <span key={label} className="inline-flex items-center gap-1">
              <span className="w-4 border-t border-gray-400" />
              {label}
            </span>
          ))}
          {/* 2-17: 設定ボタン */}
          <button
            type="button"
            onClick={() => setShowSettings(!showSettings)}
            className={`ml-auto inline-flex items-center gap-1 px-2 py-0.5 rounded border transition-colors ${
              showSettings
                ? "border-sky-400 bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400"
                : "border-gray-300 dark:border-gray-600 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            }`}
          >
            <Settings size={12} />
            設定
          </button>
        </div>
      </div>
      {/* 2-17: 設定パネル */}
      {showSettings && (
        <GraphSettingsPanel
          settings={forceSettings}
          onChange={setForceSettings}
        />
      )}
      {/* 編集パネル（editable モード時） */}
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
