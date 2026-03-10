[← README.md](../../README.md)

# status-069: T7-1/7-2/7-3 AI連携基盤（AIProvider・Ollama・summarize・diff）

- 日付: 2026-03-10
- ブランチ: claude/execute-status-todos-O8t4T

## 実施内容

### T7-1: AIProviderプロトコル + OllamaProvider

AIProviderプロトコルをコア層で定義し、OllamaProviderをプラグインとして分離。

- **`services/ai/__init__.py`**: `AIProvider` Protocolクラス定義（`chat()`, `summarize()`）
  - グローバルプロバイダレジストリ（`get_provider()`, `set_provider()`, `require_provider()`）
  - `runtime_checkable` で duck typing サポート
- **`services/ai/provider.py`**: `OllamaProvider` 実装
  - `urllib.request` のみ使用（追加外部依存なし）
  - `/api/chat` エンドポイントでchat/summarize
  - `/api/tags` で接続チェック（`available`プロパティ）
  - `create_provider_from_config()`: config.yamlからプロバイダ生成
- **`services/plugins/ollama/__init__.py`**: プラグインエントリポイント
  - `register()` で config 読み込み → OllamaProvider 登録
  - 登録失敗時はサイレントスキップ

### T7-2: jj ai summarize コマンド

- **`services/ai/summarizer.py`**: ファイル要約機能
  - `summarize_file()`: 単体ファイル要約（100KB制限）
  - `summarize_files()`: 複数ファイル一括要約（エラー個別ハンドリング）
- **CLI**: `jj ai summarize <file...>` / `jj ai sum <file...>`

### T7-3: jj ai diff コマンド

- **`services/ai/diff_analyzer.py`**: diff分析機能
  - `get_git_diff()`: git diff出力取得
  - `analyze_diff()`: diff テキストのAI分析（50K文字制限で自動切り詰め）
  - `analyze_git_diff()`: git diff取得 + AI分析の統合
- **CLI**: `jj ai diff [target] [--staged]`

### CLI追加コマンド

- `jj ai summarize <file...>` — ファイルの内容をAIで要約
- `jj ai diff [target] [--staged]` — git diffをAIで分析・要約
- `jj ai chat <message...>` — AIとチャット
- `jj ai status` — AIプロバイダの状態を表示

### テスト

26件のユニットテスト新規追加:
- `TestAIProviderProtocol`: プロトコル適合・レジストリ（5件）
- `TestOllamaProvider`: 基本動作・接続エラー（3件）
- `TestOllamaProviderWithMock`: モックサーバー経由テスト（3件）
- `TestCreateProviderFromConfig`: config解析（4件）
- `TestSummarizer`: ファイル要約（4件）
- `TestDiffAnalyzer`: diff分析（4件）
- `TestAICLI`: CLIコマンド統合（3件）

## ファイル構成

```
services/ai/__init__.py                    # [NEW] AIProviderプロトコル・レジストリ
services/ai/provider.py                    # [NEW] OllamaProvider実装
services/ai/summarizer.py                  # [NEW] ファイル要約
services/ai/diff_analyzer.py               # [NEW] diff分析
services/plugins/ollama/__init__.py        # [NEW] Ollamaプラグイン
services/cli/__init__.py                   # [MOD] jj ai サブコマンド追加
pyproject.toml                             # [MOD] ollama optional依存・entry point追加
tests/test_ai_service.py                   # [NEW] 26件テスト
docs/status/status-069.md                  # [NEW] 本status
```

## 設計判断

### urllib.request採用（httpx/requests不使用）

- OllamaProviderは標準ライブラリの`urllib.request`のみ使用
- 追加パッケージ依存ゼロ（`pip install jj[ollama]`は実質空依存）
- Ollama REST APIはシンプルなJSON POST/GETのみで十分

### AIProviderプロトコル（Protocol + runtime_checkable）

- duck typing サポートにより、外部プラグインも容易に適合
- `require_provider()` でプロバイダ未設定時の明確なエラーメッセージ
- 将来の OpenAI/Claude API 対応も同一プロトコルで追加可能

### Ollama config 構造

```yaml
ai:
  provider: ollama          # ollama | disabled
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.1:8b"
    embed_model: "nomic-embed-text"
```

## TODO

### T7 継続
- [ ] T7-4: 簡易RAG（embedding + 検索）
- [ ] T7-5: jj tips（tips抽出・蓄積・表示）
- [ ] T7-6: ダッシュボードAIアシスタントパネル

### ワークトラック（継続）
- [ ] T8: 汎用データ管理

### 確認事項・懸念
- Ollama接続テストは実サーバーなしのモック方式。CI環境でも安定動作。
- embed()メソッドはRAGフェーズ(T7-4)で追加予定。Protocol定義への追加が必要。
