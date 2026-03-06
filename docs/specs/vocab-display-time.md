[← README.md](../../README.md)

# Vocab表示時適用仕様書

## 概要

現在vocabはparse時に全ノードプロパティのキーと値を変換している（VocabFinalizer, priority=100）。
これにより以下の問題が発生している:

1. **変換前と後が混在**: パーサーによってvocab適用のタイミングが異なり、生キーと変換後キーが混在
2. **逆引きの困難**: graph.yamlに保存されるキーがvocab依存で、vocab変更時に過去データとの互換性が失われる
3. **デバッグ困難**: プロパティキーが環境やconfigにより異なる表記になる

## 設計方針

### 原則: 保存は生キー、表示時のみvocab適用

```
Parse時:  ファイル → Node(properties={idx: 1, v: 1, stress: 450})  # 生キー
保存時:   graph.yaml に生キーで永続化
表示時:   vocab変換 → {条件: 1, v: 1, 応力: 450}  # UIやCLI出力時のみ
```

### 変更点

| コンポーネント | Before | After |
|---|---|---|
| VocabFinalizer (priority=100) | 全ノードプロパティを変換 | **廃止** |
| DirectoryParser | vocab.get(key) で変換後キーを格納 | 生キー（idx, v等）を格納 |
| GraphService.file_to_node | vocab.get(key) で変換後キーを格納 | 生キー（idx, v等）を格納 |
| DisplayNameParser | vocab変換済みキーでテンプレート展開 | 生キーでテンプレート展開（vocab逆引きは維持） |
| AbaqusConnectorParsers | inline vocab変換 | 生キーを格納 |
| DashboardDataProvider | vocab変換済みキーを前提 | 表示時にvocab変換ユーティリティを使用 |
| sort_columns_by_vocab | vocab変換済みキーの順序付け | 生キー→vocab変換した表示名での順序付け |
| HTML Export | vocab変換済みキーを前提 | 表示時変換 |
| Obsidian Export | inline vocab変換 | 表示時変換ユーティリティを使用 |

### 新規ユーティリティ: `vocab_display`

```python
# modules/vocab_display.py

def translate_key(key: str, vocab: dict[str, str]) -> str:
    """キーをvocab変換する（表示用）"""
    return vocab.get(key, key)

def translate_properties(props: dict[str, Any], vocab: dict[str, str]) -> dict[str, Any]:
    """プロパティ辞書のキーと文字列値をvocab変換する（表示用）"""

def translate_columns(columns: list[str], vocab: dict[str, str]) -> list[str]:
    """カラム名リストをvocab変換する（表示用）"""
```

## 実装計画

### Phase 1: VocabFinalizer廃止・DirectoryParser修正
- VocabFinalizerのapply()を空操作に変更（クラスは残す）
- DirectoryParserで生キーを格納するように変更
- GraphService.file_to_nodeで生キーを格納するように変更
- DisplayNameParserを生キーベースに変更

### Phase 2: vocab_displayユーティリティ追加
- modules/vocab_display.py を新規作成
- 既存のVocabFinalizer内のロジックを移動（表示専用として再利用）

### Phase 3: Dashboard/Export/CLI修正
- DashboardDataProviderのキー識別をvocab_display経由に変更
- テーブル表示、HTMLエクスポートでvocab変換を適用
- Obsidianエクスポートの修正

### Phase 4: テスト修正
- 既存vocabテストの期待値を生キーに変更
- 表示時変換テストを追加

## 影響範囲

- **services/parse/parsers/vocab_finalizer.py**: 空操作化
- **services/parse/parsers/directory_parser.py**: 生キー格納
- **services/parse/parsers/display_name_parser.py**: 生キーベース
- **services/graph/__init__.py**: file_to_node生キー格納
- **services/graph/project_graph.py**: 生キー検索
- **services/dashboard/data_provider.py**: 表示時変換
- **services/dashboard/components/table.py**: 表示時変換
- **services/dashboard/html_export.py**: 表示時変換
- **services/export/connectors/obsidian/**: 表示時変換
- **services/query/sort.py**: 表示時変換
- **tests/**: 20+テストファイル

## リスク・注意点

- graph.yamlのフォーマットが変わるため、既存プロジェクトはre-parseが必要
- vocabを変更してもgraph.yamlの再生成が不要になる（利点）
- 表示時変換のオーバーヘッドは微小（dict lookup）
