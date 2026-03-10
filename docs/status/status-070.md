[← README.md](../../README.md)

# status-070: T7-4/7-5 RAG検索・Tips抽出

- 日付: 2026-03-10
- ブランチ: claude/execute-status-todos-eL76K

## 実施内容

### T7-4: 簡易RAG（embedding + コサイン類似度検索）

AIProviderプロトコルにembed()メソッドを追加し、簡易RAGシステムを実装。

- **`services/ai/__init__.py`**: AIProviderプロトコルに`embed()`メソッド追加
- **`services/ai/provider.py`**: OllamaProviderに`embed()`実装（`/api/embed`エンドポイント）
- **`services/ai/rag.py`**: [NEW] RAGモジュール
  - `chunk_text()`: テキストを行境界尊重でチャンク分割
  - `_cosine_similarity()`: 純Python実装のコサイン類似度計算
  - `RagIndex`: チャンク＋埋め込みベクトルのインデックス管理
    - `add_file()`: ファイルをチャンク化→埋め込み→インデックス追加
    - `remove_file()`: ファイルのエントリ削除
    - `search()`: クエリのコサイン類似度検索（top-k）
    - `save()`/`load()`: `.j2/storage/rag_index.json`に永続化
  - `rag_query()`: RAG検索 + AIコンテキスト付き回答

### T7-5: Tips抽出・蓄積・表示

ファイルからAIでTips/知見を抽出し、蓄積・検索・ランダム表示する機能。

- **`services/ai/tips.py`**: [NEW] Tipsモジュール
  - `TipsStore`: Tips永続化ストア（`.j2/storage/tips.json`）
    - `add_tip()`: Tip追加（title, body, tags, source）
    - `get_random()`: ランダム取得
    - `search()`: キーワード検索（title/body/tags横断）
    - `list_all()`: 全件取得
  - `extract_tips_from_file()`: AIでファイルからTips抽出
  - `extract_tips_from_text()`: テキストからTips抽出
  - `_parse_tips_response()`: AI応答のJSON配列パース（```フェンス対応）

### CLIコマンド追加

- `jj ai index <file...>` — ファイルをRAGインデックスに追加
- `jj ai ask <question> [--top-k N]` — RAG検索で質問に回答
- `jj ai tips` — ランダムTips表示
- `jj ai tips --extract <file...>` — ファイルからTipsを抽出・蓄積
- `jj ai tips --search <keyword>` — キーワードでTips検索
- `jj ai tips --list` — 全Tips表示
- `jj ai status` — RAGインデックス情報も表示するよう拡張

### テスト

30件の新規テスト追加（既存26件+新規30件=計56件）:
- `TestChunkText`: チャンク分割（4件）
- `TestCosineSimilarity`: コサイン類似度計算（3件）
- `TestRagIndex`: インデックス操作（7件）
- `TestRagQuery`: RAGクエリ（2件）
- `TestOllamaProviderEmbed`: embed API（2件）
- `TestTipsStore`: Tips蓄積（6件）
- `TestTipsExtract`: Tips抽出・パース（5件）
- MockOllamaサーバーに `/api/embed` エンドポイント追加

## ファイル構成

```
services/ai/__init__.py                    # [MOD] embed()メソッド追加
services/ai/provider.py                    # [MOD] OllamaProvider.embed()追加
services/ai/rag.py                         # [NEW] RAGモジュール
services/ai/tips.py                        # [NEW] Tipsモジュール
services/cli/__init__.py                   # [MOD] index/ask/tipsサブコマンド追加
tests/test_ai_service.py                   # [MOD] 30件テスト追加
docs/status/status-070.md                  # [NEW] 本status
```

## 設計判断

### 純Python実装のコサイン類似度

- numpy依存を避け、math.sqrtとzip()で計算
- 数千エントリ規模のローカルRAGには十分な性能
- 将来的にnumpyに切り替えも容易

### Tips抽出のJSON応答パース

- AIの応答は```jsonフェンスで囲まれる場合がある
- フェンス除去→JSON.loads→バリデーションの3段階パース
- パース失敗時は空リストを返し、サイレントフォールバック

### RagIndexの永続化

- `.j2/storage/rag_index.json`にJSON形式で保存
- 埋め込みベクトルも含めて完全永続化（再計算不要）
- ファイル再インデックス時は既存エントリを自動置換

## TODO

### T7 継続
- [ ] T7-6: ダッシュボードAIアシスタントパネル

### ワークトラック（継続）
- [ ] T8: 汎用データ管理

### 確認事項・懸念
- RAGインデックスが巨大化した場合、JSONシリアライズのパフォーマンスが懸念。数万エントリを超える場合はSQLite等へのマイグレーションを検討。
- Tips抽出の品質はAIモデルに依存。小規模モデル（8B）での抽出精度は検証が必要。
