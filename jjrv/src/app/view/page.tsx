"use client";
import {
  BookOpen,
  Clipboard,
  Download,
  Expand,
  Eye,
  GitFork,
  GripVertical,
  Star,
  User,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import {
  Suspense,
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { BodyPreviewModal } from "@/components/BodyPreviewModal";
import {
  BodyRenderer,
  detectFormat,
  formatLabel,
} from "@/components/BodyRenderer";
import { EntityCard } from "@/components/EntityCard";
import { EntityDiagram } from "@/components/EntityDiagram";
import { EntityGraph } from "@/components/EntityGraph";
import { EntityTable } from "@/components/EntityTable";
import { TopNav } from "@/components/TopNav";
import { ViewSwitcher, type ViewType } from "@/components/ViewSwitcher";
import { useAuth } from "@/contexts/AuthContext";
import { fetchEntities, fetchEntityById } from "@/lib/entity-api";
import {
  fetchEntityStatsById,
  fetchFavoriteState,
  fetchFavoriteUsers,
  recordEntityDownload,
  toggleEntityFavorite,
} from "@/lib/entity-stats-api";
import {
  fetchRelatedEntitiesGrouped,
  fetchRelationsByEntityId,
} from "@/lib/relation-api";
import type { EntityStats, StringEntity } from "@/lib/types";
import { fetchUsersByIds } from "@/lib/user-api";

// ========================================
// プロパティテーブル
// ========================================

function PropertyTable({ entity }: { entity: StringEntity }) {
  const allProps = useMemo(() => {
    const entries: { key: string; value: string; type: "sys" | "user" }[] = [];
    for (const [k, v] of Object.entries(entity.sysProps ?? {})) {
      entries.push({ key: k, value: v, type: "sys" });
    }
    for (const [k, v] of Object.entries(entity.userProps ?? {})) {
      entries.push({ key: k, value: v, type: "user" });
    }
    return entries;
  }, [entity.sysProps, entity.userProps]);

  if (allProps.length === 0) return null;

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm border-collapse">
        <thead>
          <tr className="border-b border-neutral-200 dark:border-neutral-700">
            <th className="text-left px-3 py-2 text-neutral-500 font-medium">
              プロパティ
            </th>
            <th className="text-left px-3 py-2 text-neutral-500 font-medium">
              値
            </th>
            <th className="text-left px-3 py-2 text-neutral-500 font-medium w-16">
              種別
            </th>
          </tr>
        </thead>
        <tbody>
          {allProps.map((prop) => (
            <tr
              key={`${prop.type}-${prop.key}`}
              className="border-b border-neutral-100 dark:border-neutral-800 hover:bg-neutral-50 dark:hover:bg-neutral-800/50"
            >
              <td className="px-3 py-1.5 font-mono text-[13px]">{prop.key}</td>
              <td className="px-3 py-1.5 text-[13px]">{prop.value}</td>
              <td className="px-3 py-1.5">
                <span
                  className={`text-[11px] rounded-full px-2 py-0.5 ${
                    prop.type === "sys"
                      ? "bg-sky-50 text-sky-600 dark:bg-sky-900/30 dark:text-sky-400"
                      : "bg-amber-50 text-amber-600 dark:bg-amber-900/30 dark:text-amber-400"
                  }`}
                >
                  {prop.type === "sys" ? "sys" : "user"}
                </span>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ========================================
// 統計バッジ
// ========================================

function StatsBadges({
  stats,
  favoriteUsers,
  ownerName,
  isFavorite,
  onToggleFavorite,
}: {
  stats: EntityStats | null;
  favoriteUsers: { id: string; username: string; displayName: string }[];
  ownerName: string;
  isFavorite: boolean;
  onToggleFavorite: () => void;
}) {
  return (
    <div className="flex flex-wrap items-center gap-4 text-sm">
      <div className="inline-flex items-center gap-1.5 text-neutral-600 dark:text-neutral-300">
        <User size={14} />
        <span>{ownerName}</span>
      </div>
      <button
        type="button"
        onClick={onToggleFavorite}
        className={`inline-flex items-center gap-1.5 rounded-lg border px-2.5 py-1 transition-colors ${
          isFavorite
            ? "border-amber-300 bg-amber-50 text-amber-700 dark:border-amber-500 dark:bg-amber-900/30 dark:text-amber-300"
            : "border-neutral-200 dark:border-neutral-700 text-neutral-500 hover:bg-neutral-50 dark:hover:bg-neutral-800"
        }`}
      >
        <Star
          size={14}
          fill={isFavorite ? "currentColor" : "none"}
          className={isFavorite ? "text-amber-500" : ""}
        />
        <span>{stats?.favoriteCount ?? 0}</span>
      </button>
      <div className="inline-flex items-center gap-1.5 text-neutral-500">
        <Download size={14} />
        <span>{stats?.downloadCount ?? 0}</span>
      </div>
      {favoriteUsers.length > 0 && (
        <div className="inline-flex items-center gap-1">
          <Eye size={14} className="text-neutral-400" />
          {favoriteUsers.slice(0, 8).map((u) => (
            <span
              key={u.id}
              title={u.displayName || u.username}
              className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-[10px] font-semibold"
            >
              {(u.displayName || u.username).slice(0, 1).toUpperCase()}
            </span>
          ))}
          {favoriteUsers.length > 8 && (
            <span className="text-[10px] text-neutral-400">
              +{favoriteUsers.length - 8}
            </span>
          )}
        </div>
      )}
    </div>
  );
}

// ========================================
// 関連エンティティビュー
// ========================================

function RelationView({
  relatedGroups,
  relations,
  centerEntity,
  onEntityClick,
}: {
  relatedGroups: Record<string, StringEntity[]>;
  relations: import("@/lib/types").Relation[];
  centerEntity: StringEntity;
  onEntityClick: (entity: StringEntity) => void;
}) {
  const [view, setView] = useState<ViewType>("graph");
  const allRelated = useMemo(
    () => Object.values(relatedGroups).flat(),
    [relatedGroups],
  );

  // 中心エンティティ + 関連エンティティを統合（ビューコンポーネントに渡す）
  const viewEntities = useMemo(() => {
    const ids = new Set(allRelated.map((e) => e.id));
    if (ids.has(centerEntity.id)) return allRelated;
    return [centerEntity, ...allRelated];
  }, [allRelated, centerEntity]);

  if (allRelated.length === 0) return null;

  return (
    <div>
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-base font-semibold flex items-center gap-2">
          <GitFork size={16} className="text-neutral-500" />
          関連エンティティ
          <span className="text-sm font-normal text-neutral-500">
            ({allRelated.length}件)
          </span>
        </h3>
        <ViewSwitcher
          value={view}
          onChange={setView}
          views={["graph", "diagram", "table", "card"]}
          size="sm"
        />
      </div>

      {view === "graph" ? (
        <EntityGraph
          entities={viewEntities}
          onNodeClick={onEntityClick}
          height={360}
          relations={relations}
          showHierarchyBar={false}
        />
      ) : view === "diagram" ? (
        <EntityDiagram
          entities={viewEntities}
          onNodeClick={onEntityClick}
          height={360}
          relations={relations}
          showHierarchyBar={false}
        />
      ) : view === "table" ? (
        <EntityTable
          entities={allRelated}
          onRowClick={onEntityClick}
          metaById={{}}
        />
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {Object.entries(relatedGroups).map(([label, entities]) =>
            entities.map((e) => (
              <div key={e.id} className="relative">
                <span className="absolute top-2 right-2 text-[10px] rounded-full bg-violet-100 dark:bg-violet-900/40 text-violet-600 dark:text-violet-300 px-2 py-0.5 z-10">
                  {label}
                </span>
                <EntityCard
                  entity={e}
                  className="h-full w-full"
                  onClick={() => onEntityClick(e)}
                  clickLabel={`${e.name} を開く`}
                  enableActions={false}
                />
              </div>
            )),
          )}
        </div>
      )}
    </div>
  );
}

// ========================================
// メインコンテンツ
// ========================================

function ViewContent() {
  const params = useSearchParams();
  const router = useRouter();
  const id = params.get("id");
  const { user, isLoading } = useAuth();
  const [entity, setEntity] = useState<StringEntity | null>(null);
  const [relatedGroups, setRelatedGroups] = useState<
    Record<string, StringEntity[]>
  >({});
  const [relations, setRelations] = useState<import("@/lib/types").Relation[]>(
    [],
  );
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState<EntityStats | null>(null);
  const [isFavorite, setIsFavorite] = useState(false);
  const [favoriteUsers, setFavoriteUsers] = useState<
    { id: string; username: string; displayName: string }[]
  >([]);
  const [ownerName, setOwnerName] = useState("");
  const [copied, setCopied] = useState(false);
  const copyTimerRef = useRef<number | null>(null);
  const [showBodyPreview, setShowBodyPreview] = useState(false);
  /** レポジトリ/ディレクトリ直下のREADME.mdエンティティ */
  const [readmeEntity, setReadmeEntity] = useState<StringEntity | null>(null);
  // リサイズ可能な2カラムレイアウト用state
  const [leftWidthPercent, setLeftWidthPercent] = useState(35); // 左カラム（プロパティ）の幅%
  const containerRef = useRef<HTMLDivElement>(null);
  const isDragging = useRef(false);

  const handleResizeStart = useCallback(
    (e: React.MouseEvent) => {
      e.preventDefault();
      isDragging.current = true;
      const startX = e.clientX;
      const startWidth = leftWidthPercent;

      const onMouseMove = (ev: MouseEvent) => {
        if (!isDragging.current || !containerRef.current) return;
        const containerRect = containerRef.current.getBoundingClientRect();
        const deltaX = ev.clientX - startX;
        const deltaPercent = (deltaX / containerRect.width) * 100;
        const newWidth = Math.min(60, Math.max(20, startWidth + deltaPercent));
        setLeftWidthPercent(newWidth);
      };

      const onMouseUp = () => {
        isDragging.current = false;
        document.removeEventListener("mousemove", onMouseMove);
        document.removeEventListener("mouseup", onMouseUp);
        document.body.style.cursor = "";
        document.body.style.userSelect = "";
      };

      document.addEventListener("mousemove", onMouseMove);
      document.addEventListener("mouseup", onMouseUp);
      document.body.style.cursor = "col-resize";
      document.body.style.userSelect = "none";
    },
    [leftWidthPercent],
  );

  const header = (
    <TopNav
      title="詳細ビュー"
      items={[
        { label: "検索", href: "/search" },
        { label: "詳細ビュー", href: id ? `/view?id=${id}` : "/view" },
      ]}
      className="mb-4"
    />
  );

  useEffect(() => {
    async function load() {
      if (!user) return;
      let targetEntity: StringEntity | null = null;
      if (id) {
        const res = await fetchEntityById(id);
        if (res.data) {
          targetEntity = res.data;
        }
      }
      if (!targetEntity) {
        const allRes = await fetchEntities();
        if (allRes.data && allRes.data.length > 0) {
          targetEntity = allRes.data[0];
        }
      }
      if (targetEntity) {
        setEntity(targetEntity);
        const [relatedRes, relationsRes, statsRes, favStateRes, favUsersRes] =
          await Promise.all([
            fetchRelatedEntitiesGrouped(targetEntity.id),
            fetchRelationsByEntityId(targetEntity.id),
            fetchEntityStatsById(targetEntity.id),
            fetchFavoriteState(targetEntity.id),
            fetchFavoriteUsers([targetEntity.id]),
          ]);
        if (relatedRes.data) setRelatedGroups(relatedRes.data);
        if (relationsRes.data) setRelations(relationsRes.data);
        if (statsRes.data) setStats(statsRes.data);
        if (favStateRes.data) setIsFavorite(favStateRes.data.favorite);
        if (favUsersRes.data) {
          setFavoriteUsers(favUsersRes.data[targetEntity.id] ?? []);
        }
        if (targetEntity.createdBy) {
          const userRes = await fetchUsersByIds([targetEntity.createdBy]);
          if (userRes.data && userRes.data.length > 0) {
            setOwnerName(userRes.data[0].username);
          } else {
            setOwnerName(targetEntity.createdBy);
          }
        }

        // レポジトリ/ディレクトリの場合、直下のREADME.mdを検索
        const isRepoOrDir =
          targetEntity.sysTags.includes("repository") ||
          targetEntity.sysTags.includes("directory") ||
          targetEntity.sysTags.includes("user_namespace");
        if (isRepoOrDir && relatedRes.data) {
          const childEntities = [
            ...(relatedRes.data.child ?? []),
            ...(relatedRes.data.contains ?? []),
          ];
          const readme = childEntities.find(
            (e) =>
              e.name.toLowerCase() === "readme.md" ||
              e.name.toLowerCase() === "readme",
          );
          setReadmeEntity(readme ?? null);
        } else {
          setReadmeEntity(null);
        }
      }
      setLoading(false);
    }
    load();
  }, [id, user]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  useEffect(
    () => () => {
      if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
    },
    [],
  );

  const handleToggleFavorite = async () => {
    if (!entity) return;
    const res = await toggleEntityFavorite(entity.id);
    if (res.data) {
      setIsFavorite(res.data.favorite);
      setStats(res.data.stats);
    }
  };

  const handleCopy = () => {
    if (!entity) return;
    navigator.clipboard.writeText(entity.body);
    setCopied(true);
    if (copyTimerRef.current) window.clearTimeout(copyTimerRef.current);
    copyTimerRef.current = window.setTimeout(() => setCopied(false), 1500);
  };

  const handleDownload = () => {
    if (!entity) return;
    const blob = new Blob([entity.body], { type: "text/plain" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = entity.name || `${entity.id}.txt`;
    a.click();
    URL.revokeObjectURL(url);
    recordEntityDownload(entity.id);
  };

  if (isLoading || loading) {
    return (
      <div className="min-h-screen p-6 sm:p-10 font-sans">
        {header}
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-6 text-sm text-neutral-600 dark:text-neutral-400">
          読み込み中...
        </div>
      </div>
    );
  }

  if (!entity) {
    return (
      <div className="min-h-screen p-6 sm:p-10 font-sans">
        {header}
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-6 text-sm text-neutral-600 dark:text-neutral-400">
          エンティティが見つかりませんでした。
        </div>
      </div>
    );
  }

  const format = detectFormat(entity);
  const hasRelatedEntities = Object.keys(relatedGroups).length > 0;
  const hasProps =
    Object.keys(entity.sysProps ?? {}).length > 0 ||
    Object.keys(entity.userProps ?? {}).length > 0;
  const isRepoOrDir =
    entity.sysTags.includes("repository") ||
    entity.sysTags.includes("directory") ||
    entity.sysTags.includes("user_namespace");
  const repoType = entity.sysProps?.repository_type;

  return (
    <div className="min-h-screen p-6 sm:p-10 font-sans">
      {header}

      <div className="max-w-6xl">
        {/* ヘッダー: Git repo page スタイル */}
        <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-5">
          <div className="flex items-start justify-between gap-4">
            <div className="flex-1 min-w-0">
              <div className="flex items-center gap-2 mb-1">
                {entity.sysTags.includes("repository") && (
                  <span className="text-xs rounded-full border border-violet-200 dark:border-violet-700 bg-violet-50 dark:bg-violet-900/30 text-violet-600 dark:text-violet-400 px-2 py-0.5">
                    レポジトリ
                  </span>
                )}
                {entity.sysTags.includes("user_namespace") && (
                  <span className="text-xs rounded-full border border-indigo-200 dark:border-indigo-700 bg-indigo-50 dark:bg-indigo-900/30 text-indigo-600 dark:text-indigo-400 px-2 py-0.5">
                    ユーザー
                  </span>
                )}
                {repoType && (
                  <span className="text-xs rounded-full border border-emerald-200 dark:border-emerald-700 bg-emerald-50 dark:bg-emerald-900/30 text-emerald-600 dark:text-emerald-400 px-2 py-0.5">
                    {repoType}
                  </span>
                )}
                {entity.entityType && (
                  <span className="text-xs rounded-full border border-sky-200 dark:border-sky-700 bg-sky-50 dark:bg-sky-900/30 text-sky-600 dark:text-sky-400 px-2 py-0.5">
                    {entity.entityType}
                  </span>
                )}
                {entity.domain && (
                  <span className="text-xs rounded-full border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-500 px-2 py-0.5">
                    {entity.domain}
                  </span>
                )}
                {!isRepoOrDir && (
                  <span className="text-xs rounded-full border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-500 px-2 py-0.5">
                    {formatLabel(format)}
                  </span>
                )}
              </div>
              <h1 className="text-xl font-bold tracking-tight truncate">
                {entity.name}
              </h1>
              {entity.remark && (
                <p className="mt-1 text-sm text-neutral-600 dark:text-neutral-400">
                  {entity.remark}
                </p>
              )}
            </div>
            <div className="flex items-center gap-2 flex-shrink-0">
              <button
                type="button"
                onClick={handleCopy}
                className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs font-medium hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                title="コピー"
              >
                <Clipboard size={14} />
                {copied ? "コピー済み" : "コピー"}
              </button>
              <button
                type="button"
                onClick={handleDownload}
                className="inline-flex items-center gap-1.5 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs font-medium hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                title="ダウンロード"
              >
                <Download size={14} />
                DL
              </button>
            </div>
          </div>

          {(entity.userTags.length > 0 || entity.sysTags.length > 0) && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              {entity.userTags.map((t) => (
                <button
                  type="button"
                  key={`u-${t}`}
                  className="inline-flex items-center rounded-full px-2 py-0.5 text-[12px] border-amber-300/80 bg-amber-50/70 text-amber-900 dark:bg-amber-900/30 dark:text-amber-300 border cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() =>
                    router.push(`/search?tags=${encodeURIComponent(t)}`)
                  }
                >
                  {t}
                </button>
              ))}
              {entity.sysTags.map((t) => (
                <button
                  type="button"
                  key={`s-${t}`}
                  className="inline-flex items-center rounded-full px-2 py-0.5 text-[12px] border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-300 cursor-pointer hover:opacity-80 transition-opacity"
                  onClick={() =>
                    router.push(`/search?tags=${encodeURIComponent(t)}`)
                  }
                >
                  {t}
                </button>
              ))}
            </div>
          )}

          <div className="mt-4 pt-3 border-t border-neutral-100 dark:border-neutral-800">
            <StatsBadges
              stats={stats}
              favoriteUsers={favoriteUsers}
              ownerName={ownerName || entity.createdBy || "unknown"}
              isFavorite={isFavorite}
              onToggleFavorite={handleToggleFavorite}
            />
          </div>

          <div className="mt-2 flex items-center gap-4 text-xs text-neutral-400">
            <span>
              作成: {new Date(entity.createdAt).toLocaleDateString("ja-JP")}
            </span>
            <span>
              更新: {new Date(entity.updatedAt).toLocaleDateString("ja-JP")}
            </span>
          </div>
        </div>

        {/* 2カラムレイアウト: 左=プロパティ+関連エンティティ、右=ボディ（ドラッグでリサイズ可能） */}
        <div
          ref={containerRef}
          className="mt-4 flex flex-col lg:flex-row gap-0"
        >
          {/* 左カラム: プロパティ + 関連エンティティ */}
          <div
            className="space-y-4 min-w-0 lg:flex-shrink-0"
            style={{ width: `${leftWidthPercent}%` }}
          >
            {/* プロパティテーブル */}
            {hasProps && (
              <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-5">
                <h2 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400 mb-3">
                  プロパティ
                </h2>
                <PropertyTable entity={entity} />
              </div>
            )}

            {/* 関連エンティティ */}
            {hasRelatedEntities && (
              <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-5">
                <RelationView
                  relatedGroups={relatedGroups}
                  relations={relations}
                  centerEntity={entity}
                  onEntityClick={(e) => router.push(`/view?id=${e.id}`)}
                />
              </div>
            )}
          </div>

          {/* ドラッグ可能なリサイズハンドル */}
          <div
            onMouseDown={handleResizeStart}
            className="hidden lg:flex items-center justify-center w-3 cursor-col-resize group flex-shrink-0 select-none"
            title="ドラッグで幅を変更"
          >
            <div className="w-1 h-12 rounded-full bg-neutral-200 dark:bg-neutral-700 group-hover:bg-sky-400 dark:group-hover:bg-sky-500 transition-colors">
              <GripVertical
                size={12}
                className="text-neutral-400 group-hover:text-sky-500 dark:group-hover:text-sky-400 -ml-0.5 mt-3"
              />
            </div>
          </div>

          {/* 右カラム: ボディ (フォーマット対応レンダリング) — レポジトリ/ディレクトリ以外 */}
          {!isRepoOrDir && (
            <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-5 min-w-0 flex-1">
              <div className="flex items-center justify-between mb-3">
                <h2 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400">
                  コンテンツ
                </h2>
                <div className="flex items-center gap-2">
                  <span className="text-xs text-neutral-400">
                    {entity.body.split("\n").length} 行
                  </span>
                  {entity.body && (
                    <button
                      type="button"
                      onClick={() => setShowBodyPreview(true)}
                      className="inline-flex items-center gap-1 rounded-lg border border-neutral-200 dark:border-neutral-700 px-2 py-1 text-xs font-medium hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                      title="拡大プレビュー"
                    >
                      <Expand size={13} />
                      拡大
                    </button>
                  )}
                </div>
              </div>
              <BodyRenderer entity={entity} collapsible />
              {showBodyPreview && entity.body && (
                <BodyPreviewModal
                  entity={entity}
                  onClose={() => setShowBodyPreview(false)}
                />
              )}
            </div>
          )}
        </div>

        {/* README.md レンダリング（レポジトリ/ディレクトリ直下のREADME.md） */}
        {readmeEntity && (
          <div className="mt-4 rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-5">
            <div className="flex items-center gap-2 mb-4">
              <BookOpen size={16} className="text-neutral-500" />
              <h2 className="text-sm font-semibold text-neutral-600 dark:text-neutral-400">
                {readmeEntity.name}
              </h2>
            </div>
            <BodyRenderer
              entity={{
                ...readmeEntity,
                sysProps: {
                  ...readmeEntity.sysProps,
                  format: "markdown",
                },
              }}
              collapsible
            />
          </div>
        )}
      </div>
    </div>
  );
}

export default function ViewPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen p-6 sm:p-10 font-sans">
          <TopNav
            title="詳細ビュー"
            items={[
              { label: "検索", href: "/search" },
              { label: "詳細ビュー", href: "/view" },
            ]}
            className="mb-4"
          />
          <div className="rounded-2xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/50 p-6 text-sm text-neutral-600 dark:text-neutral-400">
            読み込み中...
          </div>
        </div>
      }
    >
      <ViewContent />
    </Suspense>
  );
}
