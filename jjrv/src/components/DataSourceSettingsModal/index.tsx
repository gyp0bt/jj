"use client";

import { Check, Database, Loader2, Network, Save, X, Zap } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import {
  type DataSourceStatus,
  getDataSourceStatus,
  switchDataSource,
  testNeo4jConnection,
} from "@/lib/datasource-api";

type DataSourceSettingsModalProps = {
  isOpen: boolean;
  onClose: () => void;
};

export function DataSourceSettingsModal({
  isOpen,
  onClose,
}: DataSourceSettingsModalProps) {
  const [status, setStatus] = useState<DataSourceStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<string | null>(null);

  // Neo4j接続フォーム
  const [neo4jUri, setNeo4jUri] = useState("bolt://localhost:7687");
  const [neo4jUser, setNeo4jUser] = useState("neo4j");
  const [neo4jPassword, setNeo4jPassword] = useState("");

  // テスト状態
  const [testing, setTesting] = useState(false);
  const [testResult, setTestResult] = useState<{
    ok: boolean;
    serverInfo?: string;
    error?: string;
  } | null>(null);

  // 切替状態
  const [switching, setSwitching] = useState(false);

  const fetchStatus = useCallback(async () => {
    setLoading(true);
    const res = await getDataSourceStatus();
    if (res.data) {
      setStatus(res.data);
      setNeo4jUri(res.data.neo4j.uri);
      setNeo4jUser(res.data.neo4j.user);
    } else if (res.error) {
      setError(res.error);
    }
    setLoading(false);
  }, []);

  useEffect(() => {
    if (isOpen) {
      fetchStatus();
      setError(null);
      setSuccess(null);
      setTestResult(null);
    }
  }, [isOpen, fetchStatus]);

  if (!isOpen) return null;

  const handleTest = async () => {
    setTesting(true);
    setTestResult(null);
    setError(null);
    setSuccess(null);

    const res = await testNeo4jConnection({
      uri: neo4jUri,
      user: neo4jUser,
      password: neo4jPassword,
    });

    setTesting(false);
    if (res.data) {
      setTestResult(res.data);
    } else {
      setTestResult({ ok: false, error: res.error || "テストに失敗しました" });
    }
  };

  const handleSwitchToNeo4j = async () => {
    if (!neo4jPassword) {
      setError("Neo4jパスワードを入力してください");
      return;
    }
    setSwitching(true);
    setError(null);
    setSuccess(null);

    const res = await switchDataSource("neo4j", {
      uri: neo4jUri,
      user: neo4jUser,
      password: neo4jPassword,
    });

    setSwitching(false);
    if (res.data) {
      setSuccess(res.data.message);
      fetchStatus();
    } else {
      setError(res.error || "切替に失敗しました");
    }
  };

  const handleSwitchToSqlite = async () => {
    setSwitching(true);
    setError(null);
    setSuccess(null);

    const res = await switchDataSource("sqlite");

    setSwitching(false);
    if (res.data) {
      setSuccess(res.data.message);
      fetchStatus();
    } else {
      setError(res.error || "切替に失敗しました");
    }
  };

  const inputClass =
    "w-full rounded-lg border border-neutral-300 dark:border-neutral-600 bg-white dark:bg-neutral-950 px-3 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="bg-white dark:bg-neutral-900 rounded-xl shadow-2xl border border-neutral-200 dark:border-neutral-700 w-full max-w-lg overflow-hidden">
        {/* ヘッダー */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-neutral-200 dark:border-neutral-700">
          <h2 className="text-lg font-semibold text-neutral-800 dark:text-neutral-100 flex items-center gap-2">
            <Database size={20} />
            データソース設定
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

        <div className="p-5 space-y-5 max-h-[70vh] overflow-y-auto">
          {/* メッセージ */}
          {error && (
            <div className="p-3 rounded-lg bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400 text-sm">
              {error}
            </div>
          )}
          {success && (
            <div className="p-3 rounded-lg bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400 text-sm flex items-center gap-2">
              <Check size={16} />
              {success}
            </div>
          )}

          {loading ? (
            <div className="flex items-center justify-center py-8">
              <Loader2 size={24} className="animate-spin text-neutral-400" />
            </div>
          ) : (
            <>
              {/* 現在のステータス */}
              <div className="p-4 rounded-lg border border-neutral-200 dark:border-neutral-700 bg-neutral-50 dark:bg-neutral-800/50">
                <div className="text-sm font-medium text-neutral-500 dark:text-neutral-400 mb-2">
                  現在のデータソース
                </div>
                <div className="flex items-center gap-3">
                  {status?.dataSourceType === "neo4j" ? (
                    <>
                      <Network
                        size={20}
                        className="text-green-600 dark:text-green-400"
                      />
                      <div>
                        <div className="font-semibold text-neutral-800 dark:text-neutral-100">
                          Neo4j
                        </div>
                        <div className="text-xs text-neutral-500">
                          {status.neo4j.uri} ({status.neo4j.user})
                          {status.neo4j.connected ? (
                            <span className="ml-1 text-green-600 dark:text-green-400">
                              接続済み
                            </span>
                          ) : (
                            <span className="ml-1 text-red-600 dark:text-red-400">
                              未接続
                            </span>
                          )}
                        </div>
                      </div>
                    </>
                  ) : (
                    <>
                      <Database
                        size={20}
                        className="text-blue-600 dark:text-blue-400"
                      />
                      <div>
                        <div className="font-semibold text-neutral-800 dark:text-neutral-100">
                          SQLite
                        </div>
                        <div className="text-xs text-neutral-500">
                          ローカルファイルベース
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>

              {/* Neo4j接続設定 */}
              <div className="space-y-3">
                <div className="text-sm font-medium text-neutral-700 dark:text-neutral-300 flex items-center gap-2">
                  <Network size={16} />
                  Neo4j接続設定 (Bolt)
                </div>

                <div>
                  <label
                    htmlFor="neo4jUri"
                    className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1"
                  >
                    URI
                  </label>
                  <input
                    id="neo4jUri"
                    type="text"
                    value={neo4jUri}
                    onChange={(e) => setNeo4jUri(e.target.value)}
                    className={inputClass}
                    placeholder="bolt://localhost:7687"
                  />
                </div>

                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label
                      htmlFor="neo4jUser"
                      className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1"
                    >
                      ユーザー
                    </label>
                    <input
                      id="neo4jUser"
                      type="text"
                      value={neo4jUser}
                      onChange={(e) => setNeo4jUser(e.target.value)}
                      className={inputClass}
                      placeholder="neo4j"
                    />
                  </div>
                  <div>
                    <label
                      htmlFor="neo4jPassword"
                      className="block text-xs font-medium text-neutral-500 dark:text-neutral-400 mb-1"
                    >
                      パスワード
                    </label>
                    <input
                      id="neo4jPassword"
                      type="password"
                      value={neo4jPassword}
                      onChange={(e) => setNeo4jPassword(e.target.value)}
                      className={inputClass}
                      placeholder="パスワード"
                    />
                  </div>
                </div>

                {/* テスト結果 */}
                {testResult && (
                  <div
                    className={`p-3 rounded-lg text-sm ${
                      testResult.ok
                        ? "bg-green-50 dark:bg-green-900/30 text-green-600 dark:text-green-400"
                        : "bg-red-50 dark:bg-red-900/30 text-red-600 dark:text-red-400"
                    }`}
                  >
                    {testResult.ok ? (
                      <span className="flex items-center gap-2">
                        <Check size={16} />
                        接続成功
                        {testResult.serverInfo && ` (${testResult.serverInfo})`}
                      </span>
                    ) : (
                      <span>
                        接続失敗: {testResult.error || "不明なエラー"}
                      </span>
                    )}
                  </div>
                )}

                {/* ボタン群 */}
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={handleTest}
                    disabled={
                      testing || !neo4jUri || !neo4jUser || !neo4jPassword
                    }
                    className="flex-1 flex items-center justify-center gap-2 rounded-lg border border-neutral-300 dark:border-neutral-600 hover:bg-neutral-50 dark:hover:bg-neutral-800 disabled:opacity-50 text-neutral-700 dark:text-neutral-300 px-4 py-2.5 text-sm font-medium transition-colors"
                  >
                    {testing ? (
                      <Loader2 size={16} className="animate-spin" />
                    ) : (
                      <Zap size={16} />
                    )}
                    {testing ? "テスト中..." : "接続テスト"}
                  </button>

                  {status?.dataSourceType !== "neo4j" ? (
                    <button
                      type="button"
                      onClick={handleSwitchToNeo4j}
                      disabled={switching || !neo4jPassword}
                      className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-green-600 hover:bg-green-700 disabled:opacity-50 text-white px-4 py-2.5 text-sm font-medium transition-colors"
                    >
                      {switching ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Save size={16} />
                      )}
                      {switching ? "切替中..." : "Neo4jに切替"}
                    </button>
                  ) : (
                    <button
                      type="button"
                      onClick={handleSwitchToSqlite}
                      disabled={switching}
                      className="flex-1 flex items-center justify-center gap-2 rounded-lg bg-blue-600 hover:bg-blue-700 disabled:opacity-50 text-white px-4 py-2.5 text-sm font-medium transition-colors"
                    >
                      {switching ? (
                        <Loader2 size={16} className="animate-spin" />
                      ) : (
                        <Database size={16} />
                      )}
                      {switching ? "切替中..." : "SQLiteに切替"}
                    </button>
                  )}
                </div>
              </div>
            </>
          )}
        </div>
      </div>
    </div>
  );
}
