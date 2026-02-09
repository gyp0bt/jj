import JSZip from "jszip";
import { detectFormat } from "@/components/BodyRenderer";
import type { StringEntity } from "@/lib/types";

/** フォーマットからファイル拡張子を取得 */
export function getExtension(entity: StringEntity): string {
  const ext = entity.sysProps?.extension;
  if (ext) return ext;

  const format = detectFormat(entity);
  switch (format) {
    case "abaqus_inp":
      return "inp";
    case "csv":
      return "csv";
    case "json":
      return "json";
    case "markdown":
      return "md";
    default:
      return "txt";
  }
}

/** 単体エンティティをフォーマット対応拡張子でダウンロード */
export function downloadEntity(entity: StringEntity): void {
  const ext = getExtension(entity);
  const baseName = entity.name || entity.id;
  // 名前に既に拡張子が含まれている場合はそのまま使う
  const hasExt =
    baseName.includes(".") && baseName.split(".").pop()?.toLowerCase() === ext;
  const filename = hasExt ? baseName : `${baseName}.${ext}`;
  const blob = new Blob([entity.body], { type: "text/plain" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}

/** 複数エンティティをZIPでダウンロード */
export async function downloadEntitiesAsZip(
  entities: StringEntity[],
  zipName = "entities.zip",
): Promise<void> {
  const zip = new JSZip();
  const nameCount = new Map<string, number>();

  for (const entity of entities) {
    const ext = getExtension(entity);
    const baseName = entity.name || entity.id;
    // 名前に既に拡張子が含まれている場合はそのまま使う
    const hasExt =
      baseName.includes(".") &&
      baseName.split(".").pop()?.toLowerCase() === ext;
    const key = hasExt ? baseName : `${baseName}.${ext}`;
    const count = nameCount.get(key) ?? 0;
    nameCount.set(key, count + 1);
    const suffix = count > 0 ? `_${count}` : "";
    const nameWithoutExt = hasExt ? baseName.replace(/\.[^.]+$/, "") : baseName;
    const filename = `${nameWithoutExt}${suffix}.${ext}`;
    zip.file(filename, entity.body);
  }

  const blob = await zip.generateAsync({ type: "blob" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = zipName;
  a.click();
  URL.revokeObjectURL(url);
}
