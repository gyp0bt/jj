[← roadmap.md](../roadmap.md)

# 中期計画 v0.3 — 統合ワークフロー・AI連携・ダッシュボード高度化

**策定日**: 2026-03-07
**スコープ**: v0.2.0残タスク完了 + v0.3.0新規テーマ

---

## 全体像

```
v0.2.0 残タスク                         v0.3.0 新規テーマ
─────────────                         ──────────────
T1: コードベースTODO解消               T5: リモートジョブ実行基盤
T2: Config二層分離                     T6: ダッシュボード高度化
T3: M6 Phase 5 (MLダッシュボード)       T7: Ollama AI連携プラグイン
T4: Deprecation Warning修正            T8: 汎用データ管理への昇華
```

### 依存関係

```
T1 (TODO解消) ←── T2 (Config分離)   ← 多くのTODOがconfig移動を要求
                    │
T4 (deprecation) ── T6 (Dashboard高度化)
                    │   ├── AgGridフィルタ共有
                    │   ├── グラフ可視化美化
                    │   ├── parseボタン
                    │   └── Streamlitカスタムコンポーネント
                    │
T2 ────────────── T5 (リモートジョブ)
                    │   ├── フォルダマッピング
                    │   ├── submit / collect 分離
                    │   └── staモニタリング
                    │
T3 (MLダッシュボード) ─ T8 (汎用データ管理)
                    │
                    └── T7 (Ollama AI連携)
```

---

## T1: コードベースTODO解消

**優先度**: 高（T2と連動）
**工数目安**: 1セッション

コード内に散在する13件のTODOコメントを実装する。

| # | ファイル | 内容 | 対応方針 |
|---|---------|------|---------|
| 1 | `services/dashboard/components/table.py:77` | ソートロジックの関数化 | query.pyへ抽出 |
| 2 | `services/dashboard/components/table.py:150` | list[str]パースのconfig対応+関数化 | T2と連動、widgets.pyへ |
| 3 | `services/graph/__init__.py:121` | version/index/activeハードコード → config | T2と連動、config.yamlで定義 |
| 4 | `services/parse/file_parse.py:18` | DEFAULT_EXTENSIONS → config | T2と連動 |
| 5 | `services/parse/connectors/abaqus/parameter_parser.py:31` | include関係・パラメータ式評価 | 仕様確認後実装 |
| 6 | `services/parse/connectors/abaqus/result_parser.py:61` | カットバック・収束情報の収集 | v0.2対象 |
| 7-12 | `connectors/{calculix,fluent,lsdyna,openfoam,hfss,flow3d}/` | 検証環境確保後に実装 | M2依存（据え置き） |
| 13 | GalleryDefaults二重構造 | status-050から据え置き | T6と連動 |

**実施順**: #3, #4 → T2完了後に #1, #2 → #5, #6 → #13

---

## T2: Config二層分離（デフォルト / ユーザー定義）

**優先度**: 高
**工数目安**: 2セッション

### 現状の課題

- `default-config.yaml` → `jj init` で `.j2/config/config.yaml` にコピー
- ユーザーが編集した部分とデフォルトが混在し、バージョンアップ時にデフォルト変更が反映されない
- ハードコードされた拡張子・プレフィックス・特殊キー名が分散

### 設計方針

```
shared/assets/default-config.yaml    ← パッケージ同梱（常に最新）
.j2/config/config.yaml              ← ユーザー定義（差分のみ）
```

**マージ戦略**: deep merge（ユーザー定義が勝つ）

```python
# 擬似コード
merged = deep_merge(default_config, user_config)
# user_configに存在するキーはuser値を採用
# user_configに存在しないキーはdefault値を採用
```

### 実装計画

| Phase | タスク |
|-------|--------|
| 2-1 | `ConfigLoader.load()` に deep merge ロジック追加 |
| 2-2 | `default-config.yaml` に全デフォルト値を網羅（extensions, prefixes, special_keys, dashboard defaults） |
| 2-3 | `jj init` を変更: default-config.yamlをコピーせず、空の user-config.yaml を生成 |
| 2-4 | 既存プロジェクトの移行パス: `jj config migrate` で差分抽出 |
| 2-5 | T1の #3, #4 を反映（ハードコードをdefault-configへ移動） |

### config.yaml ユーザー定義例

```yaml
# .j2/config/config.yaml — ユーザー定義のみ記述
# 未記述のキーはdefault-config.yamlの値が使われる

extensions:
  calculation_input:
    - ".inp"
    - ".fem"  # 追加拡張子

prefixes:
  go_: calculation_input
  run_: calculation_input  # プロジェクト固有

dashboard:
  theme: dark
```

---

## T3: M6 Phase 5 — MLダッシュボード統合

**優先度**: 中
**工数目安**: 2セッション

M6のPhase 1-4（パーサー9種）は完了済み。Phase 5でダッシュボードに統合する。

| Phase | タスク |
|-------|--------|
| 5-1 | `MLOverviewPage` — MLノード一覧（dataset, model, script, experiment）|
| 5-2 | 三層データフロー可視化（T6のグラフ美化と連動） |
| 5-3 | モデルレジストリビュー（チェックポイント比較） |
| 5-4 | 最適化可視化（Optuna study結果、パレートフロント） |

---

## T4: Deprecation Warning修正

**優先度**: 高（すぐ対応可能）
**工数目安**: 0.5セッション

調査の結果、コード上に明示的なdeprecated API使用は見つからなかった。ユーザーが報告するwarningは以下の可能性:

1. **streamlit本体のバージョン依存** — `st.dataframe()` や plotly連携の内部API変更
2. **st_aggrid** — ライブラリ自体がStreamlit最新版と非互換
3. **plotly** — テンプレートや引数のdeprecation

**対応手順**:
- ダッシュボード起動時のwarningログを採取して特定
- 該当APIを最新推奨APIに置換
- `streamlit`, `plotly`, `st-aggrid` のバージョンピン見直し

---

## T5: リモートジョブ実行基盤

**優先度**: 高（ユーザーの主要ワークフロー）
**工数目安**: 4-5セッション
**既存資産**: `modules/pyssh/ssh.py`, `services/plugins/abaqus/submit.py`, M5仕様書

### 現状分析

- `modules/pyssh/` にparamikoベースのSSHClient実装あり
- `.pyssh.yaml` でホスト・パスマッピング設定
- `submit.py` にAbaqus固有のジョブ投入ロジックあり（凍結中）
- M5仕様書に `jj r --remote` の構想あり（Phase 5）

### ユーザーの現在のワークフロー

```
1. ローカルで入力ファイル作成
2. CLIでファイル転送 + ジョブ投入（手動コマンド）
3. watchで .sta ファイル末尾を監視（別ターミナル）
4. ジョブ完了後、結果ファイル回収（手動コマンド）
→ 投入と回収は別々のコマンドとして実行（プロセス維持が非効率なため）
```

### 設計方針: イベントドリブン分離アーキテクチャ

投入→監視→回収を**3つの独立コマンド**として設計し、ステート管理で連携する。

```
jj submit [target]        # 投入: ファイル転送 + ジョブ投入 + ステート記録
jj watch [target]         # 監視: .staファイルのtail -f相当（Ctrl+Cで離脱可能）
jj collect [target]       # 回収: 結果ファイルダウンロード + parse自動実行
jj job status             # 一覧: 投入済みジョブの状態確認（qstat/sacct相当）
```

**ステート管理**: `.j2/storage/jobs/job-{timestamp}.yaml`

```yaml
# job state file
job_id: "model_v3_idx1"
status: submitted  # submitted → running → completed → collected
submitted_at: "2026-03-07T10:00:00"
remote_host: "grid-server"
remote_dir: "/usr2/username/work/project_a/v3/"
local_dir: "F:/active/project_a/v3/"
command: "abaqus job=go_sample_v3_idx1 cpus=8"
input_files: ["go_sample_v3_idx1.inp"]
expected_outputs: ["go_sample_v3_idx1.odb", "go_sample_v3_idx1.sta", "go_sample_v3_idx1.dat"]
```

### バッチ投入対応

```bash
# 複数ジョブを一括投入
jj submit go_sample_v3_idx{1..5}

# 投入済み全ジョブの状態確認
jj job status

# 完了済みジョブの一括回収
jj collect --completed
```

### フォルダマッピング設計

`.pyssh.yaml` を拡張してベースフォルダペアを定義:

```yaml
host: grid-server
user: username
folder_mappings:
  - local: "F:/active/"
    remote: "/usr2/username/work/"
  - local: "D:/archive/"
    remote: "/usr2/username/archive/"
# マッピング: F:/active/project_a/v3/ → /usr2/username/work/project_a/v3/
```

### staモニタリング

```bash
jj watch go_sample_v3_idx1
# → SSH接続して .sta ファイルの末尾をストリーミング表示
# → 完了検知時に自動的にjob stateをcompleted更新
# → Ctrl+C で安全に離脱（ジョブは継続）
```

### 実装計画

| Phase | タスク | 依存 |
|-------|--------|------|
| 5-1 | フォルダマッピングConfig拡張（.pyssh.yaml） | T2 |
| 5-2 | JobState モデル + ストレージ | — |
| 5-3 | `jj submit` — ファイル転送 + リモート実行 + State記録 | 5-1, 5-2 |
| 5-4 | `jj watch` — SSHストリーミング + 完了検知 | 5-3 |
| 5-5 | `jj collect` — 結果ダウンロード + parse統合 | 5-3 |
| 5-6 | `jj job status` — ジョブ一覧 + qstat連携 | 5-2 |
| 5-7 | バッチ投入（複数target展開） | 5-3 |
| 5-8 | ダッシュボードJob Monitorページ（T6連動）— Prefect UIがある場合はリンク誘導のみ | 5-2 |

### 提案: 投入と回収の効率化パターン

> **現状の課題**: 投入→完了待ち→回収でプロセスを維持するのが非効率

**回収パターン**

```bash
# パターン1: 手動（推奨・最小構成）
jj submit go_sample_v3_idx1
# ... 数時間後 ...
jj job status          # 完了確認
jj collect --completed # 完了分一括回収

# パターン2: ワンショット待機（小規模ジョブ向け）
jj submit go_sample_v3_idx1 --wait --collect
# → 完了まで監視し、完了したら自動回収して終了
```

**推奨はパターン1（手動）**: シンプルで確実。`jj job status` で完了確認 → `jj collect` で回収。Prefect UIがあれば履歴が自動で可視化される。

### T5-9: Prefect統合 — 監視ダッシュボードとしての活用

#### 方針転換: オーケストレーションではなくオブザーバビリティ

Prefectの`flow.serve()`やDeploymentはgitレポジトリ前提 or 常駐プロセスが必要で、
CAEプロジェクトごとにタスク定義を書くのは運用負荷が高すぎる。

**Prefectに求めるもの**: 美しいダッシュボードと実行履歴の可視化。
**Prefectに求めないもの**: スケジューリング、リトライ制御、オーケストレーション。

```
jjコマンド実行（submit, run, collect）
  ↓ 実行完了後
Prefect API にFlow Run を事後記録（fire-and-forget）
  ↓
Prefect UI で履歴閲覧・状態確認
```

#### 設計: 事後記録パターン（Post-hoc Logging）

```python
# jjのコマンド実行は従来通り。Prefectデコレータは使わない。
# 実行結果をPrefect APIに「記録」するだけ。

from __future__ import annotations
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from services.run import RunResult

def report_to_prefect(result: "RunResult", flow_name: str = "jj-run") -> None:
    """実行結果をPrefect UIに事後記録する（optional、失敗しても無視）"""
    try:
        from prefect.client.orchestration import get_client
        from prefect.artifacts import create_markdown_artifact
        import asyncio

        async def _report():
            async with get_client() as client:
                # Flow Runを作成（実行済みとして記録）
                flow_run = await client.create_flow_run(
                    flow=None,
                    name=f"{result.command[0]} @ {result.started_at}",
                    state=Completed() if result.exit_code == 0 else Failed(),
                    tags=["jj", flow_name],
                )
                # Artifactとして詳細情報を添付
                await create_markdown_artifact(
                    key=f"jj-run-{flow_run.id}",
                    markdown=_build_run_markdown(result),
                )

        asyncio.run(_report())
    except ImportError:
        pass  # Prefect未インストール → 何もしない
    except Exception:
        pass  # Prefectサーバー未起動 → 何もしない（jj本体に影響させない）


def _build_run_markdown(result: "RunResult") -> str:
    """RunResultをPrefect Artifact用のMarkdownに変換"""
    files = "\n".join(f"- `{f}`" for f in result.trace_files) or "なし"
    return f"""## {" ".join(result.command)}

| 項目 | 値 |
|------|-----|
| exit code | {result.exit_code} |
| duration | {result.duration_seconds:.1f}s |
| host | {result.host} |
| started | {result.started_at} |

### 変更ファイル
{files}
"""
```

#### 統合ポイント

jjの既存コマンドに1行追加するだけ:

```python
# services/run/__init__.py — RunService.execute() の末尾
result = RunResult(...)
self._save_log(result)           # 既存: JSON保存
self._update_graph_storage(...)  # 既存: グラフ更新
report_to_prefect(result)        # 追加: Prefectに事後記録（optional）
```

同様に `jj submit`, `jj collect` にも追加可能。

#### 運用パターン

```bash
# 普段の作業（Prefectなしで完全に動作）
jj submit go_sample_v3_idx1
jj job status
jj collect --completed

# 履歴を振り返りたいとき → Prefect UIをオンデマンド起動
jj prefect up                    # prefect server start のラッパー
# → http://localhost:4200 でPrefect UIが開く
# → 過去のjj run / submit / collect の履歴がタイムラインで見える
# → 作業が終わったら閉じる
jj prefect down
```

**ポイント**:
- `flow.serve()` 不要 — 常駐プロセスなし
- Deployment定義不要 — gitレポジトリ前提なし
- 各プロジェクトでのタスク定義不要 — jjが自動記録
- Prefect未インストールでも全コマンド動作（ImportErrorは握りつぶす）

#### Prefect UI vs Streamlitダッシュボード の棲み分け

| 機能 | Prefect UI | Streamlitダッシュボード |
|------|-----------|----------------------|
| 実行履歴タイムライン | ◎（本職） | × |
| ジョブ状態の俯瞰 | ◎ | △（T5-8で簡易版） |
| 実行ログ詳細 | ◎ | × |
| ファイルグラフ・比較分析 | × | ◎（本職） |
| Run比較・パラメータ探索 | × | ◎ |
| CAE固有ページ（材料・メッシュ） | × | ◎ |

**結論**: 実行履歴の俯瞰はPrefect UI、データ分析はStreamlit。補完関係。

#### 実装フェーズ（T5に統合）

| Phase | タスク | 依存 |
|-------|--------|------|
| 5-9a | `report_to_prefect()` ユーティリティ | — |
| 5-9b | `jj run` / `jj submit` / `jj collect` への組み込み | 5-9a, 5-3/5-5 |
| 5-9c | `jj prefect up/down` コマンド | 5-9a |

---

## T6: ダッシュボード高度化

**優先度**: 中〜高
**工数目安**: 4-5セッション

### T6-1: jj parse ボタン追加

ダッシュボードのサイドバーに「Re-parse」ボタンを追加。

```python
if st.sidebar.button("🔄 Re-parse"):
    with st.spinner("Parsing..."):
        graph_service.parse_and_save()
    st.rerun()
```

**工数**: 0.5セッション

### T6-2: AgGridフィルタ高度化 + ビュー間共有

**課題**: フィルタを共有したい気持ちと独立させたい気持ちが混在

**提案: 二層フィルタモデル**

```
グローバルフィルタ（session_state）     ← 全ビューに反映
  ├── type フィルタ
  ├── active フィルタ
  └── ユーザー定義フィルタ（AgGrid由来）  ← 新規
      │
ローカルフィルタ（per-view）            ← そのビュー固有
  └── ビュー固有の絞り込み
```

**実装方針**:
- AgGridのフィルタ変更イベントをキャプチャ → `st.session_state.shared_filters` に格納
- サイドバーに「フィルタ共有: ON/OFF」トグル追加
- ON時: AgGridフィルタ変更が他ビューにも反映
- OFF時: そのビュー内のみ（現行動作）
- 共有フィルタはSavedViewConfigに保存可能

**工数**: 2セッション

### T6-3: グラフ可視化美化（version遷移・バッチ俯瞰）

**現状**: networkxのデータ構造を使用しているが、可視化はplotly/streamlitベース

**選択肢比較**:

| 手段 | 美しさ | Streamlit統合 | インタラクション |
|------|--------|--------------|----------------|
| plotly scatter + 手動レイアウト | ○ | ◎ | ○ |
| streamlit-agraph | ◎ | ◎ | ◎ |
| pyvis (HTML embed) | ◎ | ○ | ◎ |
| Streamlit Custom Component (React) | ◎◎ | ◎ | ◎◎ |
| graphviz (st.graphviz_chart) | ○ | ◎ | △ |
| d3.js (st.components.v1.html) | ◎◎ | ○ | ◎◎ |

**推奨: streamlit-agraph + フォールバックpyvis**

- `streamlit-agraph`: ノード・エッジをインタラクティブに描画。Streamlitネイティブ。物理シミュレーションでレイアウト自動調整
- フォールバック: pyvisのHTML出力を `st.components.v1.html()` で埋め込み

**Streamlitカスタムコンポーネント**:
- Streamlitは `streamlit.components.v1` でReactベースのカスタムコンポーネントを作成可能
- ただし開発・メンテコストが高い。まずは既存ライブラリで対応し、限界を感じたら検討

**工数**: 2セッション

### T6-4: GalleryDefaults二重構造の解消

status-050から据え置きの構造問題を解消。

**工数**: 0.5セッション

---

## T7: Ollama AI連携プラグイン

**優先度**: 中（可能性は大きいが設計判断が重要）
**工数目安**: 5-7セッション（段階的）

### ユーザーの要望整理

| 機能 | カテゴリ |
|------|---------|
| パワポ/エクセル/PDF要約 | ドキュメント処理 |
| 実行レポジトリの簡易RAG | 知識ベース |
| Abaqusキーワードリファレンスのマッピング | 専門知識DB |
| TODO照会・作成・管理 | タスク管理 |
| 会議の議事録音声データ文字起こし・要約 | 音声処理 |
| diff差分要約 | コード分析 |
| 有効だった対策の推測 | 知識推論 |
| tipsの抽出と分解 (`jj tips`) | 知識管理 |

### 設計判断: プラグイン分離 vs 密結合

**推奨: ハイブリッドアーキテクチャ**

```
jj コア
  ├── services/ai/              ← AI抽象レイヤー（コア内、軽量）
  │   ├── __init__.py           # AIProvider プロトコル定義
  │   ├── provider.py           # OllamaProvider, OpenAIProvider等
  │   └── prompts/              # プロンプトテンプレート
  │
  └── services/plugins/
      ├── ollama/               ← Ollama接続プラグイン
      │   ├── __init__.py       # register(), OllamaProvider実装
      │   └── config.py         # Ollama接続設定
      │
      └── ai_tools/             ← AI活用ツール群プラグイン
          ├── __init__.py
          ├── summarizer.py     # ドキュメント要約
          ├── rag.py            # 簡易RAG（プロジェクト内検索+LLM）
          ├── tips.py           # tips抽出・管理
          └── diff_analyzer.py  # diff要約
```

**理由**:

| 方針 | メリット | デメリット |
|------|---------|-----------|
| 完全分離（ollama-plugin単体） | 依存最小、インストール任意 | jjコアとの連携が薄い、データフロー断絶 |
| 密結合（コア内） | データアクセス容易、UX一貫 | ollama必須になりうる |
| **ハイブリッド** | **AIProviderプロトコルはコア、実装はプラグイン** | 設計の初期コストやや高い |

- `AIProvider` プロトコル（`chat()`, `embed()`, `summarize()`）をコアで定義
- `OllamaProvider` はプラグインとして実装（`pip install jj[ollama]`）
- 将来 OpenAI/Claude API対応も同じプロトコルで追加可能
- AIツール群はAIProvider依存だが、Provider不在時はgraceful skip

### 実装計画

| Phase | タスク | 依存 |
|-------|--------|------|
| 7-1 | `AIProvider` プロトコル定義 + OllamaProvider | — |
| 7-2 | `jj ai summarize <file>` — 単体ファイル要約 | 7-1 |
| 7-3 | `jj ai diff` — git diff / jj diff の要約 | 7-1 |
| 7-4 | 簡易RAG — プロジェクトファイルのembedding + 検索 | 7-1 |
| 7-5 | `jj tips` — tips抽出・蓄積・表示 | 7-4 |
| 7-6 | ダッシュボードAIアシスタントパネル | 7-1, T6 |
| 7-7 | 音声文字起こし連携（whisper.cpp / faster-whisper） | 7-1 |
| 7-8 | Abaqusキーワードリファレンス連携 | 7-4 |

### Ollama Config

```yaml
# .j2/config/config.yaml
ai:
  provider: ollama          # ollama | openai | disabled
  ollama:
    base_url: "http://localhost:11434"
    model: "llama3.1:8b"    # 要約・チャット用
    embed_model: "nomic-embed-text"  # RAG embedding用
  rag:
    chunk_size: 1000
    top_k: 5
    index_path: ".j2/storage/ai/rag_index/"
  tips:
    storage: ".j2/storage/ai/tips.yaml"
```

---

## T8: 汎用データ管理への昇華

**優先度**: 低〜中（設計方針の話。実装はT3, T5, T7と並行）
**工数目安**: 設計2セッション + 実装は各テーマに分散

### ビジョン

jjを「CAE専用ツール」から「数値シミュレーション・ML・実機実験を統一管理するRun中心プラットフォーム」に昇華する。M7のRun中心スキーマがまさにその基盤。

### 方針

```
現状のjj
├── CAEに強い（Abaqus特化パーサー群）
├── ML対応済み（Phase 1-4パーサー）
└── Run中心スキーマ（M7完了）

目指すjj
├── コア: Run中心の汎用データ管理
│   ├── 入力 → 実行 → 出力 の三項関係
│   ├── パラメータトレーサビリティ
│   └── バージョン管理・比較
│
├── プラグイン層: ドメイン固有
│   ├── CAE (abaqus, lsdyna, openfoam, ...)
│   ├── ML (pytorch, sklearn, optuna, ...)
│   ├── 実験 (実機試験データ取り込み)
│   └── AI (ollama, tips, RAG)
│
└── ダッシュボード: 統一UI
    ├── Run一覧・比較・DAG可視化
    ├── パラメータ探索（scatter, pareto）
    └── プラグイン固有ページ
```

### 具体アクション

| # | タスク | 関連テーマ |
|---|--------|-----------|
| 1 | プラグインテンプレートにRun発見パターンを標準化 | T3, M6 |
| 2 | 実機実験プラグインのスケルトン作成 | 新規 |
| 3 | Run比較ダッシュボードをドメイン非依存に一般化 | T6 |
| 4 | config分類（classification）の汎用化 | T2 |
| 5 | プラグイン開発ガイド更新 | ドキュメント |

---

## 実施ロードマップ

### Phase A: 基盤整理（1-2週間）

```
Week 1-2:
  T4: Deprecation Warning修正             ← すぐ着手可能
  T2: Config二層分離 Phase 2-1〜2-3       ← 最重要基盤
  T1: TODO解消（config関連 #3, #4）        ← T2と連動
  T6-1: parseボタン追加                    ← 小タスク
```

### Phase B: ワークフロー自動化（3-4週間）

```
Week 3-5:
  T5: リモートジョブ実行基盤
    5-1: フォルダマッピング
    5-2: JobStateモデル
    5-3: jj submit
    5-4: jj watch
    5-5: jj collect
    5-6: jj job status
    5-7: バッチ投入
  T1: TODO解消（残り #1, #2, #5, #6）

Week 5-6:
  T5-9: Prefect統合（事後記録パターン）
    5-9a: report_to_prefect() ユーティリティ
    5-9b: jj run/submit/collect への組み込み
    5-9c: jj prefect up/down コマンド
```

### Phase C: ダッシュボード高度化（2-3週間）

```
Week 6-8:
  T6-2: AgGridフィルタ共有
  T6-3: グラフ可視化美化（streamlit-agraph）
  T6-4: GalleryDefaults解消
  T3: M6 Phase 5 MLダッシュボード
  T5-8: Job Monitorページ
```

### Phase D: AI連携（3-4週間）

```
Week 9-12:
  T7-1: AIProviderプロトコル + OllamaProvider
  T7-2: ファイル要約
  T7-3: diff要約
  T7-4: 簡易RAG
  T7-5: jj tips
  T8: 汎用データ管理設計
```

---

## 技術選定メモ

| 領域 | 選定 | 理由 |
|------|------|------|
| グラフ可視化 | streamlit-agraph（第一候補）+ pyvisフォールバック | Streamlitネイティブ、インタラクティブ |
| AI Provider | ollama（ローカル）、将来OpenAI/Claude対応 | ユーザー環境にollama稼働中 |
| RAG embedding | nomic-embed-text (ollama) | ローカル完結、高速 |
| ジョブ実行管理 | Prefect（optional）+ YAMLフォールバック | Run中心スキーマと1:1対応、UIが美しい |
| ジョブステート | YAML（.j2/storage/jobs/） | 既存のYAMLストレージパターンに統一（Prefectなし時） |
| 音声文字起こし | whisper.cpp / faster-whisper | ローカル完結 |
| Config merge | deep merge（ユーザー優先） | シンプルで予測可能 |
| フィルタ共有 | session_state + トグル | 最小限の実装で両立 |
| 実行履歴可視化 | Prefect（optional、事後記録） | UIが美しい、常駐プロセス不要 |

---

## 未整理・将来検討

- Abaqusキーワードリファレンスの体系的URL DB構築（T7-8、要データ収集）
- エージェント化（AIが自律的にjjコマンドを組み合わせて分析）— T7完了後に検討
- ollama-abaqus-plugin のような特化プラグインの分離判断 — T7-1のプロトコル設計後に判断
- パワポ/エクセル生成 — python-pptx / openpyxl、T7のAI要約と組み合わせ
- 会議議事録 — faster-whisper + ollama要約のパイプライン、`jj ai transcribe <audio>`
