"use client";

import { Database, LogIn, Settings } from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { AccountSettingsModal } from "@/components/AccountSettingsModal";
import { DataSourceSettingsModal } from "@/components/DataSourceSettingsModal";
import { UserIcon } from "@/components/UserIcon";
import { useAuth } from "@/contexts/AuthContext";

export function AccountStatus() {
  const { user, logout } = useAuth();
  const [isOpen, setIsOpen] = useState(false);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const [dataSourceOpen, setDataSourceOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener("mousedown", handleClickOutside);
    }
    return () => {
      document.removeEventListener("mousedown", handleClickOutside);
    };
  }, [isOpen]);

  if (!user) {
    return (
      <Link
        href="/login"
        className="w-10 h-10 rounded-full bg-neutral-200 text-neutral-600 dark:bg-neutral-800 dark:text-neutral-300 font-medium flex items-center justify-center transition-colors hover:bg-neutral-300 dark:hover:bg-neutral-700"
        aria-label="ログイン"
        title="ログイン"
      >
        <LogIn size={16} />
      </Link>
    );
  }

  return (
    <div ref={menuRef} className="relative">
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className="rounded-full transition-colors focus:outline-none focus:ring-2 focus:ring-neutral-500 focus:ring-offset-2 focus:ring-offset-neutral-900 hover:opacity-80"
        aria-label="アカウントメニュー"
      >
        <UserIcon
          displayName={user.displayName}
          avatar={user.avatar}
          size="md"
          showTooltip={false}
        />
      </button>

      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-neutral-800 border border-neutral-700 rounded-lg shadow-lg py-2 z-50">
          <div className="px-4 py-3 border-b border-neutral-700">
            <p className="text-sm font-medium text-neutral-100">
              {user.displayName}
            </p>
            <p className="text-xs text-neutral-400">@{user.username}</p>
            {user.role === "admin" && (
              <span className="inline-block mt-1 text-xs bg-blue-900 text-blue-200 px-2 py-0.5 rounded">
                管理者
              </span>
            )}
          </div>
          <button
            type="button"
            onClick={() => {
              setSettingsOpen(true);
              setIsOpen(false);
            }}
            className="w-full px-4 py-2 text-left text-sm text-neutral-300 hover:bg-neutral-700 hover:text-neutral-100 transition-colors flex items-center gap-2"
          >
            <Settings size={14} />
            アカウント設定
          </button>
          {user.role === "admin" && (
            <button
              type="button"
              onClick={() => {
                setDataSourceOpen(true);
                setIsOpen(false);
              }}
              className="w-full px-4 py-2 text-left text-sm text-neutral-300 hover:bg-neutral-700 hover:text-neutral-100 transition-colors flex items-center gap-2"
            >
              <Database size={14} />
              データソース設定
            </button>
          )}
          <button
            type="button"
            onClick={() => {
              logout();
              setIsOpen(false);
            }}
            className="w-full px-4 py-2 text-left text-sm text-neutral-300 hover:bg-neutral-700 hover:text-neutral-100 transition-colors"
          >
            ログアウト
          </button>
        </div>
      )}

      <AccountSettingsModal
        isOpen={settingsOpen}
        onClose={() => setSettingsOpen(false)}
      />
      <DataSourceSettingsModal
        isOpen={dataSourceOpen}
        onClose={() => setDataSourceOpen(false)}
      />
    </div>
  );
}
