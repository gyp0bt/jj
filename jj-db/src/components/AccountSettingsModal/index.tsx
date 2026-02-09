"use client";

import { Check, Key, Save, User, X } from "lucide-react";
import { useState } from "react";
import { UserIcon } from "@/components/UserIcon";
import { useAuth } from "@/contexts/AuthContext";
import { changePassword, updateProfile } from "@/lib/user-api";

type AccountSettingsModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

const AVATAR_OPTIONS = [
  null,
  "red",
  "orange",
  "amber",
  "yellow",
  "lime",
  "green",
  "emerald",
  "teal",
  "cyan",
  "sky",
  "blue",
  "indigo",
  "violet",
  "purple",
  "fuchsia",
  "pink",
  "rose",
];

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

export function AccountSettingsModal({
  isOpen,
  onClose,
}: AccountSettingsModalProps) {
  const { user, refreshUser } = useAuth();
  const [displayName, setDisplayName] = useState(user?.displayName ?? "");
  const [selectedAvatar, setSelectedAvatar] = useState<string | null>(
    user?.avatar ?? null,
  );
  const [currentPassword, setCurrentPassword] = useState("");
  const [newPassword, setNewPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<"profile" | "password">("profile");

  if (!isOpen || !user) return null;

  const handleSaveProfile = async () => {
    setError(null);
    setSuccess(null);
    setSaving(true);

    const updates: { displayName?: string; avatar?: string | null } = {};
    if (displayName.trim() !== user.displayName) {
      updates.displayName = displayName.trim();
    }
    if (selectedAvatar !== user.avatar) {
      updates.avatar = selectedAvatar;
    }

    if (Object.keys(updates).length === 0) {
      setSuccess("変更はありません");
      setSaving(false);
      return;
    }

    const res = await updateProfile(updates);
    setSaving(false);

    if (res.error) {
      setError(res.error);
      return;
    }

    setSuccess("プロフィールを更新しました");
    refreshUser();
  };

  const handleChangePassword = async () => {
    setError(null);
    setSuccess(null);

    if (!currentPassword) {
      setError("現在のパスワードを入力してください");
      return;
    }
    if (!newPassword) {
      setError("新しいパスワードを入力してください");
      return;
    }
    if (newPassword.length < 4) {
      setError("パスワードは4文字以上で入力してください");
      return;
    }
    if (newPassword !== confirmPassword) {
      setError("新しいパスワードが一致しません");
      return;
    }

    setSaving(true);
    const res = await changePassword(currentPassword, newPassword);
    setSaving(false);

    if (res.error) {
      setError(res.error);
      return;
    }

    setSuccess("パスワードを変更しました");
    setCurrentPassword("");
    setNewPassword("");
    setConfirmPassword("");
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-md overflow-hidden">
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100">
            アカウント設定
          </h2>
          <button
            type="button"
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800 transition-colors"
            aria-label="閉じる"
          >
            <X size={20} className="text-neutral-500" />
          </button>
        </div>

        <div className="flex border-b border-neutral-200 dark:border-neutral-700">
          <button
            type="button"
            onClick={() => setActiveTab("profile")}
            className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 ${
              activeTab === "profile"
                ? "text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400"
                : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            }`}
          >
            <User size={16} />
            プロフィール
          </button>
          <button
            type="button"
            onClick={() => setActiveTab("password")}
            className={`flex-1 px-4 py-3 text-sm font-medium flex items-center justify-center gap-2 ${
              activeTab === "password"
                ? "text-blue-600 dark:text-blue-400 border-b-2 border-blue-600 dark:border-blue-400"
                : "text-neutral-500 hover:text-neutral-700 dark:hover:text-neutral-300"
            }`}
          >
            <Key size={16} />
            パスワード
          </button>
        </div>

        <div className="p-5">
          {error && (
            <div className="mb-4 p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="mb-4 p-3 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
              <Check size={16} />
              {success}
            </div>
          )}

          {activeTab === "profile" && (
            <div className="space-y-5">
              <div className="flex justify-center">
                <UserIcon
                  displayName={displayName || user.displayName}
                  avatar={selectedAvatar}
                  size="xl"
                  showTooltip={false}
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2">
                  アイコンの色
                </label>
                <div className="grid grid-cols-6 gap-2">
                  {AVATAR_OPTIONS.map((color) => (
                    <button
                      key={color ?? "default"}
                      type="button"
                      onClick={() => setSelectedAvatar(color)}
                      className={`w-10 h-10 rounded-full flex items-center justify-center transition-all ${
                        color
                          ? AVATAR_COLORS[color]
                          : "bg-neutral-300 dark:bg-neutral-600"
                      } ${
                        selectedAvatar === color
                          ? "ring-2 ring-offset-2 ring-blue-500 dark:ring-offset-neutral-900"
                          : "hover:scale-110"
                      }`}
                      title={color ?? "デフォルト"}
                    >
                      {selectedAvatar === color && (
                        <Check size={16} className="text-white" />
                      )}
                    </button>
                  ))}
                </div>
              </div>

              <div>
                <label
                  htmlFor="displayName"
                  className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
                >
                  表示名
                </label>
                <input
                  id="displayName"
                  type="text"
                  value={displayName}
                  onChange={(e) => setDisplayName(e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="表示名を入力"
                />
              </div>

              <button
                type="button"
                onClick={handleSaveProfile}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2.5 text-sm font-medium transition-colors"
              >
                <Save size={16} />
                {saving ? "保存中..." : "保存"}
              </button>
            </div>
          )}

          {activeTab === "password" && (
            <div className="space-y-4">
              <div>
                <label
                  htmlFor="currentPassword"
                  className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
                >
                  現在のパスワード
                </label>
                <input
                  id="currentPassword"
                  type="password"
                  value={currentPassword}
                  onChange={(e) => setCurrentPassword(e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="現在のパスワード"
                />
              </div>

              <div>
                <label
                  htmlFor="newPassword"
                  className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
                >
                  新しいパスワード
                </label>
                <input
                  id="newPassword"
                  type="password"
                  value={newPassword}
                  onChange={(e) => setNewPassword(e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="4文字以上"
                />
              </div>

              <div>
                <label
                  htmlFor="confirmPassword"
                  className="block text-sm font-medium text-neutral-700 dark:text-neutral-300 mb-2"
                >
                  新しいパスワード（確認）
                </label>
                <input
                  id="confirmPassword"
                  type="password"
                  value={confirmPassword}
                  onChange={(e) => setConfirmPassword(e.target.value)}
                  className="w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  placeholder="もう一度入力"
                />
              </div>

              <button
                type="button"
                onClick={handleChangePassword}
                disabled={saving}
                className="w-full flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2.5 text-sm font-medium transition-colors"
              >
                <Key size={16} />
                {saving ? "変更中..." : "パスワードを変更"}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
