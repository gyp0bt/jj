"use client";
import {
  ChevronLeft,
  ChevronRight,
  GitBranch,
  History,
  Star,
  User,
} from "lucide-react";
import { useRouter, useSearchParams } from "next/navigation";
import { Suspense, useEffect, useMemo, useState } from "react";
import { EntityCard } from "@/components/EntityCard";
import { EntityDiagram } from "@/components/EntityDiagram";
import { EntityGraph } from "@/components/EntityGraph";
import { EntityMetaBadges } from "@/components/EntityMetaBadges";
import { EntityTable } from "@/components/EntityTable";
import { SearchBar } from "@/components/SearchBar";
import { SearchFilter } from "@/components/SearchFilter";
import { SearchHistoryPanel } from "@/components/SearchHistoryPanel";
import { SidebarTreeNav } from "@/components/SidebarTreeNav";
import { TopNav } from "@/components/TopNav";
import { ViewSwitcher, type ViewType } from "@/components/ViewSwitcher";
import { useAuth } from "@/contexts/AuthContext";
import { fetchEntities } from "@/lib/entity-api";
import { downloadEntitiesAsZip } from "@/lib/entity-export";
import { searchEntities } from "@/lib/entity-search";
import {
  fetchEntityStats,
  fetchFavoriteStates,
  fetchFavoriteUsers,
} from "@/lib/entity-stats-api";
import { fetchRelationsByEntityIds } from "@/lib/relation-api";
import { createSearchHistory } from "@/lib/search-history-api";
import type {
  EntityStats,
  EntityType,
  Relation,
  SearchHistory,
  StringEntity,
} from "@/lib/types";
import { fetchUsers, fetchUsersByIds } from "@/lib/user-api";

const SEARCH_SESSION_KEY = "mat-db-search-state";

type SearchSessionState = {
  name: string;
  tags: string;
  domain: string;
  sortBy: string;
  sortOrder: string;
  view: string;
  limit: number;
  createdBy: string;
  favoritedBy: string;
  entityType: string;
  repositoryOnly?: boolean;
};

function loadSearchSession(): SearchSessionState | null {
  try {
    const raw = sessionStorage.getItem(SEARCH_SESSION_KEY);
    if (!raw) return null;
    return JSON.parse(raw) as SearchSessionState;
  } catch {
    return null;
  }
}

function SearchContent() {
  const router = useRouter();
  const params = useSearchParams();
  const { user, isLoading } = useAuth();

  // URLにパラメータがない場合はsessionStorageから復元
  const hasUrlParams = params.toString().length > 0;
  const session = hasUrlParams ? null : loadSearchSession();

  const nameParam = (
    params.get("name") ||
    params.get("q") ||
    session?.name ||
    ""
  ).trim();
  const tagsParam = (params.get("tags") || session?.tags || "").trim();
  const domainParam = (params.get("domain") || session?.domain || "").trim();
  const sortByRaw = params.get("sortBy") || session?.sortBy || "updated";
  const SORT_OPTIONS = [
    "created",
    "updated",
    "name",
    "favoriteCount",
    "downloadCount",
  ] as const;
  const sortByParam = SORT_OPTIONS.includes(
    sortByRaw as (typeof SORT_OPTIONS)[number],
  )
    ? (sortByRaw as (typeof SORT_OPTIONS)[number])
    : "updated";
  const sortOrderParam = (params.get("sortOrder") ||
    session?.sortOrder ||
    "desc") as "asc" | "desc";
  const VIEW_OPTIONS: ViewType[] = ["table", "diagram", "graph", "card"];
  const viewRaw = params.get("view") || session?.view || "card";
  const viewParam = VIEW_OPTIONS.includes(viewRaw as ViewType)
    ? (viewRaw as ViewType)
    : "card";
  const createdByParam = (
    params.get("createdBy") ||
    session?.createdBy ||
    ""
  ).trim();
  const favoritedByParam = (
    params.get("favoritedBy") ||
    session?.favoritedBy ||
    ""
  ).trim();
  const DEFAULT_LIMIT = 10;
  const LIMIT_OPTIONS = [10, 50, 100, 200, 500];
  const limitParamRaw = Number(
    params.get("limit") ?? session?.limit ?? DEFAULT_LIMIT,
  );
  const limitParam = LIMIT_OPTIONS.includes(limitParamRaw)
    ? limitParamRaw
    : DEFAULT_LIMIT;

  const initialTags = useMemo(
    () =>
      tagsParam
        ? tagsParam
            .split(/[\s,]+/)
            .map((tag) => tag.trim())
            .filter(Boolean)
        : [],
    [tagsParam],
  );

  const [nameQuery, setNameQuery] = useState(nameParam);
  const [tags, setTags] = useState<string[]>(initialTags);
  const [domain, setDomain] = useState(domainParam);
  const [sortBy, setSortBy] = useState<
    "created" | "updated" | "name" | "favoriteCount" | "downloadCount"
  >(sortByParam);
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">(sortOrderParam);
  const [view, setView] = useState<ViewType>(viewParam);
  const [limit, setLimit] = useState(limitParam);
  const [createdBy, setCreatedBy] = useState(createdByParam);
  const [favoritedBy, setFavoritedBy] = useState(favoritedByParam);
  const rawEntityTypeParam = params.get("entityType");
  const entityTypeParam =
    rawEntityTypeParam === null
      ? ((session?.entityType as EntityType | "") ?? "")
      : (rawEntityTypeParam as EntityType | "");
  const [entityType, setEntityType] = useState<EntityType | "">(
    entityTypeParam,
  );
  const [repositoryOnly, setRepositoryOnly] = useState(
    session?.repositoryOnly ?? false,
  );

  const [entities, setEntities] = useState<StringEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [page, setPage] = useState(1);
  const pageSize = limit;
  const [statsMap, setStatsMap] = useState<Record<string, EntityStats>>({});
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [selectionMode, setSelectionMode] = useState(false);
  const [favoriteUsersMap, setFavoriteUsersMap] = useState<
    Record<string, { id: string; username: string; displayName: string }[]>
  >({});
  const [favoriteStatesMap, setFavoriteStatesMap] = useState<
    Record<string, boolean>
  >({});
  const [userMap, setUserMap] = useState<Record<string, string>>({});
  const [users, setUsers] = useState<
    { id: string; username: string; displayName: string; role: string }[]
  >([]);
  const [historyPanelOpen, setHistoryPanelOpen] = useState(false);
  const [relations, setRelations] = useState<Relation[]>([]);
  // サイドバーツリー用: 全エンティティ（root/user_namespace含む）と全階層リレーション
  const [allEntitiesForTree, setAllEntitiesForTree] = useState<StringEntity[]>(
    [],
  );
  const [treeRelations, setTreeRelations] = useState<Relation[]>([]);

  useEffect(() => {
    if (!user) return;
    setLoading(true);
    fetchEntities().then((res) => {
      if (res.data) {
        // ツリー用: フィルタなしの全エンティティを保持
        setAllEntitiesForTree(res.data);
        // 検索結果用: ルートレポジトリとユーザー名前空間を除外
        setEntities(
          res.data.filter(
            (e) => e.id !== "root" && !e.sysTags.includes("user_namespace"),
          ),
        );
        // 全エンティティIDでツリー用リレーションを取得
        const allIds = res.data.map((e) => e.id);
        fetchRelationsByEntityIds(allIds).then((relRes) => {
          if (relRes.data) {
            setTreeRelations(
              relRes.data.filter(
                (r) => r.label === "child" || r.label === "contains",
              ),
            );
          }
        });
      }
      setLoading(false);
    });
  }, [user]);

  useEffect(() => {
    if (!isLoading && !user) {
      router.replace("/login");
    }
  }, [isLoading, user, router]);

  // 利用可能なドメインを取得
  const availableDomains = useMemo(() => {
    const domainSet = new Set<string>();
    entities.forEach((e) => {
      if (e.domain) domainSet.add(e.domain);
    });
    return Array.from(domainSet).sort();
  }, [entities]);

  // 利用可能なエンティティタイプを取得（現在のデータから動的に生成）
  const availableEntityTypes = useMemo(() => {
    const typeSet = new Set<string>();
    entities.forEach((e) => {
      if (e.entityType) typeSet.add(e.entityType);
    });
    return Array.from(typeSet).sort();
  }, [entities]);

  const baseSortBy =
    sortBy === "favoriteCount" || sortBy === "downloadCount"
      ? "updated"
      : sortBy;

  const baseList = useMemo(
    () =>
      searchEntities(entities, {
        nameQuery,
        tags,
        domain: domain ? domain : null,
        sortBy: baseSortBy,
        sortOrder,
      }),
    [entities, nameQuery, tags, domain, baseSortBy, sortOrder],
  );

  const list = useMemo(() => {
    let filtered = baseList;
    if (createdBy) {
      filtered = filtered.filter((entity) => entity.createdBy === createdBy);
    }
    if (favoritedBy) {
      filtered = filtered.filter((entity) =>
        favoriteUsersMap[entity.id]?.some((user) => user.id === favoritedBy),
      );
    }
    if (entityType) {
      filtered = filtered.filter((entity) => entity.entityType === entityType);
    }
    if (repositoryOnly) {
      filtered = filtered.filter((entity) =>
        entity.sysTags.includes("repository"),
      );
    }
    if (sortBy === "favoriteCount" || sortBy === "downloadCount") {
      const getValue = (entity: StringEntity) =>
        sortBy === "favoriteCount"
          ? (statsMap[entity.id]?.favoriteCount ?? 0)
          : (statsMap[entity.id]?.downloadCount ?? 0);
      filtered = [...filtered].sort((a, b) => {
        const delta = getValue(a) - getValue(b);
        return sortOrder === "asc" ? delta : -delta;
      });
    }
    return filtered;
  }, [
    baseList,
    createdBy,
    entityType,
    favoritedBy,
    favoriteUsersMap,
    repositoryOnly,
    sortBy,
    sortOrder,
    statsMap,
  ]);

  const pageCount = Math.max(1, Math.ceil(list.length / pageSize));
  const paged = useMemo(
    () => list.slice((page - 1) * pageSize, page * pageSize),
    [list, page, pageSize],
  );
  const graphList = useMemo(() => list.slice(0, limit), [list, limit]);
  const baseIds = useMemo(
    () => baseList.map((entity) => entity.id),
    [baseList],
  );
  const visibleEntities = useMemo(() => {
    return view === "graph" || view === "diagram" ? graphList : paged;
  }, [view, graphList, paged]);
  const visibleIds = useMemo(
    () => visibleEntities.map((entity) => entity.id),
    [visibleEntities],
  );
  const baseIdsKey = useMemo(() => baseIds.join("|"), [baseIds]);
  const visibleIdsKey = useMemo(() => visibleIds.join("|"), [visibleIds]);
  const statsIdsKey = useMemo(
    () =>
      sortBy === "favoriteCount" || sortBy === "downloadCount"
        ? baseIdsKey
        : visibleIdsKey,
    [baseIdsKey, sortBy, visibleIdsKey],
  );
  const favoriteUsersKey = useMemo(
    () => (favoritedBy ? baseIdsKey : visibleIdsKey),
    [baseIdsKey, favoritedBy, visibleIdsKey],
  );
  const metaById = useMemo(
    () =>
      Object.fromEntries(
        list.map((entity) => [
          entity.id,
          {
            owner: {
              name:
                (entity.createdBy ? userMap[entity.createdBy] : undefined) ??
                (user && entity.createdBy === user.id
                  ? user.username
                  : undefined) ??
                (entity.createdBy || "unknown"),
            },
            favorites: statsMap[entity.id]?.favoriteCount ?? 0,
            downloads: statsMap[entity.id]?.downloadCount ?? 0,
            favoriteUsers:
              favoriteUsersMap[entity.id]?.map((item) => ({
                name: item.username,
              })) ?? [],
            usedBy: [],
          },
        ]),
      ),
    [favoriteUsersMap, list, statsMap, user, userMap],
  );

  // Relation を取得（graph/diagram/table全ビューで階層表示に必要）
  const relationTargetIds = useMemo(() => {
    if (view === "graph" || view === "diagram") {
      return graphList.map((e) => e.id);
    }
    // table/card: ページ内エンティティのRelationを取得
    return paged.map((e) => e.id);
  }, [view, graphList, paged]);
  const relationIdsKey = useMemo(
    () => relationTargetIds.join("|"),
    [relationTargetIds],
  );
  useEffect(() => {
    if (!user || !relationIdsKey) {
      setRelations([]);
      return;
    }
    const ids = relationIdsKey.split("|");
    fetchRelationsByEntityIds(ids).then((res) => {
      if (res.data) setRelations(res.data);
    });
  }, [user, relationIdsKey]);

  useEffect(() => {
    setPage((current) => Math.min(current, pageCount));
  }, [pageCount]);

  useEffect(() => {
    if (!user) return;
    if (!statsIdsKey) {
      setStatsMap((current) =>
        Object.keys(current).length === 0 ? current : {},
      );
      return;
    }
    const statsIds = statsIdsKey.split("|");
    fetchEntityStats(statsIds).then((res) => {
      if (!res.data) return;
      const map: Record<string, EntityStats> = {};
      res.data.forEach((stat) => {
        map[stat.entityId] = stat;
      });
      setStatsMap(map);
    });
  }, [user, statsIdsKey]);

  useEffect(() => {
    if (!user) return;
    if (!favoriteUsersKey) {
      setFavoriteUsersMap((current) =>
        Object.keys(current).length === 0 ? current : {},
      );
      return;
    }
    const favoriteIds = favoriteUsersKey.split("|");
    fetchFavoriteUsers(favoriteIds).then((res) => {
      if (!res.data) return;
      setFavoriteUsersMap(res.data);
    });
  }, [user, favoriteUsersKey]);

  useEffect(() => {
    const creatorIds = Array.from(
      new Set(
        baseList.map((entity) => entity.createdBy).filter(Boolean) as string[],
      ),
    );
    if (creatorIds.length === 0) {
      setUserMap({});
      return;
    }
    fetchUsersByIds(creatorIds).then((res) => {
      if (!res.data) return;
      const map: Record<string, string> = {};
      res.data.forEach((item) => {
        map[item.id] = item.username;
      });
      setUserMap(map);
    });
  }, [baseList]);

  useEffect(() => {
    if (!user) return;
    if (!visibleIdsKey) {
      setFavoriteStatesMap((current) =>
        Object.keys(current).length === 0 ? current : {},
      );
      return;
    }
    const ids = visibleIdsKey.split("|");
    fetchFavoriteStates(ids).then((res) => {
      if (!res.data) return;
      const map: Record<string, boolean> = {};
      for (const id of ids) {
        map[id] = res.data.includes(id);
      }
      setFavoriteStatesMap(map);
    });
  }, [user, visibleIdsKey]);

  useEffect(() => {
    fetchUsers().then((res) => {
      if (!res.data) return;
      setUsers(res.data);
    });
  }, []);

  useEffect(() => {
    setSelectedIds((current) => {
      const next = new Set<string>();
      for (const entity of list) {
        if (current.has(entity.id)) {
          next.add(entity.id);
        }
      }
      return next;
    });
  }, [list]);

  // URLパラメータを更新 + sessionStorageに保存
  useEffect(() => {
    const newParams = new URLSearchParams();
    if (nameQuery) newParams.set("name", nameQuery);
    if (tags.length > 0) newParams.set("tags", tags.join(" "));
    if (domain) newParams.set("domain", domain);
    if (sortBy !== "updated") newParams.set("sortBy", sortBy);
    if (sortOrder !== "desc") newParams.set("sortOrder", sortOrder);
    if (view !== "card") newParams.set("view", view);
    if (limit !== DEFAULT_LIMIT) newParams.set("limit", String(limit));
    if (createdBy) newParams.set("createdBy", createdBy);
    if (favoritedBy) newParams.set("favoritedBy", favoritedBy);
    if (entityType) newParams.set("entityType", entityType);
    const newUrl = newParams.toString()
      ? `/search?${newParams.toString()}`
      : "/search";
    router.replace(newUrl);

    // 検索条件をsessionStorageに保存（画面遷移後も保持）
    try {
      const state: SearchSessionState = {
        name: nameQuery,
        tags: tags.join(" "),
        domain,
        sortBy,
        sortOrder,
        view,
        limit,
        createdBy,
        favoritedBy,
        entityType: entityType ?? "",
        repositoryOnly,
      };
      sessionStorage.setItem(SEARCH_SESSION_KEY, JSON.stringify(state));
    } catch {
      // sessionStorage利用不可の場合は無視
    }
  }, [
    nameQuery,
    tags,
    domain,
    sortBy,
    sortOrder,
    view,
    limit,
    createdBy,
    favoritedBy,
    entityType,
    repositoryOnly,
    router,
  ]);

  useEffect(() => {
    if (!user || loading) return;
    const hasQuery =
      nameQuery.trim() ||
      tags.length > 0 ||
      domain.trim() ||
      createdBy.trim() ||
      favoritedBy.trim();
    if (!hasQuery) return;
    const timer = setTimeout(() => {
      createSearchHistory({
        query: nameQuery,
        filters: {
          tags,
          domain: domain.trim(),
          sortBy,
          sortOrder,
          limit,
          createdBy,
          favoritedBy,
          entityType,
          view,
        },
        resultCount: list.length,
      });
    }, 600);
    return () => clearTimeout(timer);
  }, [
    user,
    loading,
    nameQuery,
    tags,
    domain,
    sortBy,
    sortOrder,
    limit,
    createdBy,
    favoritedBy,
    entityType,
    view,
    list.length,
  ]);

  const handleApplyHistory = (historyItem: SearchHistory) => {
    setNameQuery(historyItem.query || "");
    const filters = historyItem.filters;
    if (filters.tags && Array.isArray(filters.tags)) {
      setTags(filters.tags as string[]);
    } else {
      setTags([]);
    }
    if (filters.domain && typeof filters.domain === "string") {
      setDomain(filters.domain);
    } else {
      setDomain("");
    }
    if (filters.entityType && typeof filters.entityType === "string") {
      setEntityType(filters.entityType as EntityType | "");
    } else {
      setEntityType("");
    }
    if (filters.createdBy && typeof filters.createdBy === "string") {
      setCreatedBy(filters.createdBy);
    } else {
      setCreatedBy("");
    }
    if (filters.favoritedBy && typeof filters.favoritedBy === "string") {
      setFavoritedBy(filters.favoritedBy);
    } else {
      setFavoritedBy("");
    }
    if (filters.sortBy && typeof filters.sortBy === "string") {
      setSortBy(
        filters.sortBy as
          | "created"
          | "updated"
          | "name"
          | "favoriteCount"
          | "downloadCount",
      );
    }
    if (filters.sortOrder && typeof filters.sortOrder === "string") {
      setSortOrder(filters.sortOrder as "asc" | "desc");
    }
    if (
      filters.view &&
      typeof filters.view === "string" &&
      VIEW_OPTIONS.includes(filters.view as ViewType)
    ) {
      setView(filters.view as ViewType);
    }
    setPage(1);
  };

  if (isLoading || !user) {
    return (
      <div className="min-h-screen p-6 sm:p-10 font-sans">
        <div className="text-center py-12 text-neutral-500">読み込み中...</div>
      </div>
    );
  }

  return (
    <div className="min-h-screen flex font-sans">
      {/* サイドバーツリーナビゲーション */}
      <SidebarTreeNav
        entities={allEntitiesForTree}
        relations={treeRelations}
        className="w-64 min-w-0 flex-shrink-0 h-screen sticky top-0 hidden md:flex"
      />

      {/* メインコンテンツ */}
      <div className="flex-1 min-w-0 p-6 sm:p-10">
        <TopNav
          title="検索"
          items={[{ label: "検索", href: "/search" }]}
          className="mb-4"
        />

        {/* 検索バー */}
        <div className="mb-4 flex gap-3">
          <SearchBar
            nameQuery={nameQuery}
            onNameQueryChange={setNameQuery}
            tags={tags}
            onTagsChange={setTags}
            entityType={entityType}
            onEntityTypeChange={(type) => {
              setEntityType(type);
              setPage(1);
            }}
            domain={domain}
            onDomainChange={setDomain}
            availableDomains={availableDomains}
            availableEntityTypes={availableEntityTypes}
            className="flex-1"
          />
          <button
            type="button"
            onClick={() => setHistoryPanelOpen(true)}
            title="検索履歴"
            aria-label="検索履歴"
            className="flex-shrink-0 flex items-center justify-center w-12 h-12 rounded-2xl border border-gray-300 dark:border-gray-600 bg-white dark:bg-neutral-900 shadow-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
          >
            <History
              size={20}
              className="text-neutral-600 dark:text-neutral-300"
            />
          </button>
        </div>

        {/* 検索履歴パネル */}
        <SearchHistoryPanel
          isOpen={historyPanelOpen}
          onClose={() => setHistoryPanelOpen(false)}
          onApply={handleApplyHistory}
        />

        {/* フィルタ、ビュー切り替え、結果数 */}
        <div className="mb-5 flex flex-wrap items-center gap-3">
          <SearchFilter
            sortBy={sortBy}
            sortOrder={sortOrder}
            onSortChange={(by, order) => {
              setSortBy(by);
              setSortOrder(order);
            }}
            createdBy={createdBy}
            onCreatedByChange={(userId) => {
              setCreatedBy(userId);
              setPage(1);
            }}
            favoritedBy={favoritedBy}
            onFavoritedByChange={(userId) => {
              setFavoritedBy(userId);
              setPage(1);
            }}
            availableUsers={users.map((userItem) => ({
              id: userItem.id,
              username: userItem.username,
            }))}
          />
          <div className="flex flex-wrap items-center gap-2">
            <ViewSwitcher
              value={view}
              onChange={setView}
              views={VIEW_OPTIONS}
            />
            <button
              type="button"
              onClick={() => {
                if (!user) return;
                setFavoritedBy((current) =>
                  current === user.id ? "" : user.id,
                );
                setPage(1);
              }}
              title="お気に入りのみ"
              aria-label="お気に入りのみ"
              className={`flex items-center rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                user && favoritedBy === user.id
                  ? "border-amber-400 bg-amber-50 text-amber-700 dark:border-amber-300 dark:bg-amber-900/40 dark:text-amber-200"
                  : "border-neutral-300 text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              }`}
            >
              <Star size={12} />
            </button>
            <button
              type="button"
              onClick={() => {
                if (!user) return;
                setCreatedBy((current) => (current === user.id ? "" : user.id));
                setPage(1);
              }}
              title="自分の登録のみ"
              aria-label="自分の登録のみ"
              className={`flex items-center rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                user && createdBy === user.id
                  ? "border-emerald-400 bg-emerald-50 text-emerald-700 dark:border-emerald-300 dark:bg-emerald-900/40 dark:text-emerald-200"
                  : "border-neutral-300 text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              }`}
            >
              <User size={12} />
            </button>
            <button
              type="button"
              onClick={() => {
                setRepositoryOnly((current) => !current);
                setPage(1);
              }}
              title="レポジトリのみ"
              aria-label="レポジトリのみ"
              className={`flex items-center gap-1 rounded-lg border px-3 py-2 text-xs font-medium transition-colors ${
                repositoryOnly
                  ? "border-violet-400 bg-violet-50 text-violet-700 dark:border-violet-300 dark:bg-violet-900/40 dark:text-violet-200"
                  : "border-neutral-300 text-neutral-700 hover:bg-neutral-50 dark:border-neutral-700 dark:text-neutral-300 dark:hover:bg-neutral-800"
              }`}
            >
              <GitBranch size={12} />
            </button>
            <label className="flex items-center gap-2 text-xs text-neutral-600 dark:text-neutral-300">
              表示件数
              <select
                value={limit}
                onChange={(e) => {
                  setLimit(Number(e.target.value));
                  setPage(1);
                }}
                className="rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm focus:outline-none focus:ring-2 focus:ring-neutral-400 dark:focus:ring-neutral-600"
              >
                {LIMIT_OPTIONS.map((option) => (
                  <option key={option} value={option}>
                    {option} 件
                  </option>
                ))}
              </select>
            </label>
          </div>
          <span className="ml-auto text-sm text-neutral-700 dark:text-neutral-300">
            {list.length} 件
          </span>
        </div>

        {/* 選択モード */}
        {list.length > 0 && (
          <div className="mb-3 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
            <button
              type="button"
              onClick={() => setSelectionMode((current) => !current)}
              className={`rounded-lg border px-3 py-1.5 font-medium ${
                selectionMode
                  ? "border-pink-400 bg-pink-50 text-pink-700 shadow-[0_0_0_2px_rgba(244,114,182,0.3)]"
                  : "border-neutral-200 dark:border-neutral-800 text-neutral-500"
              } hover:bg-neutral-50 dark:hover:bg-neutral-800`}
            >
              選択モード: {selectionMode ? "ON" : "OFF"}
            </button>
            <span>選択中: {selectedIds.size}</span>
          </div>
        )}

        {/* 一括アクション（グラフ以外） */}
        {list.length > 0 && view !== "graph" && (
          <div className="mb-4 flex flex-wrap items-center gap-2 text-xs text-neutral-500">
            <button
              type="button"
              onClick={() =>
                setSelectedIds(new Set(paged.map((entity) => entity.id)))
              }
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              このページを全選択
            </button>
            <button
              type="button"
              onClick={() => setSelectedIds(new Set())}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              選択解除
            </button>
            <span className="ml-auto text-xs text-neutral-500">
              {selectedIds.size} 件選択中
            </span>
            <button
              type="button"
              onClick={() => {
                const selected = list.filter((entity) =>
                  selectedIds.has(entity.id),
                );
                const text = selected.map((entity) => entity.body).join("\n\n");
                if (text) {
                  navigator.clipboard.writeText(text);
                }
              }}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              一括コピー
            </button>
            <button
              type="button"
              onClick={() => {
                const selected = list.filter((entity) =>
                  selectedIds.has(entity.id),
                );
                if (selected.length === 0) return;
                const text = selected.map((entity) => entity.body).join("\n\n");
                const blob = new Blob([text], { type: "text/plain" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = "entities.txt";
                a.click();
                URL.revokeObjectURL(url);
              }}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              一括ダウンロード
            </button>
            <button
              type="button"
              onClick={() => {
                const selected = list.filter((entity) =>
                  selectedIds.has(entity.id),
                );
                if (selected.length === 0) return;
                downloadEntitiesAsZip(selected);
              }}
              className="rounded-lg border border-neutral-200 dark:border-neutral-800 px-3 py-1.5 hover:bg-neutral-50 dark:hover:bg-neutral-800"
            >
              ZIP出力
            </button>
          </div>
        )}

        {/* 検索結果 */}
        {loading ? (
          <div className="text-center py-12 text-neutral-500">
            読み込み中...
          </div>
        ) : list.length === 0 ? (
          <div className="text-center py-12 text-neutral-500">
            検索結果がありません
          </div>
        ) : view === "graph" ? (
          /* グラフビュー */
          <EntityGraph
            entities={graphList}
            onNodeClick={(e) => router.push(`/view?id=${e.id}`)}
            onToggleSelect={(entityId) =>
              setSelectedIds((current) => {
                const next = new Set(current);
                if (next.has(entityId)) {
                  next.delete(entityId);
                } else {
                  next.add(entityId);
                }
                return next;
              })
            }
            selectionMode={selectionMode}
            selectedIds={selectedIds}
            userMap={userMap}
            relations={relations}
          />
        ) : view === "diagram" ? (
          /* ダイアグラムビュー */
          <EntityDiagram
            entities={graphList}
            onNodeClick={(e) => router.push(`/view?id=${e.id}`)}
            onToggleSelect={(entityId) =>
              setSelectedIds((current) => {
                const next = new Set(current);
                if (next.has(entityId)) {
                  next.delete(entityId);
                } else {
                  next.add(entityId);
                }
                return next;
              })
            }
            selectionMode={selectionMode}
            selectedIds={selectedIds}
            height={480}
            userMap={userMap}
            relations={relations}
          />
        ) : view === "table" ? (
          /* テーブルビュー */
          <>
            <EntityTable
              entities={paged}
              onRowClick={(e) => router.push(`/view?id=${e.id}`)}
              metaById={metaById}
              selectedIds={selectionMode ? selectedIds : undefined}
              onToggleSelect={
                selectionMode
                  ? (entityId) =>
                      setSelectedIds((current) => {
                        const next = new Set(current);
                        if (next.has(entityId)) {
                          next.delete(entityId);
                        } else {
                          next.add(entityId);
                        }
                        return next;
                      })
                  : undefined
              }
              onToggleSelectAll={
                selectionMode
                  ? (next) => {
                      if (next) {
                        setSelectedIds(
                          new Set(paged.map((entity) => entity.id)),
                        );
                      } else {
                        setSelectedIds(new Set());
                      }
                    }
                  : undefined
              }
              selectionMode={selectionMode}
              favoriteStateMap={favoriteStatesMap}
              onFavoriteChange={(entityId, next) =>
                setFavoriteStatesMap((current) => ({
                  ...current,
                  [entityId]: next,
                }))
              }
              enableFiltering
              enableHierarchy
              relations={relations}
              allEntities={entities}
              onTagClick={(tag) =>
                router.push(`/search?tags=${encodeURIComponent(tag)}`)
              }
              onRelationClick={(e) => router.push(`/view?id=${e.id}`)}
            />
            {/* ページネーション */}
            {pageCount > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-xl border border-neutral-200 dark:border-neutral-800 px-3 py-2 disabled:opacity-40 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft size={18} /> 前へ
                </button>
                <span className="text-sm">
                  {page} / {pageCount}
                </span>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-xl border border-neutral-200 dark:border-neutral-800 px-3 py-2 disabled:opacity-40 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                  onClick={() => setPage(Math.min(pageCount, page + 1))}
                  disabled={page >= pageCount}
                >
                  次へ <ChevronRight size={18} />
                </button>
              </div>
            )}
          </>
        ) : (
          /* カードビュー（デフォルト） */
          <>
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4">
              {paged.map((e) => (
                <EntityCard
                  key={e.id}
                  entity={e}
                  className="h-full w-full"
                  onClick={() => {
                    if (selectionMode) {
                      setSelectedIds((current) => {
                        const next = new Set(current);
                        if (next.has(e.id)) {
                          next.delete(e.id);
                        } else {
                          next.add(e.id);
                        }
                        return next;
                      });
                      return;
                    }
                    router.push(`/view?id=${e.id}`);
                  }}
                  clickLabel={`${e.name} を開く`}
                  selected={selectedIds.has(e.id)}
                  favoriteState={favoriteStatesMap[e.id]}
                  onFavoriteChange={(next) =>
                    setFavoriteStatesMap((current) => ({
                      ...current,
                      [e.id]: next,
                    }))
                  }
                  meta={
                    <EntityMetaBadges
                      owner={{
                        name:
                          (e.createdBy ? userMap[e.createdBy] : undefined) ??
                          (user && e.createdBy === user.id
                            ? user.username
                            : undefined) ??
                          (e.createdBy || "unknown"),
                      }}
                      favorites={statsMap[e.id]?.favoriteCount ?? 0}
                      downloads={statsMap[e.id]?.downloadCount ?? 0}
                      favoriteUsers={
                        favoriteUsersMap[e.id]?.map((item) => ({
                          name: item.username,
                        })) ?? []
                      }
                      usedBy={[]}
                      className="text-[11px]"
                    />
                  }
                />
              ))}
            </div>
            {/* ページネーション */}
            {pageCount > 1 && (
              <div className="mt-6 flex items-center justify-center gap-2">
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-xl border border-neutral-200 dark:border-neutral-800 px-3 py-2 disabled:opacity-40 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                  onClick={() => setPage(Math.max(1, page - 1))}
                  disabled={page <= 1}
                >
                  <ChevronLeft size={18} /> 前へ
                </button>
                <span className="text-sm">
                  {page} / {pageCount}
                </span>
                <button
                  type="button"
                  className="inline-flex items-center gap-1 rounded-xl border border-neutral-200 dark:border-neutral-800 px-3 py-2 disabled:opacity-40 hover:bg-neutral-50 dark:hover:bg-neutral-800 transition-colors"
                  onClick={() => setPage(Math.min(pageCount, page + 1))}
                  disabled={page >= pageCount}
                >
                  次へ <ChevronRight size={18} />
                </button>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}

export default function SearchPage() {
  return (
    <Suspense
      fallback={
        <div className="min-h-screen p-6 sm:p-10 font-sans">
          <div className="text-center py-12 text-neutral-500">
            読み込み中...
          </div>
        </div>
      }
    >
      <SearchContent />
    </Suspense>
  );
}
