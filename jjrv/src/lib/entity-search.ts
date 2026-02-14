import type { StringEntity } from "./types";

export type EntitySearchOptions = {
  nameQuery?: string;
  tags?: string[];
  propertyKey?: string;
  propertyValue?: number | null;
  domain?: string | null;
  sortBy?: "created" | "updated" | "name";
  sortOrder?: "asc" | "desc";
};

export function searchEntities(
  entities: StringEntity[],
  options: EntitySearchOptions,
): StringEntity[] {
  const {
    nameQuery = "",
    tags = [],
    propertyKey = "",
    propertyValue = null,
    domain = null,
    sortBy = "updated",
    sortOrder = "desc",
  } = options;
  const nameKw = nameQuery.trim().toLowerCase();
  const tagSet = new Set(tags.map((t) => t.toLowerCase()));
  const propKey = propertyKey.trim().toLowerCase();
  const hasPropFilter = propKey.length > 0 && propertyValue !== null;
  const domainKw = domain ? domain.trim().toLowerCase() : "";

  const filtered = entities.filter((e) => {
    const hitName = nameKw ? e.name.toLowerCase().includes(nameKw) : true;
    const hitTags = tagSet.size
      ? Array.from(tagSet).every((t) =>
          [...e.userTags, ...e.sysTags].some((x) => x.toLowerCase() === t),
        )
      : true;
    const hitDomain = domainKw
      ? e.domain?.toLowerCase().includes(domainKw)
      : true;
    const hitProp = hasPropFilter
      ? [e.userProps, e.sysProps].some((props) =>
          Object.entries(props).some(([key, raw]) => {
            if (key.toLowerCase() !== propKey) return false;
            const numeric = Number(raw);
            return Number.isFinite(numeric) && numeric === propertyValue;
          }),
        )
      : true;
    return hitName && hitTags && hitDomain && hitProp;
  });

  // 並び替え（レポジトリ→フォルダ→ファイルの順に表示）
  filtered.sort((a, b) => {
    // レポジトリ→フォルダ→ファイルの優先順位
    const priority = (e: StringEntity) => {
      if (e.sysTags.includes("repository")) return 0;
      if (e.sysTags.includes("directory")) return 1;
      return 2;
    };
    const aPri = priority(a);
    const bPri = priority(b);
    if (aPri !== bPri) return aPri - bPri;

    let comparison = 0;
    switch (sortBy) {
      case "created":
        comparison =
          new Date(a.createdAt).getTime() - new Date(b.createdAt).getTime();
        break;
      case "updated":
        comparison =
          new Date(a.updatedAt).getTime() - new Date(b.updatedAt).getTime();
        break;
      case "name":
        comparison = a.name.localeCompare(b.name, "ja");
        break;
    }
    return sortOrder === "asc" ? comparison : -comparison;
  });

  return filtered;
}
