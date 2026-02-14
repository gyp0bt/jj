[READMEへ戻る](../../README.md)

# status-046: warning/error重複排除、cpu_time修正、results info-only、Obsidian directory修正

**日付**: 2026-02-10

## 概要

6つの改善を実施:
1. **warning/errorリストの重複排除**: msg/sta/datから抽出したwarning/errorの数値正規化重複排除
2. **cpu_time/wallclock_time修正**: parse_dat_fileで最後のマッチを取得（最終JOB TIME SUMMARY採用）
3. **jj info表示改善**: プロパティをYAML形式でそのまま出力
4. **results/ info-only**: results/ディレクトリ内ファイルのNode化除外（情報のみ読み取り）
5. **Obsidian export directory修正**: directoryノードの実ファイルリンクを除外
6. **.dat warning/error抽出**: .datファイルからもwarning/errorを抽出しinpに伝搬

テスト445件パス（前回比+2件）、0件失敗、20スキップ。

## 変更内容

### 1. warning/errorリストの重複排除

**背景**: msg/sta/datファイルから抽出したwarning/errorリストに大量の重複が存在。数値のみが異なるメッセージ（例: "THE SYSTEM MATRIX HAS 289 NEGATIVE EIGENVALUES." と "THE SYSTEM MATRIX HAS 6 NEGATIVE EIGENVALUES."）も実質同一。

**実装**:
- `_normalize_numbers(text)`: メッセージ中の数値を`{N}`プレースホルダに置換
- `_deduplicate_messages(messages)`: 正規化後の文字列で重複判定し初出のみ保持
- `parse_sta_file()`, `parse_msg_file()`, `parse_dat_file()` の各関数に適用

**例**:
```
入力（重複あり）:
- THE SYSTEM MATRIX HAS 289 NEGATIVE EIGENVALUES.
- CONVERGENCE JUDGED UNLIKELY.  INCREMENT WILL BE ATTEMPTED AGAIN
- THE SYSTEM MATRIX HAS 6 NEGATIVE EIGENVALUES.
- CONVERGENCE JUDGED UNLIKELY.  INCREMENT WILL BE ATTEMPTED AGAIN

出力（重複排除後）:
- THE SYSTEM MATRIX HAS 289 NEGATIVE EIGENVALUES.
- CONVERGENCE JUDGED UNLIKELY.  INCREMENT WILL BE ATTEMPTED AGAIN
```

### 2. cpu_time/wallclock_time修正

**背景**: Abaqus .datファイルには複数のJOB TIME SUMMARYセクションがある（初期化フェーズ＋解析実行）。`re.search()`は最初のマッチ（初期化の小さい値）を返していた。

**修正**: `re.search()` → `re.findall()` に変更し、最後のマッチ（最終解析結果）を採用。

```python
# 修正前: 最初のマッチ（初期化フェーズの値）
cpu_match = re.search(rf"TOTAL\s+CPU\s+TIME...", content)

# 修正後: 全マッチ取得し最後の値（最終解析結果）
cpu_matches = re.findall(rf"TOTAL\s+CPU\s+TIME...", content)
if cpu_matches:
    result["cpu_time"] = float(cpu_matches[-1])
```

### 3. jj info表示改善

**背景**: `_run_info()`がプロパティをカスタムフォーマットで整形していたが、yamlソースをそのまま表示する方が望ましい。

**修正**: `yaml.safe_dump()`を使用してプロパティをYAML形式で出力。メッシュ統計の専用セクション(`_print_mesh_stats_section`)は除去し、yaml出力に統合。

### 4. results/ info-only

**背景**: results/ディレクトリ内のファイル（例: `results/go_idx0.v29_stress.json`）は、JsonPropertyParser(priority=33)で情報がgo_*.inpに伝搬済み。Node自体はグラフに不要。

**実装**: `EnrichmentOnlyFilter`(priority=99)で`results/`ディレクトリ内のファイルノードも除外対象に追加。

- `_INFO_ONLY_DIRECTORIES`: info-onlyディレクトリ名のfrozenset（`{"results"}`）
- `_is_in_info_only_directory()`: パスがinfo-onlyディレクトリ内かを判定

**データフロー**:
1. `scan_files()` → results/内ファイルもスキャン
2. `file_to_node()` → Node生成
3. `JsonPropertyParser`(priority=33) → JSON読み取り、go_*.inpに割り当て
4. `EnrichmentOnlyFilter`(priority=99) → results/内ファイルNodeを除去

### 5. Obsidian export directory修正

**背景**: directoryタイプのノードのマークダウン出力に実ファイルリンク（`[[path|name]]`）が含まれていたが、ディレクトリに対しては不適切。

**修正**: `_format_md()`で`node.format == "directory"`の場合は実ファイルリンクを出力しない。

### 6. .dat warning/error抽出

**追加**: `parse_dat_file()`で`***WARNING:`/`***ERROR:`パターンも抽出。`_enrich_dat_status()`でdat_warnings/dat_errorsをinpノードに伝搬。

## 変更ファイル一覧

| ファイル | 変更種別 |
|---------|---------|
| `services/parse/connectors/abaqus/result_parser.py` | 変更: 重複排除関数追加、cpu_time最後マッチ、dat warning/error抽出 |
| `services/parse/parsers/enrichment_filter.py` | 変更: results/ディレクトリinfo-only追加 |
| `services/cli/graph.py` | 変更: jj infoのYAML出力化 |
| `services/export/connectors/obsidian/__init__.py` | 変更: directory実ファイルリンク除外 |
| `tests/test_graph_feature.py` | 変更: results/Node化除外テストに更新 |
| `tests/test_parser_pipeline.py` | 変更: has_output, results除外, JSON伝搬テスト追加 |

## テスト結果

```
445 passed, 0 failed, 20 skipped
```

- ユニットテスト: 全パス
- グラフ機能テスト: 全パス（results/除外テスト追加）
- Obsidianコネクタテスト: 全パス
- パイプラインテスト: 全パス（+2件追加: results除外, JSON伝搬テスト）

## TODO / 次のステップ

- [ ] Phase 2: グラフ機能の仕上げ（roadmap参照）
- [ ] Phase 2.5: ダッシュボード・API基盤
- [ ] SubmitServiceの統合テスト追加
- [ ] InfoServiceの単体テスト追加
- [ ] results/以外のinfo-onlyディレクトリの設定化（現在はハードコード）

## 確認事項

- `results/`ディレクトリのinfo-only設定は現在`_INFO_ONLY_DIRECTORIES`にハードコード。将来的にconfig.yaml(`info-only-directories`)で設定可能にすることを検討。
- `.dat`ファイルのwarning/error抽出を追加したが、AbaqusIncludePropertyParser(priority=86)でdat_warnings/dat_errorsの伝搬キーも追加が必要な場合がある。
