[READMEへ戻る](../../README.md)

# 実装状況 (status-020)

## 概要

`jj g parse` の拡張（サブバージョン関係・グループ関係構築）、設定機能の大幅拡充（path-type-map, path-property-map, ignore等）、Obsidian記法対応の改善を実装しました。

## 実装内容

### 1. デフォルト設定ファイル（assets/default-config.yaml）

**ファイル**: `assets/default-config.yaml`

jjのデフォルト設定を一元管理するYAMLファイルを作成しました。

**主要な設定項目**:
- `vocab`: 語彙マッピング（例: "idx" → "番号"）
- `path-type-map`: パスパターンによるファイルタイプ指定
- `path-property-map`: パスパターンによるプロパティ自動付与
- `ignore`: 除外パターン（.gitignore相当）
- `obsidian`: Obsidianエクスポート設定

### 2. 設定モデルの拡張（config/__init__.py）

**新規追加クラス**:
- `PathTypeMapConfig`: path-type-map設定の管理
- `PathPropertyMapConfig`: path-property-map設定の管理
- `PathTagMapConfig`: path-tag-map設定の管理
- `IgnoreConfig`: ignore設定（除外パターン）の管理
- `ObsidianExportConfig`: Obsidianエクスポート設定の管理
- `GraphConfig`: 上記すべてを統合した設定クラス

**新規追加関数**:
- `load_default_config()`: デフォルト設定の読み込み
- `load_project_config()`: プロジェクト設定の読み込み（デフォルトとマージ）
- `init_graph_config()`: 設定ファイルの初期化

### 3. GraphServiceの拡張（services/graph/__init__.py）

**変更点**:
- `GraphConfig`を使用した設定の自動読み込み
- `ignore`設定を使ったファイルスキャン時の除外処理
- `path-type-map`/`path-property-map`/`path-tag-map`/`vocab`を使ったノード生成

**新規機能: サブバージョン関係・グループ関係の構築**

`_build_version_and_group_relations()` メソッドを追加:
- 同一type/indexのノードをグループ化
- version順にソートして`next_version`リレーションを作成
- グループ内のノード間で`same_index_group`リレーションを作成

### 4. Obsidianコネクタの拡張（services/connectors/obsidian.py）

**新しいリンク記法対応**:
- `to_obsidian_file_link()`: 実ファイルへのリンク `[[path|name]]`
- `to_obsidian_md_link()`: mdファイルへのリンク `[[filename]]`
- `to_labeled_link()`: ラベル付きリンク `label:[[filename]]`

**新機能: .baseファイル（NodeGroup）生成**:
- `_write_base_files()`: 同一indexのノードをグループ化した.baseファイルを生成
- `_format_base_file()`: views設定を含む.baseファイルの内容を生成

**リレーション情報のエクスポート**:
- `write_md_with_relations()`: リレーション情報を含むmdファイル生成
- エクスポート時にリレーション情報を「関連ファイル」セクションとして出力

### 5. `jj g init` サブコマンドの追加

**ファイル**: `cli/graph.py`

```bash
jj g init           # 設定ファイルを初期化
jj g init --overwrite  # 既存ファイルを上書き
```

デフォルト設定を`.jj/config/config.yaml`にコピーします。

## ファイル構成の変更

```
jj/
├── assets/
│   └── default-config.yaml  (新規: デフォルト設定)
├── cli/
│   └── graph.py             (変更: initサブコマンド追加)
├── config/
│   └── __init__.py          (変更: 設定モデル大幅拡張)
├── services/
│   ├── graph/
│   │   └── __init__.py      (変更: サブバージョン・グループ関係構築)
│   └── connectors/
│       └── obsidian.py      (変更: Obsidian記法対応、.baseファイル生成)
└── docs/
    └── status/
        └── status-020.md    (新規)
```

## TODO（ユーザーからの追加要求）

以下は今後実装予定の項目です：

- [ ] 設定読み込みは遅延インポートにする
  - SSH設定が不要な場合でもcli/__init__.pyのインポート時にエラーになる問題の解消
- [ ] jj nはjj gに統合（グラフ機能がメイン、obsidian機能はexportのみ）
  - 既存のjj nコマンドのビジネスロジックをjj gに移行
- [ ] jj g initでconfig等のテンプレート生成（ある場合は上書き）
  - 実装済み：`jj g init --overwrite`
- [ ] タイプ指定機能を拡充
  - path-type-mapのパターンマッチング精度向上
  - 複数条件の組み合わせ対応

## 設計上の懸念事項

1. **path-type-mapの評価順序**: 現在は上から順に評価し、最初にマッチしたルールを適用。複雑なパターンでは意図しない結果になる可能性あり
2. **vocabの適用タイミング**: 現在はファイル名パース時のpropsキーのみ変換。frontmatter出力時の変換も検討が必要

## 次のステップ

1. 既存のjj nコマンドのテストを実行して互換性を確認
2. jj g parseとexportの統合テスト
3. 遅延インポートの実装でSSH設定依存を解消

---

**作成日時**: 2026-02-05
**担当**: Claude Code
**前回**: [status-019.md](./status-019.md)
**次回**: status-021.md (未作成)
