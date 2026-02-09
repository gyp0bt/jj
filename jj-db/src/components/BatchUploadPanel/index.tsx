"use client";

import { Folder, Loader2, Upload } from "lucide-react";
import { useMemo, useState } from "react";

export type ParsedMaterial = {
  name: string;
  sourcePath: string;
  block: string;
};

export type ParsedMaterialResult = {
  materials: ParsedMaterial[];
  skippedFiles: string[];
  errors: string[];
};

type BatchUploadPanelProps = {
  files: File[];
  onFilesChange: (files: File[]) => void;
  onParse: (result: ParsedMaterialResult) => void;
  className?: string;
};

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

function parseMaterialName(line: string, fallback: string) {
  const match = line.match(/name\s*=\s*([^,]+)/i);
  if (match?.[1]) return match[1].trim();
  return fallback;
}

function extractMaterialsFromText(text: string, sourcePath: string) {
  const lines = text.split(/\r?\n/);
  const materials: ParsedMaterial[] = [];
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
          materials.push({
            name: currentName,
            sourcePath,
            block: currentLines.join("\n").trimEnd(),
          });
        }
        count += 1;
        currentName = parseMaterialName(trimmed, `material-${count}`);
        currentLines = [line];
        continue;
      }

      if (currentLines.length > 0) {
        if (MATERIAL_SET.has(normalized)) {
          currentLines.push(line);
        } else {
          materials.push({
            name: currentName,
            sourcePath,
            block: currentLines.join("\n").trimEnd(),
          });
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
    materials.push({
      name: currentName,
      sourcePath,
      block: currentLines.join("\n").trimEnd(),
    });
  }

  return materials;
}

export function BatchUploadPanel({
  files,
  onFilesChange,
  onParse,
  className = "",
}: BatchUploadPanelProps) {
  const [parsing, setParsing] = useState(false);
  const [lastResult, setLastResult] = useState<ParsedMaterialResult | null>(
    null,
  );

  const inpFiles = useMemo(
    () => files.filter((file) => file.name.toLowerCase().endsWith(".inp")),
    [files],
  );

  const handleFiles = (fileList: FileList | null) => {
    if (!fileList) return;
    onFilesChange(Array.from(fileList));
  };

  const handleParse = async () => {
    if (parsing) return;
    setParsing(true);
    const result: ParsedMaterialResult = {
      materials: [],
      skippedFiles: [],
      errors: [],
    };

    for (const file of files) {
      if (!file.name.toLowerCase().endsWith(".inp")) {
        result.skippedFiles.push(file.name);
        continue;
      }
      try {
        const text = await file.text();
        const sourcePath =
          "webkitRelativePath" in file && file.webkitRelativePath
            ? file.webkitRelativePath
            : file.name;
        const materials = extractMaterialsFromText(text, sourcePath);
        if (materials.length === 0) {
          result.skippedFiles.push(sourcePath);
        } else {
          result.materials.push(...materials);
        }
      } catch (error) {
        result.errors.push(`${file.name}: ${String(error)}`);
      }
    }

    setLastResult(result);
    setParsing(false);
    onParse(result);
  };

  return (
    <div
      className={`rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/60 p-4 ${className}`}
    >
      <div className="flex flex-wrap items-center gap-3">
        <div className="inline-flex items-center gap-2 text-sm font-semibold text-neutral-600 dark:text-neutral-300">
          <Upload size={16} />
          一括アップロード
        </div>
        <label className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-2 text-sm cursor-pointer hover:bg-neutral-50 dark:hover:bg-neutral-800">
          <Folder size={16} />
          フォルダ/ファイル選択
          <input
            type="file"
            multiple
            // @ts-expect-error webkitdirectory is supported in Chromium based browsers.
            webkitdirectory="true"
            className="hidden"
            onChange={(e) => handleFiles(e.target.files)}
          />
        </label>
        <button
          type="button"
          onClick={handleParse}
          disabled={parsing || files.length === 0}
          className="inline-flex items-center gap-2 rounded-lg border border-neutral-200 dark:border-neutral-700 px-3 py-2 text-sm hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-40"
        >
          {parsing ? <Loader2 size={16} className="animate-spin" /> : null}
          material 抽出
        </button>
      </div>

      <div className="mt-3 text-xs text-neutral-500">
        選択ファイル: {files.length} / .inp: {inpFiles.length}
      </div>

      {lastResult && (
        <div className="mt-3 text-xs text-neutral-500 space-y-1">
          <div>抽出: {lastResult.materials.length} 件</div>
          {lastResult.skippedFiles.length > 0 && (
            <div>スキップ: {lastResult.skippedFiles.length} 件</div>
          )}
          {lastResult.errors.length > 0 && (
            <div className="text-rose-500">
              エラー: {lastResult.errors.length} 件
            </div>
          )}
        </div>
      )}
    </div>
  );
}
