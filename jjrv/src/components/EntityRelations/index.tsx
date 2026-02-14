"use client";

import { Link2, Tag } from "lucide-react";

export type RelationItem = {
  id: string;
  type: "tag" | "related";
  label: string;
  href?: string;
  meta?: string;
};

type EntityRelationsProps = {
  relations: RelationItem[];
  className?: string;
};

export function EntityRelations({
  relations,
  className = "",
}: EntityRelationsProps) {
  if (relations.length === 0) {
    return (
      <div className={`text-sm text-neutral-500 ${className}`}>
        関連情報がありません
      </div>
    );
  }

  return (
    <div
      className={`rounded-xl border border-neutral-200 dark:border-neutral-800 bg-white/80 dark:bg-neutral-900/60 p-4 ${className}`}
    >
      <div className="space-y-2">
        {relations.map((item) => (
          <div key={item.id} className="flex items-center gap-2 text-sm">
            {item.type === "tag" ? (
              <Tag size={14} className="text-amber-500" />
            ) : (
              <Link2 size={14} className="text-sky-500" />
            )}
            {item.href ? (
              <a
                href={item.href}
                className="text-neutral-700 dark:text-neutral-200 hover:underline"
              >
                {item.label}
              </a>
            ) : (
              <span className="text-neutral-700 dark:text-neutral-200">
                {item.label}
              </span>
            )}
            {item.meta && (
              <span className="text-xs text-neutral-400">{item.meta}</span>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}
