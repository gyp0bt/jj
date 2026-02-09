"use client";

import {
  ChevronDown,
  ChevronRight,
  ChevronUp,
  FileWarning,
  UnfoldVertical,
} from "lucide-react";
import { useMemo, useState } from "react";
import type { StringEntity } from "@/lib/types";

// ========================================
// フォーマット検出
// ========================================

export type BodyFormat =
  | "abaqus_inp"
  | "csv"
  | "json"
  | "markdown"
  | "python"
  | "plain";

/**
 * エンティティからボディのフォーマットを推定する
 * 優先順: sysProps.format > userProps.format > domain > extension > 内容解析
 */
export function detectFormat(entity: StringEntity): BodyFormat {
  // 1. 明示的なformat属性
  const explicit = entity.sysProps?.format ?? entity.userProps?.format ?? null;
  if (explicit) {
    const f = explicit.toLowerCase();
    if (f === "abaqus_inp" || f === "inp") return "abaqus_inp";
    if (f === "csv") return "csv";
    if (f === "json") return "json";
    if (f === "markdown" || f === "md") return "markdown";
    if (f === "python" || f === "py") return "python";
    return "plain";
  }

  // 2. domain
  if (entity.domain) {
    const d = entity.domain.toLowerCase();
    if (d === "abaqus_inp" || d.includes("abaqus")) return "abaqus_inp";
  }

  // 3. extension
  const ext = (entity.sysProps?.extension ?? "").toLowerCase();
  if (ext === "inp") return "abaqus_inp";
  if (ext === "csv") return "csv";
  if (ext === "json") return "json";
  if (ext === "md" || ext === "markdown") return "markdown";
  if (ext === "py") return "python";

  // 4. 内容ヒューリスティック
  const body = entity.body;
  if (body.startsWith("{") || body.startsWith("[")) {
    try {
      JSON.parse(body);
      return "json";
    } catch {
      // JSONではない
    }
  }
  if (/^\*\w/m.test(body) && /^\*\*/m.test(body) === false) {
    // Abaqus inp: *keyword行があり、Markdownの太字(**) ではない
    if (/^\*material|^\*elastic|^\*plastic|^\*conductivity/im.test(body)) {
      return "abaqus_inp";
    }
  }
  // Python: def/class/import/from が行頭にある
  if (/^(def |class |import |from \S+ import )/m.test(body)) return "python";
  if (/^#\s|^##\s|^###\s/m.test(body)) return "markdown";
  if (body.includes(",") && body.split("\n").length > 1) {
    const lines = body.split("\n").filter((l) => l.trim());
    if (lines.length >= 2) {
      const commaCountFirst = (lines[0].match(/,/g) || []).length;
      const commaCountSecond = (lines[1].match(/,/g) || []).length;
      if (commaCountFirst > 0 && commaCountFirst === commaCountSecond) {
        return "csv";
      }
    }
  }

  return "plain";
}

// ========================================
// Abaqus INP レンダラー
// ========================================

function AbaqusInpRenderer({ body }: { body: string }) {
  const lines = body.split("\n");

  return (
    <pre className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap">
      {lines.map((line, i) => {
        const trimmed = line.trimStart();
        if (trimmed.startsWith("**")) {
          // コメント行
          return (
            <span key={i} className="text-emerald-600 dark:text-emerald-400">
              {line}
              {"\n"}
            </span>
          );
        }
        if (trimmed.startsWith("*")) {
          // キーワード行
          return (
            <span
              key={i}
              className="text-sky-600 dark:text-sky-400 font-semibold"
            >
              {line}
              {"\n"}
            </span>
          );
        }
        // データ行
        return (
          <span key={i}>
            {line}
            {"\n"}
          </span>
        );
      })}
    </pre>
  );
}

// ========================================
// CSV レンダラー
// ========================================

function CsvRenderer({ body }: { body: string }) {
  const lines = body.split("\n").filter((l) => l.trim());
  if (lines.length === 0)
    return <pre className="font-mono text-[13px]">{body}</pre>;

  const rows = lines.map((line) => line.split(",").map((cell) => cell.trim()));
  const maxCols = Math.max(...rows.map((r) => r.length));

  return (
    <div className="overflow-x-auto">
      <table className="border-collapse text-[13px] font-mono w-full">
        <thead>
          <tr>
            <th className="px-2 py-1 border border-neutral-300 dark:border-neutral-600 bg-neutral-100 dark:bg-neutral-800 text-neutral-500 text-right w-8">
              #
            </th>
            {Array.from({ length: maxCols }, (_, ci) => (
              <th
                key={ci}
                className="px-3 py-1.5 border border-neutral-300 dark:border-neutral-600 bg-neutral-100 dark:bg-neutral-800 text-left font-semibold"
              >
                {rows[0]?.[ci] ?? ""}
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.slice(1).map((row, ri) => (
            <tr
              key={ri}
              className={
                ri % 2 === 0
                  ? "bg-white dark:bg-neutral-900"
                  : "bg-neutral-50 dark:bg-neutral-800/50"
              }
            >
              <td className="px-2 py-1 border border-neutral-300 dark:border-neutral-600 text-neutral-400 text-right">
                {ri + 1}
              </td>
              {Array.from({ length: maxCols }, (_, ci) => (
                <td
                  key={ci}
                  className="px-3 py-1 border border-neutral-300 dark:border-neutral-600"
                >
                  {row[ci] ?? ""}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

// ========================================
// JSON レンダラー
// ========================================

function JsonRenderer({ body }: { body: string }) {
  let formatted: string;
  try {
    const parsed = JSON.parse(body);
    formatted = JSON.stringify(parsed, null, 2);
  } catch {
    formatted = body;
  }

  const lines = formatted.split("\n");

  return (
    <pre className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap">
      {lines.map((line, i) => {
        // キーの色付け
        const keyMatch = line.match(/^(\s*)"([^"]+)"(\s*:\s*)/);
        if (keyMatch) {
          const indent = keyMatch[1];
          const key = keyMatch[2];
          const separator = keyMatch[3];
          const rest = line.slice(
            indent.length + key.length + 2 + separator.length,
          );
          return (
            <span key={i}>
              {indent}
              <span className="text-violet-600 dark:text-violet-400">
                &quot;{key}&quot;
              </span>
              {separator}
              <span className="text-amber-700 dark:text-amber-300">{rest}</span>
              {"\n"}
            </span>
          );
        }
        // 文字列値
        if (/^\s*"/.test(line)) {
          return (
            <span key={i} className="text-amber-700 dark:text-amber-300">
              {line}
              {"\n"}
            </span>
          );
        }
        return (
          <span key={i}>
            {line}
            {"\n"}
          </span>
        );
      })}
    </pre>
  );
}

// ========================================
// Markdown レンダラー（簡易）
// ========================================

function MarkdownRenderer({
  body,
  attachedDocuments,
}: {
  body: string;
  attachedDocuments?: { relativePath: string; documentId: number }[];
}) {
  // 簡易Markdown→HTML変換
  const lines = body.split("\n");
  const elements: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBuffer: string[] = [];

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // コードブロック
    if (line.trimStart().startsWith("```")) {
      if (inCodeBlock) {
        elements.push(
          <pre
            key={`code-${i}`}
            className="my-2 p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800 font-mono text-[13px] overflow-x-auto"
          >
            {codeBuffer.join("\n")}
          </pre>,
        );
        codeBuffer = [];
        inCodeBlock = false;
      } else {
        inCodeBlock = true;
      }
      continue;
    }

    if (inCodeBlock) {
      codeBuffer.push(line);
      continue;
    }

    // 見出し
    const h3Match = line.match(/^###\s+(.*)/);
    if (h3Match) {
      elements.push(
        <h4
          key={i}
          className="text-base font-semibold mt-4 mb-1 text-neutral-800 dark:text-neutral-200"
        >
          {h3Match[1]}
        </h4>,
      );
      continue;
    }
    const h2Match = line.match(/^##\s+(.*)/);
    if (h2Match) {
      elements.push(
        <h3
          key={i}
          className="text-lg font-semibold mt-5 mb-2 text-neutral-800 dark:text-neutral-200 border-b border-neutral-200 dark:border-neutral-700 pb-1"
        >
          {h2Match[1]}
        </h3>,
      );
      continue;
    }
    const h1Match = line.match(/^#\s+(.*)/);
    if (h1Match) {
      elements.push(
        <h2
          key={i}
          className="text-xl font-bold mt-6 mb-2 text-neutral-900 dark:text-neutral-100 border-b-2 border-neutral-300 dark:border-neutral-600 pb-1"
        >
          {h1Match[1]}
        </h2>,
      );
      continue;
    }

    // リスト
    const ulMatch = line.match(/^(\s*)[-*]\s+(.*)/);
    if (ulMatch) {
      const indent = Math.floor(ulMatch[1].length / 2);
      elements.push(
        <div
          key={i}
          className="flex items-start gap-2 text-sm"
          style={{ paddingLeft: `${indent * 16 + 8}px` }}
        >
          <span className="text-neutral-400 mt-0.5">-</span>
          <span>{renderInlineMarkdown(ulMatch[2], attachedDocuments)}</span>
        </div>,
      );
      continue;
    }

    // 番号付きリスト
    const olMatch = line.match(/^(\s*)\d+\.\s+(.*)/);
    if (olMatch) {
      const num = line.match(/^(\s*)(\d+)\./);
      elements.push(
        <div
          key={i}
          className="flex items-start gap-2 text-sm"
          style={{ paddingLeft: "8px" }}
        >
          <span className="text-neutral-500 font-mono min-w-[1.5em] text-right">
            {num?.[2]}.
          </span>
          <span>{renderInlineMarkdown(olMatch[2], attachedDocuments)}</span>
        </div>,
      );
      continue;
    }

    // 空行
    if (!line.trim()) {
      elements.push(<div key={i} className="h-2" />);
      continue;
    }

    // 通常テキスト
    elements.push(
      <p key={i} className="text-sm leading-relaxed">
        {renderInlineMarkdown(line, attachedDocuments)}
      </p>,
    );
  }

  // 閉じ忘れのコードブロック
  if (inCodeBlock && codeBuffer.length > 0) {
    elements.push(
      <pre
        key="code-end"
        className="my-2 p-3 rounded-lg bg-neutral-100 dark:bg-neutral-800 font-mono text-[13px] overflow-x-auto"
      >
        {codeBuffer.join("\n")}
      </pre>,
    );
  }

  return <div className="prose-sm">{elements}</div>;
}

/** インラインMarkdown（太字、コード、リンク） */
function renderInlineMarkdown(
  text: string,
  attachedDocuments?: { relativePath: string; documentId: number }[],
): React.ReactNode {
  const parts: React.ReactNode[] = [];
  // パターン: **bold**, `code`, [text](link), [[wikilink]]
  const regex =
    /\*\*(.+?)\*\*|`([^`]+)`|\[([^\]]+)\]\(([^)]+)\)|\[\[([^\]]+)\]\]/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[1]) {
      // **bold**
      parts.push(
        <strong key={match.index} className="font-semibold">
          {match[1]}
        </strong>,
      );
    } else if (match[2]) {
      // `code`
      parts.push(
        <code
          key={match.index}
          className="px-1 py-0.5 rounded bg-neutral-100 dark:bg-neutral-800 text-[12px] font-mono text-rose-600 dark:text-rose-400"
        >
          {match[2]}
        </code>,
      );
    } else if (match[3] && match[4]) {
      // [text](link) - check if link refers to attached document
      const href = match[4];
      const doc = attachedDocuments?.find((d) => d.relativePath === href);
      parts.push(
        <span
          key={match.index}
          className="text-sky-600 dark:text-sky-400 underline cursor-pointer"
          title={doc ? `Document #${doc.documentId}` : href}
        >
          {match[3]}
        </span>,
      );
    } else if (match[5]) {
      // [[wikilink]]
      const linkName = match[5];
      const doc = attachedDocuments?.find(
        (d) =>
          d.relativePath.includes(linkName) ||
          d.relativePath.endsWith(`${linkName}.md`),
      );
      parts.push(
        <span
          key={match.index}
          className={`underline cursor-pointer ${
            doc
              ? "text-sky-600 dark:text-sky-400"
              : "text-neutral-400 dark:text-neutral-500"
          }`}
          title={doc ? `Document #${doc.documentId}` : `${linkName} (未リンク)`}
        >
          {linkName}
        </span>,
      );
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length === 1 ? parts[0] : <>{parts}</>;
}

// ========================================
// Python レンダラー (25-09)
// ========================================

const PY_KEYWORDS = new Set([
  "False",
  "None",
  "True",
  "and",
  "as",
  "assert",
  "async",
  "await",
  "break",
  "class",
  "continue",
  "def",
  "del",
  "elif",
  "else",
  "except",
  "finally",
  "for",
  "from",
  "global",
  "if",
  "import",
  "in",
  "is",
  "lambda",
  "nonlocal",
  "not",
  "or",
  "pass",
  "raise",
  "return",
  "try",
  "while",
  "with",
  "yield",
]);

const PY_BUILTINS = new Set([
  "print",
  "len",
  "range",
  "int",
  "float",
  "str",
  "list",
  "dict",
  "set",
  "tuple",
  "bool",
  "type",
  "isinstance",
  "enumerate",
  "zip",
  "map",
  "filter",
  "open",
  "super",
  "property",
  "staticmethod",
  "classmethod",
  "abs",
  "max",
  "min",
  "sum",
  "sorted",
  "reversed",
  "any",
  "all",
  "next",
  "iter",
  "hasattr",
  "getattr",
  "setattr",
]);

function PythonRenderer({ body }: { body: string }) {
  const lines = body.split("\n");

  return (
    <pre className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap">
      {lines.map((line, i) => (
        <span key={i}>
          {tokenizePythonLine(line)}
          {"\n"}
        </span>
      ))}
    </pre>
  );
}

function tokenizePythonLine(line: string): React.ReactNode[] {
  const parts: React.ReactNode[] = [];
  // パターン: コメント, 文字列("""/'''/"/'), デコレータ, 数値, 識別子
  const regex =
    /(#.*$)|("""[\s\S]*?"""|'''[\s\S]*?'''|"(?:[^"\\]|\\.)*"|'(?:[^'\\]|\\.)*')|(@\w+)|(\b\d+(?:\.\d+)?(?:e[+-]?\d+)?\b)|(\b[a-zA-Z_]\w*\b)/gm;
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(line)) !== null) {
    if (match.index > lastIndex) {
      parts.push(line.slice(lastIndex, match.index));
    }
    if (match[1]) {
      // コメント
      parts.push(
        <span key={match.index} className="text-neutral-400 italic">
          {match[1]}
        </span>,
      );
    } else if (match[2]) {
      // 文字列
      parts.push(
        <span
          key={match.index}
          className="text-emerald-600 dark:text-emerald-400"
        >
          {match[2]}
        </span>,
      );
    } else if (match[3]) {
      // デコレータ
      parts.push(
        <span key={match.index} className="text-amber-600 dark:text-amber-400">
          {match[3]}
        </span>,
      );
    } else if (match[4]) {
      // 数値
      parts.push(
        <span
          key={match.index}
          className="text-orange-600 dark:text-orange-400"
        >
          {match[4]}
        </span>,
      );
    } else if (match[5]) {
      // 識別子
      if (PY_KEYWORDS.has(match[5])) {
        parts.push(
          <span
            key={match.index}
            className="text-violet-600 dark:text-violet-400 font-semibold"
          >
            {match[5]}
          </span>,
        );
      } else if (PY_BUILTINS.has(match[5])) {
        parts.push(
          <span key={match.index} className="text-sky-600 dark:text-sky-400">
            {match[5]}
          </span>,
        );
      } else {
        parts.push(match[5]);
      }
    }
    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < line.length) {
    parts.push(line.slice(lastIndex));
  }

  return parts;
}

// ========================================
// バイナリ検出ヘルパー (25-10)
// ========================================

/**
 * bodyがバイナリデータかどうかを判定する
 * NULバイトや制御文字の割合で判定
 */
export function isBinaryBody(body: string): boolean {
  if (!body || body.length === 0) return false;
  const checkLen = Math.min(body.length, 8192);
  let controlCount = 0;
  for (let i = 0; i < checkLen; i++) {
    const code = body.charCodeAt(i);
    // NULバイト → ほぼ確実にバイナリ
    if (code === 0) return true;
    // 制御文字（タブ・改行・CRを除く）
    if (code < 32 && code !== 9 && code !== 10 && code !== 13) {
      controlCount++;
    }
  }
  // 制御文字が10%以上ならバイナリ
  return controlCount / checkLen > 0.1;
}

// ========================================
// プレーンテキスト レンダラー
// ========================================

function PlainRenderer({ body }: { body: string }) {
  return (
    <pre className="font-mono text-[13px] leading-relaxed whitespace-pre-wrap">
      {body}
    </pre>
  );
}

// ========================================
// セクション検出 (25-08)
// ========================================

/** セクション折りたたみ行コンポーネント */
function CollapsedSectionLine({
  section,
  onClick,
}: {
  section: Section;
  onClick: () => void;
}) {
  const lineCount = section.endLine - section.startLine + 1;
  return (
    <div
      onClick={onClick}
      onKeyDown={(e) => e.key === "Enter" && onClick()}
      className="flex items-center gap-2 px-2 py-1 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded text-sm font-mono text-neutral-600 dark:text-neutral-400"
    >
      <ChevronRight size={14} />
      <span className="font-semibold">{section.title}</span>
      <span className="text-xs text-neutral-400">({lineCount}行)</span>
    </div>
  );
}

type Section = {
  /** セクション開始行番号（0-indexed） */
  startLine: number;
  /** セクション終了行番号（0-indexed、次のセクション開始の1つ前） */
  endLine: number;
  /** セクション名（表示用） */
  title: string;
  /** ネストレベル（Markdownの見出しレベル等） */
  level?: number;
};

/**
 * フォーマット別にセクション構造を検出する
 */
function detectSections(body: string, format: BodyFormat): Section[] {
  const lines = body.split("\n");
  const sections: Section[] = [];

  switch (format) {
    case "abaqus_inp": {
      // Abaqus INP: `*`から始まる行（`**`コメントは除外）
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i].trimStart();
        if (line.startsWith("*") && !line.startsWith("**")) {
          sections.push({
            startLine: i,
            endLine: -1, // 後で埋める
            title: line.split(",")[0] || line, // カンマ前をタイトルに
          });
        }
      }
      break;
    }

    case "json": {
      // JSON: トップレベルのキー（インデント2スペースまたはタブ1つ）
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        // トップレベルキーのパターン: `  "key":` または `\t"key":`
        const match = line.match(/^(\s{2}|\t)"([^"]+)"\s*:/);
        if (match) {
          sections.push({
            startLine: i,
            endLine: -1,
            title: match[2],
          });
        }
      }
      break;
    }

    case "markdown": {
      // Markdown: 見出し行（`#`, `##`, `###`）
      for (let i = 0; i < lines.length; i++) {
        const line = lines[i];
        const match = line.match(/^(#{1,6})\s+(.+)/);
        if (match) {
          sections.push({
            startLine: i,
            endLine: -1,
            title: match[2],
            level: match[1].length,
          });
        }
      }
      break;
    }

    // YAML は BodyFormat に含まれていないため、一旦スキップ
    // 将来的に YAML フォーマットを追加する場合は以下のロジックを使用
    // case "yaml": {
    //   // YAML: トップレベルのキー（インデント0の行）
    //   for (let i = 0; i < lines.length; i++) {
    //     const line = lines[i];
    //     // トップレベルキーのパターン: `key:` （インデントなし、コメントではない）
    //     if (line.match(/^[a-zA-Z_][\w-]*:/) && !line.trimStart().startsWith("#")) {
    //       const key = line.split(":")[0];
    //       sections.push({
    //         startLine: i,
    //         endLine: -1,
    //         title: key,
    //       });
    //     }
    //   }
    //   break;
    // }

    default:
      // その他のフォーマットは階層畳み込み非対応
      return [];
  }

  // endLineを計算（次のセクション開始の1つ前、または最終行）
  for (let i = 0; i < sections.length; i++) {
    const nextStart = sections[i + 1]?.startLine ?? lines.length;
    sections[i].endLine = nextStart - 1;
  }

  return sections;
}

// ========================================
// バッチ表示セクションコンポーネント
// ========================================

/** セクション内のバッチ表示コンポーネント */
function BatchedSectionBody({
  body,
  format,
  attachedDocuments,
  batchSize,
}: {
  body: string;
  format: BodyFormat;
  attachedDocuments?: { relativePath: string; documentId: number }[];
  batchSize: number;
}) {
  const lines = body.split("\n");
  const totalLines = lines.length;
  const [visibleLines, setVisibleLines] = useState(
    Math.min(batchSize, totalLines),
  );

  const displayBody = lines.slice(0, visibleLines).join("\n");
  const hasMore = visibleLines < totalLines;

  const loadMore = () => {
    setVisibleLines((prev) => Math.min(prev + batchSize, totalLines));
  };

  return (
    <div>
      {renderFormatted(displayBody, format, attachedDocuments)}
      {hasMore && (
        <button
          type="button"
          onClick={loadMore}
          className="mt-1 flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 hover:underline"
        >
          <ChevronDown size={14} />
          さらに表示（残り {totalLines - visibleLines} 行）
        </button>
      )}
    </div>
  );
}

/** フォーマットに応じたレンダリング */
function renderFormatted(
  body: string,
  format: BodyFormat,
  attachedDocuments?: { relativePath: string; documentId: number }[],
): React.ReactNode {
  switch (format) {
    case "abaqus_inp":
      return <AbaqusInpRenderer body={body} />;
    case "csv":
      return <CsvRenderer body={body} />;
    case "json":
      return <JsonRenderer body={body} />;
    case "markdown":
      return (
        <MarkdownRenderer body={body} attachedDocuments={attachedDocuments} />
      );
    case "python":
      return <PythonRenderer body={body} />;
    default:
      return <PlainRenderer body={body} />;
  }
}

// ========================================
// メインコンポーネント
// ========================================

/** バッチ表示のデフォルト行数 */
const BATCH_SIZE = 50;

type BodyRendererProps = {
  entity: StringEntity;
  className?: string;
  /** 行数制限（プレビュー用） */
  maxLines?: number;
  /** 大容量bodyの折りたたみを有効にする (25-08) */
  collapsible?: boolean;
  /** バッチ表示の行数（デフォルト: 50） */
  collapseLines?: number;
};

export function BodyRenderer({
  entity,
  className = "",
  maxLines,
  collapsible = false,
  collapseLines = BATCH_SIZE,
}: BodyRendererProps) {
  // バッチ表示: 現在の表示行数
  const [visibleLineCount, setVisibleLineCount] = useState(collapseLines);
  // 25-08: 階層畳み込み用の状態（初期: すべて折りたたみ）
  const [collapsedSections, setCollapsedSections] =
    useState<Set<number> | null>(null);
  const [hierarchicalCollapseMode, setHierarchicalCollapseMode] =
    useState(true);

  const format = detectFormat(entity);
  const totalLines = entity.body.split("\n").length;

  // 25-08: セクション検出（初回のみ実行）
  const sections = useMemo(
    () => detectSections(entity.body, format),
    [entity.body, format],
  );

  // セクションがある場合は初期状態ですべて折りたたみ
  const effectiveCollapsedSections = useMemo(() => {
    if (collapsedSections !== null) return collapsedSections;
    // 初期値: すべてのセクションを折りたたみ
    if (sections.length > 0) {
      return new Set(sections.map((_, i) => i));
    }
    return new Set<number>();
  }, [collapsedSections, sections]);

  // 25-10: バイナリbody非表示
  if (isBinaryBody(entity.body)) {
    return (
      <div
        className={`flex items-center gap-2 text-sm text-neutral-400 ${className}`}
      >
        <FileWarning size={16} />
        <span>バイナリデータのため表示できません</span>
      </div>
    );
  }

  // 階層畳み込みのハンドラー
  const toggleSection = (sectionIndex: number) => {
    const prev = effectiveCollapsedSections;
    const next = new Set(prev);
    if (next.has(sectionIndex)) {
      next.delete(sectionIndex);
    } else {
      next.add(sectionIndex);
    }
    setCollapsedSections(next);
  };

  const toggleAllSections = () => {
    if (hierarchicalCollapseMode) {
      // すべて展開
      setCollapsedSections(new Set());
      setHierarchicalCollapseMode(false);
    } else {
      // すべて畳み込み
      setCollapsedSections(new Set(sections.map((_, i) => i)));
      setHierarchicalCollapseMode(true);
    }
  };

  let body = entity.body;

  // maxLines（プレビュー用の硬い上限）
  if (maxLines && maxLines > 0) {
    const lines = body.split("\n");
    if (lines.length > maxLines) {
      body = lines.slice(0, maxLines).join("\n");
    }
  }

  // バッチ表示: collapsible時かつセクションがない場合にバッチ制限を適用
  const useBatchDisplay =
    collapsible &&
    !maxLines &&
    totalLines > collapseLines &&
    sections.length === 0;
  if (useBatchDisplay) {
    const lines = body.split("\n");
    body = lines.slice(0, visibleLineCount).join("\n");
  }

  const hasMoreLines = useBatchDisplay && visibleLineCount < totalLines;

  const loadMore = () => {
    setVisibleLineCount((prev) => Math.min(prev + collapseLines, totalLines));
  };

  const collapseBack = () => {
    setVisibleLineCount(collapseLines);
  };

  const renderBody = () => {
    // 階層畳み込みが有効で、セクションが存在する場合
    if (sections.length > 0) {
      return renderBodyWithSections();
    }

    // 通常のレンダリング
    return renderFormatted(body, format, entity.attachedDocuments);
  };

  const renderBodyWithSections = () => {
    const allLines = entity.body.split("\n");
    const elements: React.ReactNode[] = [];

    // バッチ表示: セクション単位での行数カウント
    let renderedLineCount = 0;
    const lineLimit =
      collapsible && !maxLines ? visibleLineCount : Number.MAX_SAFE_INTEGER;

    for (let i = 0; i < sections.length; i++) {
      if (renderedLineCount >= lineLimit) break;

      const section = sections[i];
      const isCollapsed = effectiveCollapsedSections.has(i);

      if (isCollapsed) {
        // 折りたたまれている場合は1行としてカウント
        renderedLineCount += 1;
        elements.push(
          <CollapsedSectionLine
            key={`section-${i}`}
            section={section}
            onClick={() => toggleSection(i)}
          />,
        );
      } else {
        const sectionLineCount = section.endLine - section.startLine + 1;
        const sectionBody = allLines
          .slice(section.startLine, section.endLine + 1)
          .join("\n");

        // セクションヘッダー（クリックで折りたたみ）
        elements.push(
          <div
            key={`section-header-${i}`}
            onClick={() => toggleSection(i)}
            onKeyDown={(e) => e.key === "Enter" && toggleSection(i)}
            className="flex items-center gap-2 px-2 py-1 cursor-pointer hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded text-sm font-mono font-semibold text-neutral-700 dark:text-neutral-300 border-l-2 border-sky-500 dark:border-sky-600 mb-1"
          >
            <ChevronDown size={14} />
            <span>{section.title}</span>
            <span className="text-xs text-neutral-400 font-normal">
              ({sectionLineCount}行)
            </span>
          </div>,
        );

        // セクション本体: バッチ表示を使用（大きいセクションのパフォーマンス対策）
        elements.push(
          <div key={`section-body-${i}`} className="ml-4">
            {sectionLineCount > collapseLines ? (
              <BatchedSectionBody
                body={sectionBody}
                format={format}
                attachedDocuments={entity.attachedDocuments}
                batchSize={collapseLines}
              />
            ) : (
              renderFormatted(sectionBody, format, entity.attachedDocuments)
            )}
          </div>,
        );

        renderedLineCount += sectionLineCount;
      }
    }

    // セクション表示後にまだ表示枠が残っている場合のロードモアボタン
    const totalSections = sections.length;
    const renderedSections = elements.filter((_, idx) => idx % 2 === 0).length; // 概算
    if (
      collapsible &&
      renderedSections < totalSections &&
      renderedLineCount >= lineLimit
    ) {
      elements.push(
        <button
          key="load-more-sections"
          type="button"
          onClick={() => setVisibleLineCount((prev) => prev + collapseLines)}
          className="mt-1 flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 hover:underline"
        >
          <ChevronDown size={14} />
          さらにセクションを表示
        </button>,
      );
    }

    return <div className="space-y-1">{elements}</div>;
  };

  return (
    <div className={className}>
      {/* 25-08: 階層トグルボタン（セクションがある場合のみ表示） */}
      {sections.length > 0 && (
        <div className="flex justify-end mb-2">
          <button
            type="button"
            onClick={toggleAllSections}
            className="flex items-center gap-1 px-2 py-1 text-xs text-neutral-600 dark:text-neutral-400 hover:bg-neutral-100 dark:hover:bg-neutral-800 rounded border border-neutral-300 dark:border-neutral-600"
            title={hierarchicalCollapseMode ? "すべて展開" : "すべて折りたたむ"}
          >
            <UnfoldVertical size={14} />
            <span>
              {hierarchicalCollapseMode ? "すべて展開" : "すべて折りたたむ"}
            </span>
          </button>
        </div>
      )}

      {renderBody()}

      {maxLines && totalLines > maxLines && (
        <div className="mt-1 text-xs text-neutral-400">...</div>
      )}
      {/* バッチ表示: さらに読み込み / 折りたたむ */}
      {useBatchDisplay && (
        <div className="mt-2 flex items-center gap-3">
          {hasMoreLines && (
            <button
              type="button"
              onClick={loadMore}
              className="flex items-center gap-1 text-xs text-sky-600 dark:text-sky-400 hover:underline"
            >
              <ChevronDown size={14} />
              さらに {Math.min(collapseLines, totalLines - visibleLineCount)}{" "}
              行を表示（残り {totalLines - visibleLineCount} 行）
            </button>
          )}
          {visibleLineCount > collapseLines && (
            <button
              type="button"
              onClick={collapseBack}
              className="flex items-center gap-1 text-xs text-neutral-500 hover:underline"
            >
              <ChevronUp size={14} />
              {collapseLines}行に戻す
            </button>
          )}
        </div>
      )}
    </div>
  );
}

/** フォーマットのラベルを取得 */
export function formatLabel(format: BodyFormat): string {
  switch (format) {
    case "abaqus_inp":
      return "Abaqus INP";
    case "csv":
      return "CSV";
    case "json":
      return "JSON";
    case "markdown":
      return "Markdown";
    case "python":
      return "Python";
    case "plain":
      return "テキスト";
  }
}
