"use client";
import { useState } from "react";
import { AccountStatus } from "@/components/AccountStatus";
import { BackButton } from "@/components/BackButton";
import {
  type BatchEditItem,
  BatchEntityEditor,
} from "@/components/BatchEntityEditor";
import { BatchUploadPanel } from "@/components/BatchUploadPanel";
import { Button } from "@/components/Button";
import { EntityCard } from "@/components/EntityCard";
import { EntityDiagram } from "@/components/EntityDiagram";
import { EntityGraph } from "@/components/EntityGraph";
import { EntityMetaBadges } from "@/components/EntityMetaBadges";
import { EntityRelations } from "@/components/EntityRelations";
import { EntityTable } from "@/components/EntityTable";
import { GenericUploader } from "@/components/GenericUploader";
import LoginForm from "@/components/LoginForm";
import { SearchBar } from "@/components/SearchBar";
import { SearchFilter } from "@/components/SearchFilter";
import { TopNav } from "@/components/TopNav";
import { ViewSwitcher, type ViewType } from "@/components/ViewSwitcher";
import { MOCK_ENTITIES } from "@/lib/mock-data";
import type { EntityType } from "@/lib/types";

// タブ定義：新しいコンポーネントはここに追加
const TABS = [
  "AccountStatus",
  "BackButton",
  "BatchEntityEditor",
  "BatchUploadPanel",
  "Button",
  "EntityDiagram",
  "EntityCard",
  "EntityGraph",
  "EntityMetaBadges",
  "EntityRelations",
  "EntityTable",
  "GenericUploader",
  "LoginForm",
  "SearchBar",
  "SearchFilter",
  "TopNav",
  "ViewSwitcher",
] as const;
type TabName = (typeof TABS)[number];
const SORTED_TABS = [...TABS].sort((a, b) => a.localeCompare(b));

function AccountStatusPreview() {
  return (
    <div className="flex justify-end">
      <p className="text-sm text-neutral-500 mr-4">
        ログイン中の場合に右側にアイコンが表示されます →
      </p>
      <AccountStatus />
    </div>
  );
}

function ButtonPreview() {
  return (
    <div className="space-y-8">
      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">Variants</h3>
        <div className="flex items-center gap-3">
          <Button variant="primary">Primary</Button>
          <Button variant="secondary">Secondary</Button>
          <Button variant="ghost">Ghost</Button>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">Sizes</h3>
        <div className="flex items-center gap-3">
          <Button size="sm">Small</Button>
          <Button size="md">Medium</Button>
          <Button size="lg">Large</Button>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">States</h3>
        <div className="flex items-center gap-3">
          <Button variant="primary">有効</Button>
          <Button variant="primary" disabled>
            無効
          </Button>
        </div>
      </section>

      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">
          日本語ラベル
        </h3>
        <div className="flex items-center gap-3">
          <Button variant="primary">保存</Button>
          <Button variant="secondary">キャンセル</Button>
          <Button variant="ghost">戻る</Button>
        </div>
      </section>
    </div>
  );
}

function BackButtonPreview() {
  return (
    <div className="flex items-center gap-3">
      <BackButton />
      <BackButton label="一覧へ" href="/" />
    </div>
  );
}

function TopNavPreview() {
  return <TopNav title="検索" items={[{ label: "検索", href: "/search" }]} />;
}

function EntityCardPreview() {
  return (
    <div className="max-w-md">
      <EntityCard entity={MOCK_ENTITIES[0]} />
    </div>
  );
}

function EntityMetaBadgesPreview() {
  return (
    <EntityMetaBadges
      owner={{ name: "Nishioka" }}
      favorites={12}
      favoriteUsers={[
        { name: "A" },
        { name: "B" },
        { name: "C" },
        { name: "D" },
        { name: "E" },
        { name: "F" },
      ]}
      usedBy={[
        { label: "Project A" },
        { label: "SPDM", href: "https://example.com" },
      ]}
    />
  );
}

function EntityRelationsPreview() {
  return (
    <EntityRelations
      relations={[
        { id: "tag-1", type: "tag", label: "graphite" },
        {
          id: "rel-1",
          type: "related",
          label: "外部SPDM",
          href: "https://example.com",
        },
      ]}
    />
  );
}

function EntityTablePreview() {
  return (
    <div className="max-w-4xl">
      <EntityTable
        entities={MOCK_ENTITIES.slice(0, 5)}
        onRowClick={(e) => alert(`クリック: ${e.name}`)}
      />
    </div>
  );
}

function EntityDiagramPreview() {
  return (
    <div>
      <EntityDiagram
        entities={MOCK_ENTITIES}
        onNodeClick={(e) => alert(`クリック: ${e.name}`)}
        height={600}
      />
    </div>
  );
}

function EntityGraphPreview() {
  return (
    <div>
      <EntityGraph
        entities={MOCK_ENTITIES}
        onNodeClick={(e) => alert(`クリック: ${e.name}`)}
      />
    </div>
  );
}

function BatchUploadPanelPreview() {
  const [files, setFiles] = useState<File[]>([]);
  return (
    <BatchUploadPanel
      files={files}
      onFilesChange={setFiles}
      onParse={(result) => console.log(result)}
    />
  );
}

function BatchEntityEditorPreview() {
  const [items, setItems] = useState<BatchEditItem[]>([
    {
      id: "1",
      name: "Steel A",
      body: "*Material, name=Steel A\n*Elastic\n210000,0.3",
      sourcePath: "sample/steel.inp",
      tags: ["steel", "abaqus"],
      props: { density: "7850" },
      selected: true,
    },
  ]);

  return (
    <BatchEntityEditor
      items={items}
      onChange={setItems}
      onApplyTags={(tags) =>
        setItems((current) =>
          current.map((item) =>
            item.selected
              ? { ...item, tags: Array.from(new Set([...item.tags, ...tags])) }
              : item,
          ),
        )
      }
      onApplyProps={(props) =>
        setItems((current) =>
          current.map((item) =>
            item.selected
              ? { ...item, props: { ...item.props, ...props } }
              : item,
          ),
        )
      }
    />
  );
}

function GenericUploaderPreview() {
  return <GenericUploader />;
}

function LoginFormPreview() {
  return (
    <div className="max-w-md">
      <LoginForm onSuccess={() => alert("ログイン成功（プレビュー）")} />
    </div>
  );
}

function SearchBarPreview() {
  const [nameQuery, setNameQuery] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [entityType, setEntityType] = useState<EntityType | "">("Material");
  const [domain, setDomain] = useState("");
  return (
    <div className="space-y-4 max-w-3xl">
      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">基本</h3>
        <SearchBar
          nameQuery={nameQuery}
          onNameQueryChange={setNameQuery}
          tags={tags}
          onTagsChange={setTags}
          entityType={entityType}
          onEntityTypeChange={setEntityType}
          domain={domain}
          onDomainChange={setDomain}
          availableDomains={["abaqus_inp", "nastran", "ansys"]}
        />
      </section>
    </div>
  );
}

function SearchFilterPreview() {
  const [sortBy, setSortBy] = useState<
    "created" | "updated" | "name" | "favoriteCount" | "downloadCount"
  >("updated");
  const [sortOrder, setSortOrder] = useState<"asc" | "desc">("desc");
  const [createdBy, setCreatedBy] = useState("");
  const [favoritedBy, setFavoritedBy] = useState("");

  return (
    <div className="space-y-4">
      <SearchFilter
        sortBy={sortBy}
        sortOrder={sortOrder}
        onSortChange={(by, order) => {
          setSortBy(by);
          setSortOrder(order);
        }}
        createdBy={createdBy}
        onCreatedByChange={setCreatedBy}
        favoritedBy={favoritedBy}
        onFavoritedByChange={setFavoritedBy}
        availableUsers={[
          { id: "u1", username: "user1" },
          { id: "u2", username: "user2" },
        ]}
      />
    </div>
  );
}

function ViewSwitcherPreview() {
  const [view, setView] = useState<ViewType>("card");
  const [compactView, setCompactView] = useState<ViewType>("card");
  return (
    <div className="space-y-6">
      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">基本</h3>
        <ViewSwitcher value={view} onChange={setView} />
        <p className="mt-2 text-sm text-neutral-600">
          選択中: <strong>{view}</strong>
        </p>
      </section>
      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">
          ダイアグラムあり
        </h3>
        <ViewSwitcher
          value={compactView}
          onChange={setCompactView}
          views={["card", "table", "diagram"]}
        />
        <p className="mt-2 text-sm text-neutral-600">
          選択中: <strong>{compactView}</strong>
        </p>
      </section>
      <section>
        <h3 className="text-sm font-medium mb-3 text-neutral-500">無効化</h3>
        <ViewSwitcher value="card" onChange={() => {}} disabled />
      </section>
    </div>
  );
}

// コンポーネントプレビューのマッピング
const PREVIEW_MAP: Record<TabName, React.ComponentType> = {
  AccountStatus: AccountStatusPreview,
  Button: ButtonPreview,
  BackButton: BackButtonPreview,
  TopNav: TopNavPreview,
  EntityDiagram: EntityDiagramPreview,
  EntityCard: EntityCardPreview,
  EntityGraph: EntityGraphPreview,
  EntityMetaBadges: EntityMetaBadgesPreview,
  EntityRelations: EntityRelationsPreview,
  EntityTable: EntityTablePreview,
  BatchUploadPanel: BatchUploadPanelPreview,
  BatchEntityEditor: BatchEntityEditorPreview,
  GenericUploader: GenericUploaderPreview,
  LoginForm: LoginFormPreview,
  SearchBar: SearchBarPreview,
  SearchFilter: SearchFilterPreview,
  ViewSwitcher: ViewSwitcherPreview,
};

export default function ComponentsPreviewPage() {
  const [activeTab, setActiveTab] = useState<TabName>(SORTED_TABS[0]);
  const PreviewComponent = PREVIEW_MAP[activeTab];

  return (
    <main className="min-h-screen p-8 font-sans">
      <h1 className="text-2xl font-semibold mb-6">コンポーネント プレビュー</h1>

      {/* タブナビゲーション */}
      <div className="mb-6 overflow-x-auto border-b border-neutral-200 dark:border-neutral-700">
        <div className="flex w-max gap-1 pr-2">
          {SORTED_TABS.map((tab) => (
            <button
              key={tab}
              type="button"
              onClick={() => setActiveTab(tab)}
              className={`px-4 py-2 text-sm font-medium border-b-2 transition-colors ${
                activeTab === tab
                  ? "border-neutral-900 text-neutral-900 dark:border-white dark:text-white"
                  : "border-transparent text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
              }`}
            >
              {tab}
            </button>
          ))}
        </div>
      </div>

      {/* プレビューエリア */}
      <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 p-6 bg-white dark:bg-neutral-900">
        <PreviewComponent />
      </div>
    </main>
  );
}
