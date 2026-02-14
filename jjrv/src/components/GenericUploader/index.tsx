"use client";
import {
  ChevronDown,
  ChevronRight,
  FileText,
  FolderOpen,
  Link2,
  Loader2,
  Save,
  Tag,
  UploadCloud,
  X,
} from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  BodyRenderer,
  detectFormat,
  formatLabel,
} from "@/components/BodyRenderer";
import { EntityDiagram } from "@/components/EntityDiagram";
import { EntityGraph } from "@/components/EntityGraph";
import { EntityTable } from "@/components/EntityTable";
import { ViewSwitcher, type ViewType } from "@/components/ViewSwitcher";
import {
  createEntity,
  fetchMyNamespace,
  fetchRepositoriesAndNamespaces,
  searchEntities,
} from "@/lib/entity-api";
import { createRelation } from "@/lib/relation-api";
import { REPOSITORY_TYPES, ROOT_REPOSITORY_ID } from "@/lib/constants";
import type { Relation, StringEntity } from "@/lib/types";

const MATERIAL_KEYWORDS = [
  "*elastic",
  "*plastic",
  "*density",
  "*expansion",
  "*damage initiation",
  "*damage evolution",
  "*conductivity",
  "*electrical conductivity",
  "*specific heat",
  "*creep",
  "*hyper elastic",
];

const normalize = (value: string) => value.toLowerCase().replace(/\s+/g, "");
const MATERIAL_SET = new Set(MATERIAL_KEYWORDS.map(normalize));
const MATERIAL_START = normalize("*material");
const MATERIAL_LABELS = new Map(
  MATERIAL_KEYWORDS.map((kw) => [normalize(kw), kw.replace(/^\*/, "")]),
);

type MaterialExtractResult = {
  blocks: string[];
  materialNames: Set<string>;
  keywords: Set<string>;
};

/** ドロップされたファイルのメタ情報 */
type DroppedFile = {
  file: File;
  /** ルートからの相対パス（例: "projectA/materials/steel.inp"） */
  relativePath: string;
};

/** フォルダツリーのノード */
type FolderTreeNode = {
  name: string;
  path: string;
  isFolder: boolean;
  children: FolderTreeNode[];
  /** ファイルの場合のみ */
  file?: File;
};

async function getFilesFromDataTransfer(
  items: DataTransferItemList,
): Promise<DroppedFile[]> {
  const result: DroppedFile[] = [];
  const entries = Array.from(items)
    .map((item) => item.webkitGetAsEntry?.())
    .filter(Boolean) as Array<FileSystemEntry>;

  const walkEntry = async (entry: FileSystemEntry, parentPath: string) => {
    const currentPath = parentPath ? `${parentPath}/${entry.name}` : entry.name;

    if (entry.isFile) {
      await new Promise<void>((resolve) => {
        (entry as FileSystemFileEntry).file((file) => {
          result.push({ file, relativePath: currentPath });
          resolve();
        });
      });
      return;
    }
    if (entry.isDirectory) {
      const reader = (entry as FileSystemDirectoryEntry).createReader();
      const readBatch = async () => {
        const batch = await new Promise<FileSystemEntry[]>((resolve) => {
          reader.readEntries(resolve);
        });
        if (batch.length === 0) return;
        for (const child of batch) {
          await walkEntry(child, currentPath);
        }
        await readBatch();
      };
      await readBatch();
    }
  };

  for (const entry of entries) {
    await walkEntry(entry, "");
  }

  return result;
}

/** ファイルリストからフォルダツリーを構築 */
function buildFolderTree(files: DroppedFile[]): FolderTreeNode[] {
  const root: FolderTreeNode[] = [];
  const nodeMap = new Map<string, FolderTreeNode>();

  const getOrCreateFolder = (path: string): FolderTreeNode => {
    const existing = nodeMap.get(path);
    if (existing) return existing;

    const parts = path.split("/");
    const name = parts[parts.length - 1];
    const node: FolderTreeNode = { name, path, isFolder: true, children: [] };
    nodeMap.set(path, node);

    if (parts.length === 1) {
      root.push(node);
    } else {
      const parentPath = parts.slice(0, -1).join("/");
      const parent = getOrCreateFolder(parentPath);
      parent.children.push(node);
    }
    return node;
  };

  for (const { file, relativePath } of files) {
    const parts = relativePath.split("/");
    const name = parts[parts.length - 1];

    if (parts.length === 1) {
      const node: FolderTreeNode = {
        name,
        path: relativePath,
        isFolder: false,
        children: [],
        file,
      };
      root.push(node);
    } else {
      const parentPath = parts.slice(0, -1).join("/");
      const parent = getOrCreateFolder(parentPath);
      parent.children.push({
        name,
        path: relativePath,
        isFolder: false,
        children: [],
        file,
      });
    }
  }

  return root;
}

function parseMaterialName(line: string, fallback: string) {
  const match = line.match(/name\s*=\s*([^,]+)/i);
  if (match?.[1]) return match[1].trim();
  return fallback;
}

function extractMaterialsFromText(text: string): MaterialExtractResult {
  const lines = text.split(/\r?\n/);
  const blocks: string[] = [];
  const materialNames = new Set<string>();
  const keywords = new Set<string>();
  let currentLines: string[] = [];
  let currentName = "";
  let count = 0;

  for (const line of lines) {
    const trimmed = line.trim();
    const isStar = trimmed.startsWith("*");
    if (isStar) {
      const normalized = normalize(trimmed);
      const isMaterial = normalized.startsWith(MATERIAL_START);

      if (isMaterial) {
        if (currentLines.length > 0) {
          blocks.push(currentLines.join("\n").trimEnd());
        }
        count += 1;
        currentName = parseMaterialName(trimmed, `material-${count}`);
        materialNames.add(currentName);
        currentLines = [line];
        continue;
      }

      if (currentLines.length > 0) {
        if (MATERIAL_SET.has(normalized)) {
          const label = MATERIAL_LABELS.get(normalized);
          if (label) keywords.add(label);
          currentLines.push(line);
        } else {
          blocks.push(currentLines.join("\n").trimEnd());
          currentLines = [];
          currentName = "";
        }
      }
      continue;
    }

    if (currentLines.length > 0) {
      currentLines.push(line);
    }
  }

  if (currentLines.length > 0) {
    blocks.push(currentLines.join("\n").trimEnd());
  }

  return { blocks, materialNames, keywords };
}

/** フォルダツリー表示コンポーネント */
function FolderTreeView({
  nodes,
  depth = 0,
}: {
  nodes: FolderTreeNode[];
  depth?: number;
}) {
  const [collapsed, setCollapsed] = useState<Set<string>>(new Set());
  const sorted = [...nodes].sort((a, b) => {
    if (a.isFolder !== b.isFolder) return a.isFolder ? -1 : 1;
    return a.name.localeCompare(b.name);
  });

  return (
    <div className="text-[12px] font-mono">
      {sorted.map((node) => {
        const isOpen = !collapsed.has(node.path);
        return (
          <div key={node.path}>
            <div
              className="flex items-center gap-1 py-0.5 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded px-1"
              style={{ paddingLeft: `${depth * 16}px` }}
            >
              {node.isFolder ? (
                <button
                  type="button"
                  onClick={() =>
                    setCollapsed((prev) => {
                      const next = new Set(prev);
                      if (next.has(node.path)) next.delete(node.path);
                      else next.add(node.path);
                      return next;
                    })
                  }
                  className="flex items-center gap-1 text-neutral-600 dark:text-neutral-400"
                >
                  {isOpen ? (
                    <ChevronDown size={12} />
                  ) : (
                    <ChevronRight size={12} />
                  )}
                  <FolderOpen
                    size={14}
                    className="text-amber-500 dark:text-amber-400"
                  />
                  <span>{node.name}/</span>
                </button>
              ) : (
                <>
                  <span className="w-3" />
                  <FileText
                    size={14}
                    className="text-neutral-400 dark:text-neutral-500"
                  />
                  <span className="text-neutral-700 dark:text-neutral-300">
                    {node.name}
                  </span>
                </>
              )}
            </div>
            {node.isFolder && isOpen && node.children.length > 0 && (
              <FolderTreeView nodes={node.children} depth={depth + 1} />
            )}
          </div>
        );
      })}
    </div>
  );
}

function PropsEditor({
  userProps,
  setUserProps,
}: {
  userProps: Record<string, string>;
  setUserProps: (v: Record<string, string>) => void;
}) {
  const propInputId = "prop-input";
  const [propInput, setPropInput] = useState("");
  const addProp = () => {
    const raw = propInput.trim();
    if (!raw) return;
    const idx = raw.indexOf(":");
    if (idx < 1) return;
    const k = raw.slice(0, idx).trim();
    const v = raw.slice(idx + 1).trim();
    if (!k || !v) return;
    setUserProps({ ...userProps, [k]: v });
    setPropInput("");
  };
  return (
    <section>
      <label htmlFor={propInputId} className="block text-sm mb-2">
        プロパティ（key:value／space・enterで追加）
      </label>
      <div className="rounded-2xl border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900">
        <div className="flex flex-wrap items-center gap-2">
          {Object.entries(userProps).map(([k, v]) => (
            <span
              key={k}
              className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-[13px] font-medium border-teal-300/80 dark:border-teal-700/80 bg-teal-50/80 dark:bg-teal-800/60 text-teal-900 dark:text-teal-100"
            >
              {k}:{v}
              <button
                type="button"
                onClick={() => {
                  const x = { ...userProps };
                  delete x[k];
                  setUserProps(x);
                }}
                className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded hover:bg-teal-200/60 dark:hover:bg-teal-700"
              >
                ×
              </button>
            </span>
          ))}
          <input
            id={propInputId}
            value={propInput}
            onChange={(e) => setPropInput(e.target.value)}
            onKeyDown={(e) => {
              if (
                (e.key === "Enter" || e.key === " ") &&
                propInput.includes(":")
              ) {
                e.preventDefault();
                addProp();
              }
              if (
                e.key === "Backspace" &&
                !propInput &&
                Object.keys(userProps).length
              ) {
                const keys = Object.keys(userProps);
                const last = keys[keys.length - 1];
                if (last) {
                  const x = { ...userProps };
                  delete x[last];
                  setUserProps(x);
                }
              }
            }}
            placeholder="例: project:PRJ-1234"
            className="flex-1 min-w-[240px] bg-transparent outline-none py-1 text-sm"
          />
        </div>
      </div>
    </section>
  );
}

/** 拡張子からフォーマットを推定 */
function extToFormat(ext: string): string {
  switch (ext) {
    case "inp":
      return "abaqus_inp";
    case "csv":
      return "csv";
    case "json":
      return "json";
    case "md":
    case "markdown":
      return "markdown";
    default:
      return "";
  }
}

/** ファイルからドラフトエンティティを生成 */
async function createDraftEntity(
  file: File,
  relativePath: string,
  sysPropsBase: Record<string, string>,
): Promise<StringEntity & { _relativePath: string }> {
  const text = await file.text();
  const dot = file.name.lastIndexOf(".");
  const fileExt = dot > -1 ? file.name.slice(dot + 1).toLowerCase() : "";
  const format = extToFormat(fileExt);
  const now = new Date().toISOString();

  // INPファイルからタグ抽出
  const tags: string[] = [];
  if (fileExt === "inp") {
    const extracted = extractMaterialsFromText(text);
    for (const kw of extracted.keywords) tags.push(kw);
    for (const mn of extracted.materialNames) tags.push(mn);
  }

  return {
    id: crypto.randomUUID(),
    name: file.name,
    body: text,
    sysTags: format ? [format] : [],
    userTags: tags,
    sysProps: {
      ...sysPropsBase,
      source_filename: file.name,
      extension: fileExt,
      format,
    },
    userProps: {},
    remark: null,
    domain: null,
    domainSource: null,
    domainConfidence: null,
    createdAt: now,
    updatedAt: now,
    _relativePath: relativePath,
  };
}

/** ドラフトエンティティの型（保存時に_relativePathは除去される） */
type DraftEntity = StringEntity & { _relativePath: string };

/** フォルダモード用ビュー（カードは不要） */
const FOLDER_VIEW_OPTIONS: ViewType[] = ["table", "diagram", "graph"];

export function GenericUploader() {
  const nameInputId = "entity-name";
  const remarkInputId = "entity-remark";
  const tagInputId = "entity-tags";
  const bodyInputId = "entity-body";
  const inputRef = useRef<HTMLInputElement | null>(null);
  const [fileName, setFileName] = useState<string | null>(null);
  const [ext, setExt] = useState<string | null>(null);
  const [name, setName] = useState("");
  const [body, setBody] = useState("");
  const [remark, setRemark] = useState("");
  const [userTags, setUserTags] = useState<string[]>([]);
  const [tagInput, setTagInput] = useState("");
  const [userProps, setUserProps] = useState<Record<string, string>>({});
  const [saving, setSaving] = useState(false);
  /** インポート進捗（0〜1） */
  const [importProgress, setImportProgress] = useState(0);
  const [importTotal, setImportTotal] = useState(0);
  const [importCurrent, setImportCurrent] = useState(0);

  /** インポート先レポジトリ選択 (spec-roadmap5: 5-08) */
  const [targetRepoId, setTargetRepoId] = useState<string>(ROOT_REPOSITORY_ID);
  const [availableRepos, setAvailableRepos] = useState<StringEntity[]>([]);
  /** レポジトリタイプ選択（フォルダモードでレポジトリ作成時） */
  const [repoType, setRepoType] = useState<string>(REPOSITORY_TYPES[0]);

  useEffect(() => {
    // レポジトリ＋ユーザー名前空間の一覧取得
    fetchRepositoriesAndNamespaces().then((res) => {
      if (res.data) setAvailableRepos(res.data);
    });
    // ユーザー名前空間があればデフォルトのインポート先に設定
    fetchMyNamespace().then((res) => {
      if (res.data) {
        setTargetRepoId(res.data.id);
      }
    });
  }, []);

  /** フォルダインポート用の状態 */
  const [droppedFiles, setDroppedFiles] = useState<DroppedFile[]>([]);
  const [folderTree, setFolderTree] = useState<FolderTreeNode[]>([]);
  const [isFolderMode, setIsFolderMode] = useState(false);

  /** フォルダモード: ドラフトエンティティ（個別編集可能） */
  const [draftEntities, setDraftEntities] = useState<DraftEntity[]>([]);
  /** フォルダモード: ドラフトRelation（ラベル付きRelation） */
  const [draftRelations, setDraftRelations] = useState<Relation[]>([]);
  /** フォルダモード: プレビュービュー種類 */
  const [folderView, setFolderView] = useState<ViewType>("table");
  /** フォルダモード: 編集中のエンティティID */
  const [editingEntityId, setEditingEntityId] = useState<string | null>(null);
  /** フォルダモード: フォルダツリー表示 */
  const [showFolderTree, setShowFolderTree] = useState(false);

  /** フォルダモード: 一括タグ入力 */
  const [bulkTagInput, setBulkTagInput] = useState("");
  /** フォルダモード: 一括プロパティ入力 */
  const [bulkPropInput, setBulkPropInput] = useState("");
  /** フォルダモード: 一括Relation入力 */
  const [bulkRelationInput, setBulkRelationInput] = useState("");

  /** ボディプレビュー用の仮エンティティ（単一ファイルモード用） */
  const previewEntity: StringEntity | null = useMemo(() => {
    if (isFolderMode) return null;
    if (!body.trim()) return null;
    return {
      id: "",
      name: name || "preview",
      body,
      sysTags: [],
      userTags: [],
      sysProps: { extension: ext ?? "", format: ext ? extToFormat(ext) : "" },
      userProps: {},
      createdAt: "",
      updatedAt: "",
    };
  }, [body, name, ext, isFolderMode]);

  const detectedFormat = previewEntity ? detectFormat(previewEntity) : null;

  const sysPropsBase = useMemo(() => {
    const now = new Date().toISOString();
    return {
      ingest_time: now,
      source_filename: fileName ?? "",
      extension: ext ?? "",
    } as Record<string, string>;
  }, [fileName, ext]);

  /** フォルダモード: エンティティ変更ハンドラ */
  const handleEntityChange = useCallback((updated: StringEntity) => {
    setDraftEntities((prev) =>
      prev.map((e) =>
        e.id === updated.id
          ? { ...updated, _relativePath: e._relativePath }
          : e,
      ),
    );
  }, []);

  /** フォルダモード: 編集対象エンティティ選択 */
  const handleEditEntity = useCallback((entity: StringEntity | null) => {
    setEditingEntityId(entity?.id ?? null);
  }, []);

  /** フォルダモード: 一括タグ適用 */
  const applyBulkTags = () => {
    const tags = bulkTagInput
      .split(/[\s,]+/)
      .map((t) => t.trim())
      .filter(Boolean);
    if (tags.length === 0) return;
    setDraftEntities((prev) =>
      prev.map((e) => ({
        ...e,
        userTags: Array.from(new Set([...e.userTags, ...tags])),
      })),
    );
    setBulkTagInput("");
  };

  /** フォルダモード: 一括プロパティ適用 */
  const applyBulkProps = () => {
    const props: Record<string, string> = {};
    for (const line of bulkPropInput.split(/\r?\n/)) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      const idx = trimmed.indexOf(":");
      if (idx < 1) continue;
      const k = trimmed.slice(0, idx).trim();
      const v = trimmed.slice(idx + 1).trim();
      if (k && v) props[k] = v;
    }
    if (Object.keys(props).length === 0) return;
    setDraftEntities((prev) =>
      prev.map((e) => ({
        ...e,
        userProps: { ...e.userProps, ...props },
      })),
    );
    setBulkPropInput("");
  };

  /** フォルダモード: 一括Relation適用（全エンティティに同一ラベルで同一ターゲットを追加）
   *  3-15: relation先がインポートファイル内にない場合、DBを参照しリンクする */
  const applyBulkRelation = async () => {
    const raw = bulkRelationInput.trim();
    if (!raw) return;
    const idx = raw.indexOf(":");
    if (idx < 1) return;
    const label = raw.slice(0, idx).trim();
    const targetName = raw.slice(idx + 1).trim();
    if (!label || !targetName) return;

    // ターゲットエンティティを既存ドラフトから検索
    let targetEntity = draftEntities.find(
      (e) => e.name.toLowerCase() === targetName.toLowerCase(),
    );
    let newDrafts = draftEntities;

    // 3-15: ドラフトに無い場合はDBを検索
    if (!targetEntity) {
      try {
        const res = await searchEntities(targetName);
        if (res.data) {
          const match = res.data.find(
            (e) => e.name.toLowerCase() === targetName.toLowerCase(),
          );
          if (match) {
            const draftFromDb: DraftEntity = {
              ...match,
              _relativePath: match.name,
            };
            newDrafts = [...draftEntities, draftFromDb];
            targetEntity = draftFromDb;
            setDraftEntities(newDrafts);
          }
        }
      } catch {
        // DB接続エラー時はフォールバック（新規作成）
      }
    }

    // DB・インポートファイル双方にない場合は新規StringEntityを作成
    if (!targetEntity) {
      const newEntity: DraftEntity = {
        id: crypto.randomUUID(),
        name: targetName,
        body: `${label}: ${targetName}`,
        sysTags: [label.toLowerCase()],
        userTags: [],
        sysProps: { type: label },
        userProps: {},
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
        _relativePath: targetName,
      };
      newDrafts = [...draftEntities, newEntity];
      targetEntity = newEntity;
      setDraftEntities(newDrafts);
    }

    // 全ドラフトエンティティに対してRelationを追加（ターゲット自身は除外）
    const newRelations: Relation[] = [];
    for (const e of newDrafts) {
      if (e.id === targetEntity.id) continue;
      // 既に同じlabel+entity1+entity2のRelationがあればスキップ
      const exists = draftRelations.some(
        (r) =>
          r.label === label &&
          r.entity1Id === e.id &&
          r.entity2Id === targetEntity?.id,
      );
      if (!exists) {
        newRelations.push({
          id: crypto.randomUUID(),
          label,
          entity1Id: e.id,
          entity2Id: targetEntity.id,
          createdAt: new Date().toISOString(),
        });
      }
    }
    if (newRelations.length > 0) {
      setDraftRelations((prev) => [...prev, ...newRelations]);
    }
    setBulkRelationInput("");
  };

  /** フォルダモード用: ファイルをドラフトエンティティに変換
   *  トップレベルフォルダはレポジトリ扱い（sysTags: ["repository"]） */
  const buildDraftEntities = async (files: DroppedFile[]) => {
    const drafts: DraftEntity[] = [];
    for (const { file, relativePath } of files) {
      const draft = await createDraftEntity(file, relativePath, sysPropsBase);
      drafts.push(draft);
    }

    // フォルダパスからフォルダDraftEntityを生成
    const folderPaths = new Set<string>();
    for (const { relativePath } of files) {
      const parts = relativePath.split("/");
      for (let i = 1; i < parts.length; i++) {
        folderPaths.add(parts.slice(0, i).join("/"));
      }
    }
    const now = new Date().toISOString();

    // トップレベルフォルダを判定（パスにスラッシュが含まれない = ルート直下）
    const topLevelFolders = new Set<string>();
    for (const path of folderPaths) {
      if (!path.includes("/")) {
        topLevelFolders.add(path);
      }
    }

    const folderDrafts: DraftEntity[] = [];
    for (const path of Array.from(folderPaths).sort()) {
      const folderName = path.split("/").pop() ?? path;
      const isTopLevel = topLevelFolders.has(path);

      // トップレベルフォルダはレポジトリ扱い
      const tag = isTopLevel ? "repository" : "directory";
      const sysPropsForFolder: Record<string, string> = {
        ...sysPropsBase,
        type: tag,
      };
      if (isTopLevel) {
        sysPropsForFolder.repository_type = repoType;
      }

      folderDrafts.push({
        id: crypto.randomUUID(),
        name: folderName,
        body: isTopLevel ? `[repository] ${path}` : `[directory] ${path}`,
        sysTags: [tag],
        userTags: [],
        sysProps: sysPropsForFolder,
        userProps: {},
        remark: isTopLevel
          ? `レポジトリ: ${path} (${repoType})`
          : `フォルダ: ${path}`,
        domain: null,
        domainSource: null,
        domainConfidence: null,
        createdAt: now,
        updatedAt: now,
        _relativePath: path,
      });
    }

    const allDrafts = [...folderDrafts, ...drafts];

    // 階層Relation（child/contains）の自動生成
    const pathToId = new Map<string, string>();
    for (const d of allDrafts) pathToId.set(d._relativePath, d.id);

    const hierarchyRelations: Relation[] = [];
    for (const d of allDrafts) {
      const parts = d._relativePath.split("/");
      if (parts.length > 1) {
        const parentPath = parts.slice(0, -1).join("/");
        const parentId = pathToId.get(parentPath);
        if (parentId) {
          hierarchyRelations.push({
            id: crypto.randomUUID(),
            label:
              d.sysTags.includes("directory") ||
              d.sysTags.includes("repository")
                ? "child"
                : "contains",
            entity1Id: parentId,
            entity2Id: d.id,
            createdAt: now,
          });
        }
      }
    }

    setDraftEntities(allDrafts);
    setDraftRelations(hierarchyRelations);
    setEditingEntityId(null);
    setFolderView("table");
    setShowFolderTree(false);
    setBulkTagInput("");
    setBulkPropInput("");
  };

  const onDrop = async (items: DataTransferItemList) => {
    const dropped = await getFilesFromDataTransfer(items);
    if (dropped.length === 0) return;

    const hasFolder = dropped.some((d) => d.relativePath.includes("/"));

    if (hasFolder) {
      setIsFolderMode(true);
      setDroppedFiles(dropped);
      const tree = buildFolderTree(dropped);
      setFolderTree(tree);

      const rootName =
        tree.length === 1 && tree[0].isFolder
          ? tree[0].name
          : `import-${new Date().toISOString().slice(0, 10)}`;
      setName(rootName);
      setFileName(rootName);

      // ドラフトエンティティを生成
      await buildDraftEntities(dropped);
      return;
    }

    // 単一ファイルモード
    setIsFolderMode(false);
    setDroppedFiles(dropped);
    setFolderTree([]);
    setDraftEntities([]);
    const firstFile = dropped[0].file;
    const text = await firstFile.text();
    const extracted = extractMaterialsFromText(text);
    setBody(text);
    setFileName(firstFile.name);
    const dot = firstFile.name.lastIndexOf(".");
    setExt(dot > -1 ? firstFile.name.slice(dot + 1).toLowerCase() : null);
    if (!name) setName(firstFile.name.replace(/\.[^.]+$/, ""));
    const tagList = [
      ...Array.from(extracted.keywords),
      ...Array.from(extracted.materialNames),
    ].filter(Boolean);
    if (tagList.length > 0) {
      setUserTags((current) => Array.from(new Set([...current, ...tagList])));
    }
  };

  const onFiles = async (files: FileList | null) => {
    if (!files || files.length === 0) return;
    const fileArray = Array.from(files);
    const hasMultiple = fileArray.length > 1;
    const firstFile = fileArray[0];

    const folder =
      fileArray
        .map((file) =>
          "webkitRelativePath" in file && file.webkitRelativePath
            ? file.webkitRelativePath.split("/")[0]
            : "",
        )
        .find(Boolean) || "";

    // webkitRelativePathがある場合はフォルダモード
    if (folder) {
      const dropped: DroppedFile[] = fileArray.map((file) => ({
        file,
        relativePath:
          (file as File & { webkitRelativePath?: string }).webkitRelativePath ||
          file.name,
      }));
      setDroppedFiles(dropped);
      setIsFolderMode(true);
      const tree = buildFolderTree(dropped);
      setFolderTree(tree);
      setName(folder);
      setFileName(folder);

      // ドラフトエンティティを生成
      await buildDraftEntities(dropped);
      return;
    }

    const folderName = firstFile.name.replace(/\.[^.]+$/, "");
    const materialNames = new Set<string>();
    const keywords = new Set<string>();

    if (hasMultiple) {
      setIsFolderMode(false);
      setDroppedFiles(
        fileArray.map((f) => ({ file: f, relativePath: f.name })),
      );
      setFolderTree([]);
      setDraftEntities([]);
      const blocks: string[] = [];
      let firstInpName = "";
      for (const file of fileArray) {
        if (!file.name.toLowerCase().endsWith(".inp")) continue;
        if (!firstInpName) {
          firstInpName = file.name.replace(/\.[^.]+$/, "");
        }
        const text = await file.text();
        const extracted = extractMaterialsFromText(text);
        for (const block of extracted.blocks) blocks.push(block);
        for (const value of extracted.materialNames) materialNames.add(value);
        for (const value of extracted.keywords) keywords.add(value);
      }
      const combinedBody = blocks.join("\n\n");
      const displayName = firstInpName || folderName;
      setBody(combinedBody);
      setFileName(displayName);
      setExt("inp");
      setName(displayName);
      const tagList = [
        ...Array.from(keywords),
        ...Array.from(materialNames),
      ].filter(Boolean);
      if (tagList.length > 0) {
        setUserTags((current) => Array.from(new Set([...current, ...tagList])));
      }
      return;
    }

    // 単一ファイル
    setIsFolderMode(false);
    setDroppedFiles([{ file: firstFile, relativePath: firstFile.name }]);
    setFolderTree([]);
    setDraftEntities([]);
    const text = await firstFile.text();
    const extracted = extractMaterialsFromText(text);
    setBody(text);
    setFileName(firstFile.name);
    const dot = firstFile.name.lastIndexOf(".");
    setExt(dot > -1 ? firstFile.name.slice(dot + 1).toLowerCase() : null);
    if (!name) setName(firstFile.name.replace(/\.[^.]+$/, ""));
    const tagList = [
      ...Array.from(extracted.keywords),
      ...Array.from(extracted.materialNames),
    ].filter(Boolean);
    if (tagList.length > 0) {
      setUserTags((current) => Array.from(new Set([...current, ...tagList])));
    }
  };

  const hasBody = isFolderMode
    ? draftEntities.length > 0
    : body.trim().length > 0;

  const addTag = () => {
    const v = tagInput.trim();
    if (!v) return;
    setTagInput("");
    if (v.includes(":")) {
      const idx = v.indexOf(":");
      const k = v.slice(0, idx).trim();
      const val = v.slice(idx + 1).trim();
      if (k && val) {
        setUserProps({ ...userProps, [k]: val });
        return;
      }
    }
    const key = v.toLowerCase();
    if (!userTags.some((t) => t.toLowerCase() === key))
      setUserTags([...userTags, v]);
  };

  async function saveBundle() {
    if (!hasBody) return;
    setSaving(true);
    setImportProgress(0);
    setImportCurrent(0);
    try {
      const now = new Date().toISOString();

      if (isFolderMode && draftEntities.length > 0) {
        const totalSteps = draftEntities.length + draftRelations.length;
        setImportTotal(totalSteps);
        let completedSteps = 0;

        // 3-17: フォルダ・ファイル全ドラフトエンティティを一括保存
        for (const draft of draftEntities) {
          const { _relativePath, ...entity } = draft;
          await createEntity({
            ...entity,
            createdAt: now,
            updatedAt: now,
          });
          completedSteps++;
          setImportCurrent(completedSteps);
          setImportProgress(completedSteps / totalSteps);
        }

        // ドラフトRelationの保存（階層child/contains + ユーザー追加）
        for (const rel of draftRelations) {
          await createRelation({
            label: rel.label,
            entity1Id: rel.entity1Id,
            entity2Id: rel.entity2Id,
          });
          completedSteps++;
          setImportCurrent(completedSteps);
          setImportProgress(completedSteps / totalSteps);
        }

        // トップレベルノードを選択先に紐付け
        const childEntityIds = new Set(
          draftRelations
            .filter((r) => r.label === "child" || r.label === "contains")
            .map((r) => r.entity2Id),
        );
        const topLevelEntities = draftEntities.filter(
          (e) => !childEntityIds.has(e.id),
        );
        for (const topEntity of topLevelEntities) {
          // レポジトリ/ディレクトリ → child, その他 → contains
          const label =
            topEntity.sysTags.includes("repository") ||
            topEntity.sysTags.includes("directory")
              ? "child"
              : "contains";
          await createRelation({
            label,
            entity1Id: targetRepoId,
            entity2Id: topEntity.id,
          });
          completedSteps++;
        }

        alert(
          `フォルダインポート完了: ${draftEntities.length} エンティティ、${draftRelations.length + topLevelEntities.length} Relation を作成しました`,
        );
      } else {
        // 単一ファイルモード（従来の動作）
        const id = crypto.randomUUID();
        const entity: StringEntity = {
          id,
          name:
            name.trim() || (fileName ? fileName.replace(/\.[^.]+$/, "") : id),
          body,
          sysTags: [],
          userTags,
          sysProps: sysPropsBase,
          userProps,
          remark: remark.trim() || null,
          domain: null,
          domainSource: null,
          domainConfidence: null,
          createdAt: now,
          updatedAt: now,
        };

        const apiRes = await createEntity(entity);
        if (apiRes.error) {
          alert(`DB保存エラー: ${apiRes.error}`);
          return;
        }

        // 5-10: 単体エンティティもレポジトリに紐付け
        await createRelation({
          label: "contains",
          entity1Id: targetRepoId,
          entity2Id: id,
        });

        alert(`保存しました: ${entity.name} (ID: ${id})`);
      }

      // フォームをリセット
      setFileName(null);
      setExt(null);
      setName("");
      setBody("");
      setRemark("");
      setUserTags([]);
      setUserProps({});
      setDroppedFiles([]);
      setFolderTree([]);
      setIsFolderMode(false);
      setDraftEntities([]);
      setEditingEntityId(null);
      setBulkTagInput("");
      setBulkPropInput("");
    } finally {
      setSaving(false);
      setImportProgress(0);
      setImportCurrent(0);
      setImportTotal(0);
    }
  }

  /* ============================================
   * レンダリング
   * ============================================ */
  return (
    <div className="space-y-6">
      {/* インポート先レポジトリ選択 (spec-roadmap5: 5-08) */}
      <section className="rounded-xl border border-violet-200 dark:border-violet-800 bg-violet-50/50 dark:bg-violet-950/30 p-3">
        <div className="flex items-center gap-2">
          <span className="text-xs font-medium text-violet-700 dark:text-violet-300">
            インポート先:
          </span>
          <select
            value={targetRepoId}
            onChange={(e) => setTargetRepoId(e.target.value)}
            className="flex-1 rounded-lg border border-violet-300 dark:border-violet-700 bg-white dark:bg-neutral-900 px-2 py-1.5 text-sm"
          >
            {availableRepos.map((repo) => (
              <option key={repo.id} value={repo.id}>
                {repo.id === ROOT_REPOSITORY_ID
                  ? `${repo.name}（ルート）`
                  : repo.sysTags.includes("user_namespace")
                    ? `${repo.name}/（ユーザー）`
                    : repo.name}
              </option>
            ))}
          </select>
        </div>
        <p className="mt-1 text-[11px] text-violet-500 dark:text-violet-400">
          {isFolderMode
            ? "フォルダはレポジトリとして選択先の配下に作成されます（GitHub形式: ユーザー/レポジトリ）"
            : "インポートされたエンティティは選択先の配下に配置されます"}
        </p>
      </section>

      {/* レポジトリタイプ選択（フォルダモード時のみ表示） */}
      {isFolderMode && (
        <section className="rounded-xl border border-emerald-200 dark:border-emerald-800 bg-emerald-50/50 dark:bg-emerald-950/30 p-3">
          <div className="flex items-center gap-2">
            <span className="text-xs font-medium text-emerald-700 dark:text-emerald-300">
              レポジトリタイプ:
            </span>
            <select
              value={repoType}
              onChange={(e) => setRepoType(e.target.value)}
              className="flex-1 rounded-lg border border-emerald-300 dark:border-emerald-700 bg-white dark:bg-neutral-900 px-2 py-1.5 text-sm"
            >
              {REPOSITORY_TYPES.map((t) => (
                <option key={t} value={t}>
                  {t}
                </option>
              ))}
            </select>
          </div>
          <p className="mt-1 text-[11px] text-emerald-500 dark:text-emerald-400">
            管理データの大分類（CAE案件、材料物性など）を選択してください
          </p>
        </section>
      )}

      {/* ドロップゾーン */}
      <section>
        <label
          onDragOver={(e) => e.preventDefault()}
          onDrop={async (e) => {
            e.preventDefault();
            if (e.dataTransfer.items?.length) {
              await onDrop(e.dataTransfer.items);
              return;
            }
            onFiles(e.dataTransfer.files);
          }}
          className="flex flex-col items-center justify-center gap-3 border-2 border-dashed rounded-2xl p-8 text-center cursor-pointer border-neutral-300 dark:border-neutral-700 hover:bg-neutral-50 dark:hover:bg-neutral-900 w-full max-w-2xl aspect-[2/1] mx-auto"
        >
          <UploadCloud size={28} />
          <div className="text-sm">
            ここにフォルダ/ファイルをドロップ、またはクリックして選択
          </div>
          <input
            ref={inputRef}
            type="file"
            multiple
            accept=".inp,.txt,.md,.json,.csv,application/octet-stream,text/plain"
            onChange={(e) => onFiles(e.target.files)}
            // @ts-expect-error webkitdirectory is supported in Chromium based browsers.
            webkitdirectory="true"
            className="hidden"
          />
        </label>
        {fileName && (
          <div className="mt-2 text-xs text-neutral-500">
            読み込み: <span className="font-mono">{fileName}</span>{" "}
            {ext && <span>（.{ext}）</span>}
            {isFolderMode && (
              <span className="ml-2 text-amber-600 dark:text-amber-400">
                フォルダモード: {droppedFiles.length} ファイル
              </span>
            )}
          </div>
        )}
      </section>

      {/* ===========================
       * フォルダモード: エンティティ編集UI
       * =========================== */}
      {isFolderMode && draftEntities.length > 0 && (
        <>
          {/* フォルダツリー（折りたたみ可能） */}
          {folderTree.length > 0 && (
            <section>
              <button
                type="button"
                onClick={() => setShowFolderTree(!showFolderTree)}
                className="flex items-center gap-1 text-sm font-medium mb-2 hover:text-neutral-700 dark:hover:text-neutral-200"
              >
                <FolderOpen size={14} className="text-amber-500" />
                フォルダ構成（{droppedFiles.length} ファイル）
                {showFolderTree ? (
                  <ChevronDown size={14} />
                ) : (
                  <ChevronRight size={14} />
                )}
              </button>
              {showFolderTree && (
                <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 max-h-48 overflow-y-auto">
                  <FolderTreeView nodes={folderTree} />
                </div>
              )}
              <p className="mt-1.5 text-[11px] text-neutral-500">
                トップレベルフォルダはレポジトリ（type: {repoType}
                ）として登録されます。 サブフォルダは directory
                エンティティとして登録されます。
              </p>
            </section>
          )}

          {/* 一括編集セクション */}
          <section className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white/80 dark:bg-neutral-900/60 p-4">
            <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300 mb-3">
              一括編集（全エンティティに適用）
            </h3>
            <div className="grid gap-3 md:grid-cols-2">
              {/* 一括タグ */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
                <label className="flex items-center gap-2 text-xs text-neutral-500 mb-2">
                  <Tag size={12} />
                  一括タグ追加（空白/カンマ区切り）
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={bulkTagInput}
                    onChange={(e) => setBulkTagInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        applyBulkTags();
                      }
                    }}
                    placeholder="タグ1, タグ2"
                    className="flex-1 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    onClick={applyBulkTags}
                    className="rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-50 dark:hover:bg-neutral-800"
                  >
                    適用
                  </button>
                </div>
              </div>
              {/* 一括プロパティ */}
              <div className="rounded-lg border border-neutral-200 dark:border-neutral-800 p-3">
                <label className="flex items-center gap-2 text-xs text-neutral-500 mb-2">
                  一括プロパティ追加（key:value 改行区切り）
                </label>
                <div className="flex gap-2">
                  <input
                    type="text"
                    value={bulkPropInput}
                    onChange={(e) => setBulkPropInput(e.target.value)}
                    onKeyDown={(e) => {
                      if (e.key === "Enter") {
                        e.preventDefault();
                        applyBulkProps();
                      }
                    }}
                    placeholder="project:PRJ-001"
                    className="flex-1 rounded-lg border border-neutral-200 dark:border-neutral-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm"
                  />
                  <button
                    type="button"
                    onClick={applyBulkProps}
                    className="rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-1.5 text-xs hover:bg-neutral-50 dark:hover:bg-neutral-800"
                  >
                    適用
                  </button>
                </div>
              </div>
            </div>
            {/* 一括Relation追加 */}
            <div className="mt-3 rounded-lg border border-purple-200 dark:border-purple-800 p-3">
              <label className="flex items-center gap-2 text-xs text-purple-600 dark:text-purple-400 mb-2">
                <Link2 size={12} />
                一括Relation追加（label:対象名 —
                全エンティティに同じRelation追加）
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={bulkRelationInput}
                  onChange={(e) => setBulkRelationInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === "Enter") {
                      e.preventDefault();
                      applyBulkRelation();
                    }
                  }}
                  placeholder="カテゴリ:金属"
                  className="flex-1 rounded-lg border border-purple-200 dark:border-purple-800 bg-white dark:bg-neutral-950 px-3 py-1.5 text-sm"
                />
                <button
                  type="button"
                  onClick={applyBulkRelation}
                  className="rounded-lg border border-purple-200 dark:border-purple-700 px-3 py-1.5 text-xs text-purple-700 dark:text-purple-300 hover:bg-purple-50 dark:hover:bg-purple-900/30"
                >
                  適用
                </button>
              </div>
              {draftRelations.length > 0 && (
                <div className="mt-2 text-[11px] text-purple-500">
                  {draftRelations.length} Relation 定義済み
                </div>
              )}
            </div>
          </section>

          {/* ビュースイッチャー + プレビュー/編集ビュー */}
          <section>
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-semibold text-neutral-700 dark:text-neutral-300">
                エンティティプレビュー・編集（{draftEntities.length} 件）
              </h3>
              <ViewSwitcher
                value={folderView}
                onChange={setFolderView}
                views={FOLDER_VIEW_OPTIONS}
                size="sm"
              />
            </div>

            {folderView === "table" && (
              <EntityTable
                entities={draftEntities}
                editable
                enableFiltering
                enableHierarchy
                enableFullTextSearch
                enableBodyColumn
                enableMultiCellSelect
                onEntityChange={handleEntityChange}
                editingEntityId={editingEntityId}
                onEditEntity={handleEditEntity}
                relations={draftRelations}
                allEntities={draftEntities}
                onRelationsChange={setDraftRelations}
              />
            )}

            {folderView === "diagram" && (
              <EntityDiagram
                entities={draftEntities}
                editable
                onEntityChange={handleEntityChange}
                editingEntityId={editingEntityId}
                onEditEntity={handleEditEntity}
                height={500}
                showHierarchyBar={false}
                relations={draftRelations}
              />
            )}

            {folderView === "graph" && (
              <EntityGraph
                entities={draftEntities}
                editable
                onEntityChange={handleEntityChange}
                editingEntityId={editingEntityId}
                onEditEntity={handleEditEntity}
                height={500}
                showHierarchyBar={false}
                relations={draftRelations}
              />
            )}
          </section>
        </>
      )}

      {/* ===========================
       * 単一ファイルモード: 従来のフォーム
       * =========================== */}
      {!isFolderMode && (
        <>
          <section className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label htmlFor={nameInputId} className="block text-sm mb-1">
                名前
              </label>
              <input
                id={nameInputId}
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="表示名"
                className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2"
              />
            </div>
            <div>
              <label htmlFor={remarkInputId} className="block text-sm mb-1">
                備考
              </label>
              <input
                id={remarkInputId}
                value={remark}
                onChange={(e) => setRemark(e.target.value)}
                placeholder="用途・注意点など（任意）"
                className="w-full rounded-xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 px-3 py-2"
              />
            </div>
          </section>

          {/* タグ */}
          <section>
            <label htmlFor={tagInputId} className="block text-sm mb-2">
              ユーザータグ（space/enterで追加）
            </label>
            <div className="rounded-2xl border border-neutral-300 dark:border-neutral-700 px-3 py-2 bg-white dark:bg-neutral-900">
              <div className="flex flex-wrap items-center gap-2">
                {userTags.map((t) => (
                  <span
                    key={t}
                    className="inline-flex items-center gap-1.5 whitespace-nowrap rounded-full border px-3 py-1.5 text-[13px] font-medium border-sky-300/80 dark:border-sky-700/80 bg-sky-50/80 dark:bg-sky-800/60 text-sky-900 dark:text-sky-100"
                  >
                    <Tag size={14} /> {t}
                    <button
                      type="button"
                      onClick={() =>
                        setUserTags(userTags.filter((tag) => tag !== t))
                      }
                      className="ml-1 inline-flex h-4 w-4 items-center justify-center rounded hover:bg-sky-200/60 dark:hover:bg-sky-700"
                    >
                      <X size={12} />
                    </button>
                  </span>
                ))}
                <input
                  id={tagInputId}
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (
                      (e.key === "Enter" || e.key === " ") &&
                      tagInput.trim()
                    ) {
                      e.preventDefault();
                      addTag();
                    }
                    if (e.key === "Backspace" && !tagInput && userTags.length)
                      setUserTags(userTags.slice(0, -1));
                  }}
                  placeholder="#タグ名 または key:value"
                  className="flex-1 min-w-[160px] bg-transparent outline-none py-1 text-sm"
                />
              </div>
            </div>
          </section>

          {/* プロパティ */}
          <PropsEditor userProps={userProps} setUserProps={setUserProps} />

          {/* 本文エディタ＋プレビュー */}
          <section>
            <div className="flex items-center justify-between mb-1">
              <label htmlFor={bodyInputId} className="block text-sm">
                本文（プレビュー＆編集可）
              </label>
              {detectedFormat && (
                <span className="text-[11px] px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800 text-neutral-600 dark:text-neutral-400">
                  検出: {formatLabel(detectedFormat)}
                </span>
              )}
            </div>
            <textarea
              id={bodyInputId}
              value={body}
              onChange={(e) => setBody(e.target.value)}
              rows={10}
              placeholder="*Material, name=...
*Density
..."
              className="w-full rounded-2xl border border-neutral-300 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 font-mono text-[12.5px] leading-snug"
            />
          </section>

          {/* ボディプレビュー（即時プレビュー） */}
          {previewEntity && (
            <section>
              <h3 className="text-sm font-medium mb-1">プレビュー</h3>
              <div className="rounded-xl border border-neutral-200 dark:border-neutral-700 bg-white dark:bg-neutral-900 p-3 max-h-64 overflow-y-auto">
                <BodyRenderer entity={previewEntity} maxLines={20} />
              </div>
            </section>
          )}
        </>
      )}

      {/* 進捗表示 */}
      {saving && importTotal > 0 && (
        <div className="space-y-2">
          <div className="flex items-center justify-between text-sm">
            <span className="text-neutral-600 dark:text-neutral-400">
              インポート中... {importCurrent} / {importTotal}
            </span>
            <span className="font-medium text-sky-600 dark:text-sky-400">
              {Math.round(importProgress * 100)}%
            </span>
          </div>
          <div className="w-full h-2 bg-neutral-200 dark:bg-neutral-700 rounded-full overflow-hidden">
            <div
              className="h-full bg-sky-500 rounded-full transition-all duration-200"
              style={{ width: `${importProgress * 100}%` }}
            />
          </div>
        </div>
      )}

      {/* 保存ボタン */}
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={() => inputRef.current?.click()}
          className="inline-flex items-center gap-2 rounded-xl border border-neutral-300 dark:border-neutral-700 px-3 py-2 hover:bg-neutral-50 dark:hover:bg-neutral-800"
        >
          ファイルを選択
        </button>
        <button
          type="button"
          onClick={saveBundle}
          disabled={!hasBody || saving}
          className="inline-flex items-center gap-2 rounded-xl border border-transparent bg-neutral-900 text-white px-4 py-2 disabled:opacity-50"
        >
          {saving ? (
            <Loader2 className="animate-spin" size={16} />
          ) : (
            <Save size={16} />
          )}{" "}
          {isFolderMode
            ? `フォルダをインポート（${draftEntities.length} 件）`
            : "DBに保存"}
        </button>
      </div>
    </div>
  );
}
