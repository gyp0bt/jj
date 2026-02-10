[READMEへ戻る](../../README.md)

# status-045: idx→条件統一、CLIビジネスロジックのservices.service分離

**日付**: 2026-02-10

## 概要

2つの主要な変更を実施:
1. **idx→条件統一**: vocab定義を`番号`から`条件`に統一。config.yamlを真実の源泉とし、コード内のハードコード依存を除去。
2. **CLIビジネスロジック分離**: `services/cli/__init__.py`と`services/cli/graph.py`に混在していたビジネスロジックを`services/service/`に分離。CLI層は引数パース＋出力整形のみに責務を限定。

テスト443件パス（前回比+4件回復）、0件失敗、20スキップ。

## 変更内容

### 1. idx→条件統一

**背景**: `default-config.yaml`では`idx: 条件`と定義されているが、テストコードやドキュメントでは`idx: 番号`を使用しており不整合が存在していた。

**方針**: config.yamlが真実。コード内のハードコード依存は分離するかconfigに準じる。

**変更箇所**:

| ファイル | 変更内容 |
|---------|---------|
| `shared/assets/README.md` | vocab説明: `idx: 番号` → `idx: 条件` |
| `services/parse/parsers/output_parser.py` | `_nodes_have_same_props()`のハードコード`"番号"`を除去。vocab引数を追加しconfig依存に変更 |
| `tests/test_graph_feature.py` | 全vocab定義を`"idx": "番号"` → `"idx": "条件"`に統一。assert値も対応修正 |
| `tests/test_obsidian_connector.py` | vocab関連テストを`番号` → `条件`に統一。テスト名も`bangou` → `jouken`に変更 |

**`_nodes_have_same_props`の変更詳細**:
- 引数に`vocab: dict[str, str] | None`を追加
- ハードコードされていた`"番号"`を除去
- vocabから`idx`の変換後キーを動的に取得し、compare_keysに追加
- `ResultRelationParser`と`AssetRelationParser`の呼び出し箇所で`vocab=graph.config.vocab`を渡すように修正

### 2. CLIビジネスロジック分離

**設計**: CLI層（`services/cli/`）は引数パース＋出力整形のみ。ビジネスロジックは`services/service/`に集約。

```
services/service/
├── __init__.py     # SubmitService, InfoService のre-export
├── submit.py       # SubmitService: ジョブ投入・ターゲット解決・ファイル操作
└── info.py         # InfoService: グラフ情報検索・エクスポート
```

#### SubmitService (`services/service/submit.py`)

`cli/__init__.py`から以下のビジネスロジックを抽出:

| メソッド | 旧所在 | 概要 |
|---------|--------|------|
| `resolve_targets()` | `cli/__init__.py::resolve_targets()` | CLI引数からターゲットファイルを解決 |
| `get_abq_job_name()` | `cli/__init__.py::get_abq_job_name()` | Abaqusジョブ名を生成 |
| `write_jcf()` / `write_standard_jcf()` / `write_explicit_jcf()` | `cli/__init__.py` | JCFファイル生成 |
| `execute()` | `cli/__init__.py::execute()` | リモート実行 |
| `write_jcf_and_execute()` | `cli/__init__.py` | JCF書き出し+実行 |
| `submit()` | `cli/__init__.py::run_submit()` のコア部分 | ジョブ投入のオーケストレーション |
| `run_files_get()` / `run_files_put()` / `run_files_move()` | `cli/__init__.py` | ファイル操作 |
| `run_check_syntax()` | `cli/__init__.py` | Syntax検査 |

#### InfoService (`services/service/info.py`)

`cli/graph.py`から以下のビジネスロジックを抽出:

| メソッド | 旧所在 | 概要 |
|---------|--------|------|
| `search_nodes()` | `graph.py::_run_info()` のノード検索ロジック | 複合条件でノードを検索 |
| `export_data()` | `graph.py::_run_export_data()` のデータ変換ロジック | CSV/JSON形式でエクスポート |
| `resolve_file_path()` | `graph.py::_resolve_file_path()` | ファイル名からパスを解決 |
| `load_graph()` / `parse_and_save()` / `summary()` | GraphServiceのラッパー | グラフ操作のファサード |

#### cli/__init__.pyのリファクタリング

- 760行 → 376行に削減（約50%削減）
- SubmitServiceのインスタンスを通じてビジネスロジックを呼び出す構造に変更
- CLI関数はSubmitServiceの結果を受けて出力整形のみ担当

#### cli/graph.pyのリファクタリング

- `_run_info()`: InfoService.search_nodes()に委譲
- `_run_export_data()`: InfoService.export_data()に委譲
- `_resolve_file_path()`: InfoService.resolve_file_path()に委譲

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `shared/assets/README.md` | 変更: vocab `idx: 番号` → `idx: 条件` |
| `services/parse/parsers/output_parser.py` | 変更: ハードコード`番号`除去、vocab引数追加 |
| `services/service/__init__.py` | 変更: SubmitService, InfoService re-export |
| `services/service/submit.py` | 新規: SubmitService（ジョブ投入・ターゲット解決） |
| `services/service/info.py` | 新規: InfoService（グラフ情報検索・エクスポート） |
| `services/cli/__init__.py` | 変更: ビジネスロジックをSubmitServiceに委譲 |
| `services/cli/graph.py` | 変更: info/exportロジックをInfoServiceに委譲 |
| `tests/test_graph_feature.py` | 変更: vocab `番号` → `条件`に統一 |
| `tests/test_obsidian_connector.py` | 変更: vocab `番号` → `条件`に統一 |

## アーキテクチャ

```
main.py
  ↓
services/cli/          # CLI層: 引数パース + 出力整形
  ├── __init__.py      # submit/list/check/files/run ディスパッチ
  └── graph.py         # init/parse/show/export/info/diff/credential ディスパッチ
       ↓
services/service/      # サービス層: ビジネスロジック
  ├── submit.py        # SubmitService（ジョブ投入・ターゲット解決）
  └── info.py          # InfoService（グラフ情報検索・エクスポート）
       ↓
services/graph/        # ドメイン層: グラフデータ管理
  ├── __init__.py      # GraphService（コア）
  └── project_graph.py # ProjectGraph（データモデル）
       ↓
services/parse/        # パーサー層: ファイル解析・エンリッチメント
  ├── base.py          # AbstractFileParser（パイプライン）
  ├── file_parse.py    # FileParse（ファイル名解析）
  ├── parsers/         # グラフパーサー群
  └── connectors/      # ファイル形式別パーサー
```

## テスト結果

```
443 passed, 0 failed, 20 skipped
```

- ユニットテスト: 18件全パス
- グラフ機能テスト: 191件パス、18スキップ
- Obsidianコネクタテスト: 52件全パス（前回の4件失敗を解消）
- パイプラインテスト: 別途実行

## TODO / 次のステップ

- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤
- [ ] SubmitServiceの統合テスト追加（現在はSSH依存のため手動テスト）
- [ ] InfoServiceの単体テスト追加

## 確認事項

- `services/cli/__init__.py`はモジュールインポート時に`load_ssh_config()`を呼び出す設計を維持。SSH設定ファイル（`.pyssh.yaml`）が存在しない環境ではCLI初期化がエラーになるが、`jj graph`系コマンドのみ使う場合は影響なし（graph.pyは直接呼ばれる）。
- `SubmitService`のリモート実行系メソッド（`execute()`, `write_jcf_and_execute()`）はSSH依存のためCI環境ではテスト不可。手動確認が必要。
- `_nodes_have_same_props`のvocab引数は後方互換性のためOptional。vocabが渡されない場合は基本キー（`index`, `w`, `t`）のみで比較。
