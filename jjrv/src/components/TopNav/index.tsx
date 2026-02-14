"use client";

import { ChevronRight, Home } from "lucide-react";
import Link from "next/link";
import { AccountStatus } from "@/components/AccountStatus";

export type TopNavItem = {
  label: string;
  href: string;
};

type TopNavProps = {
  items: TopNavItem[];
  title?: string;
  onHomeClick?: () => void;
  showAccountStatus?: boolean;
  className?: string;
};

export function TopNav({
  items,
  title,
  onHomeClick,
  showAccountStatus = true,
  className = "",
}: TopNavProps) {
  return (
    <div className={`flex flex-col gap-2 ${className}`}>
      <div className="flex flex-wrap items-center gap-3">
        <div className="flex flex-wrap items-center gap-2 text-sm text-neutral-500">
          {onHomeClick ? (
            <button
              type="button"
              onClick={onHomeClick}
              aria-label="ホームへ戻る"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <Home size={16} />
            </button>
          ) : (
            <Link
              href="/"
              aria-label="ホームへ戻る"
              className="inline-flex items-center gap-1 rounded-md px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <Home size={16} />
            </Link>
          )}
          {items.map((item) => (
            <span
              key={`${item.href}-${item.label}`}
              className="inline-flex items-center gap-2"
            >
              <ChevronRight size={14} />
              <Link
                href={item.href}
                className="rounded-md px-2 py-1 hover:bg-neutral-100 dark:hover:bg-neutral-800"
              >
                {item.label}
              </Link>
            </span>
          ))}
        </div>
        <div className="ml-auto">{showAccountStatus && <AccountStatus />}</div>
      </div>
      {title && <h1 className="text-xl sm:text-2xl font-semibold">{title}</h1>}
    </div>
  );
}
