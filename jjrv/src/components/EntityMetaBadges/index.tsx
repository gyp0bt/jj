"use client";

import { Briefcase, Download, Star, User } from "lucide-react";
import Image from "next/image";

export type MetaUser = {
  name: string;
  avatarUrl?: string;
};

export type MetaProject = {
  label: string;
  href?: string;
};

export type EntityMeta = {
  owner: MetaUser;
  favorites?: number;
  downloads?: number;
  favoriteUsers?: MetaUser[];
  usedBy?: MetaProject[];
};

type EntityMetaBadgesProps = {
  owner: MetaUser;
  favorites?: number;
  downloads?: number;
  favoriteUsers?: MetaUser[];
  usedBy?: MetaProject[];
  className?: string;
};

const initials = (name: string) => name.slice(0, 1).toUpperCase();

export function EntityMetaBadges({
  owner,
  favorites = 0,
  downloads = 0,
  favoriteUsers = [],
  usedBy = [],
  className = "",
}: EntityMetaBadgesProps) {
  const visibleFavorites = favoriteUsers.slice(0, 5);
  const extraFavorites = Math.max(
    0,
    favoriteUsers.length - visibleFavorites.length,
  );

  return (
    <div
      className={`flex flex-wrap items-center gap-3 text-xs text-neutral-500 ${className}`}
    >
      <div className="inline-flex items-center gap-2">
        <span className="inline-flex items-center justify-center h-6 w-6 rounded-full bg-neutral-100 dark:bg-neutral-800">
          {owner.avatarUrl ? (
            <Image
              src={owner.avatarUrl}
              alt={owner.name}
              width={24}
              height={24}
              unoptimized
              className="h-6 w-6 rounded-full object-cover"
            />
          ) : (
            <span className="text-[11px] font-semibold text-neutral-600 dark:text-neutral-300">
              {initials(owner.name)}
            </span>
          )}
        </span>
        <span className="inline-flex items-center gap-1">
          <User size={12} /> {owner.name}
        </span>
      </div>

      <div className="inline-flex items-center gap-1">
        <Star size={12} className="text-amber-500" /> {favorites}
      </div>
      <div className="inline-flex items-center gap-1">
        <Download size={12} /> {downloads}
      </div>

      {favoriteUsers.length > 0 && (
        <div className="inline-flex items-center gap-1">
          {visibleFavorites.map((user) => (
            <span
              key={user.name}
              title={user.name}
              className="inline-flex items-center justify-center h-5 w-5 rounded-full bg-neutral-100 dark:bg-neutral-800"
            >
              {user.avatarUrl ? (
                <Image
                  src={user.avatarUrl}
                  alt={user.name}
                  width={20}
                  height={20}
                  unoptimized
                  className="h-5 w-5 rounded-full object-cover"
                />
              ) : (
                <span className="text-[10px] font-semibold text-neutral-600 dark:text-neutral-300">
                  {initials(user.name)}
                </span>
              )}
            </span>
          ))}
          {extraFavorites > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-neutral-100 dark:bg-neutral-800">
              +{extraFavorites}
            </span>
          )}
        </div>
      )}

      {usedBy.length > 0 && (
        <div className="inline-flex items-center gap-2">
          <Briefcase size={12} />
          <div className="flex flex-wrap items-center gap-1">
            {usedBy.map((item) =>
              item.href ? (
                <a
                  key={`${item.label}-${item.href}`}
                  href={item.href}
                  className="rounded-full border border-neutral-200 dark:border-neutral-700 px-2 py-0.5 text-[11px] hover:bg-neutral-50 dark:hover:bg-neutral-800"
                >
                  {item.label}
                </a>
              ) : (
                <span
                  key={item.label}
                  className="rounded-full border border-neutral-200 dark:border-neutral-700 px-2 py-0.5 text-[11px]"
                >
                  {item.label}
                </span>
              ),
            )}
          </div>
        </div>
      )}
    </div>
  );
}
