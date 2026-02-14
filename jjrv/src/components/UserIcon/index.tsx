"use client";

import { User } from "lucide-react";

export type UserIconSize = "xs" | "sm" | "md" | "lg" | "xl";

type UserIconProps = {
  displayName?: string | null;
  avatar?: string | null;
  size?: UserIconSize;
  className?: string;
  showTooltip?: boolean;
};

const SIZE_CLASSES: Record<UserIconSize, string> = {
  xs: "w-5 h-5 text-[10px]",
  sm: "w-7 h-7 text-xs",
  md: "w-10 h-10 text-sm",
  lg: "w-14 h-14 text-lg",
  xl: "w-20 h-20 text-2xl",
};

const ICON_SIZES: Record<UserIconSize, number> = {
  xs: 10,
  sm: 12,
  md: 16,
  lg: 24,
  xl: 32,
};

const AVATAR_COLORS: Record<string, string> = {
  red: "bg-red-500",
  orange: "bg-orange-500",
  amber: "bg-amber-500",
  yellow: "bg-yellow-500",
  lime: "bg-lime-500",
  green: "bg-green-500",
  emerald: "bg-emerald-500",
  teal: "bg-teal-500",
  cyan: "bg-cyan-500",
  sky: "bg-sky-500",
  blue: "bg-blue-500",
  indigo: "bg-indigo-500",
  violet: "bg-violet-500",
  purple: "bg-purple-500",
  fuchsia: "bg-fuchsia-500",
  pink: "bg-pink-500",
  rose: "bg-rose-500",
};

export function UserIcon({
  displayName,
  avatar,
  size = "md",
  className = "",
  showTooltip = true,
}: UserIconProps) {
  const sizeClass = SIZE_CLASSES[size];
  const iconSize = ICON_SIZES[size];

  if (!displayName) {
    return (
      <span
        className={`inline-flex items-center justify-center rounded-full bg-neutral-200 text-neutral-500 dark:bg-neutral-700 dark:text-neutral-400 ${sizeClass} ${className}`}
        title={showTooltip ? "未ログイン" : undefined}
      >
        <User size={iconSize} />
      </span>
    );
  }

  const initial = displayName.charAt(0).toUpperCase();
  const bgColor =
    avatar && AVATAR_COLORS[avatar]
      ? AVATAR_COLORS[avatar]
      : "bg-neutral-700 dark:bg-neutral-600";

  return (
    <span
      className={`inline-flex items-center justify-center rounded-full ${bgColor} text-white font-medium ${sizeClass} ${className}`}
      title={showTooltip ? displayName : undefined}
    >
      {initial}
    </span>
  );
}

// 複数ユーザーの場合のアイコングループ
type UserIconGroupProps = {
  users: Array<{ id?: string; displayName: string }>;
  maxDisplay?: number;
  size?: UserIconSize;
  className?: string;
};

export function UserIconGroup({
  users,
  maxDisplay = 3,
  size = "xs",
  className = "",
}: UserIconGroupProps) {
  const displayUsers = users.slice(0, maxDisplay);
  const remainingCount = users.length - maxDisplay;

  return (
    <span className={`inline-flex items-center -space-x-1 ${className}`}>
      {displayUsers.map((user) => (
        <UserIcon
          key={user.id ?? user.displayName}
          displayName={user.displayName}
          size={size}
          className="ring-2 ring-white dark:ring-neutral-900"
        />
      ))}
      {remainingCount > 0 && (
        <span
          className={`inline-flex items-center justify-center rounded-full bg-neutral-300 text-neutral-700 dark:bg-neutral-600 dark:text-neutral-300 font-medium ring-2 ring-white dark:ring-neutral-900 ${SIZE_CLASSES[size]}`}
          title={`他 ${remainingCount} 人`}
        >
          +{remainingCount}
        </span>
      )}
    </span>
  );
}
