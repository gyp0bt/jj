[READMEへ戻る](../../README.md)

# 実装状況 (status-012)

## 概要

status-011のTODO項目を分析し、設計方針を決定しました。

## 変更点

### 1. TODOの分析と回答

status-011に記載されていた3つの確認事項について、仕様書を精査し、プロジェクトの実装優先度と実用性を考慮して回答を作成しました。

## TODO分析結果

### TODO 1: properties抽出の対応フォーマットとして、他に必要な言語はあるか?

#### 現状の対応
- Python (`.py`)
- Bash (`.sh`)

#### 検討結果
CAE業務で使用される可能性がある言語を検討しました：

**優先度: 高**
- **Tcl/Tk**: Abaqus、ANSYS、Hypermeshなどで広く使用されるスクリプト言語
  - コメント記法: `# props start` - `# props end`（Pythonと同じ）
  - 変数: `set time_limit [lindex $argv 0]`
  - Phase 2での追加を推奨

**優先度: 中**
- **Perl**: レガシーなCAEワークフローで使用されることがある
  - コメント記法: `# props start` - `# props end`
  - 変数: `my $time_limit = $ARGV[0]`
  - 需要に応じて追加を検討

**優先度: 低**
- Ruby, その他のスクリプト言語

#### 結論
- **Phase 1では Python, Bash のみに対応する方針で問題なし**
- Tclは需要が高いため、**Phase 2で追加を検討**
- Perl, Rubyなどは需要が明確になった段階で追加

---

### TODO 2: スナップショット比較で、タイムスタンプだけでは不十分なケースはあるか?

#### 現状の方針
- mtimeベースの差分検出
- ファイル内容は開かない（パフォーマンス重視）
- タイムスタンプが更新されていれば「変更あり」として扱う

#### タイムスタンプのみでは不十分なケース

**ケース1: バックアップからの復元**
- バックアップツールがmtimeを保持したまま復元した場合、変更を検出できない
- **発生頻度**: 非常にレア
- **影響**: CAE業務では通常、実行中にバックアップ復元は行わない

**ケース2: mtimeの精度問題**
- 一部のファイルシステムでは秒単位の精度しかない
- 同じ秒内での複数回の変更は検出できない可能性
- **発生頻度**: レア（CAE計算は通常数秒以上かかる）
- **影響**: 実用上ほぼ問題なし

**ケース3: 内容が変わらない書き込み**
- ファイルを開いて書き込んでも内容が同じ場合
- mtimeは更新されるので「変更あり」として検出される
- **影響**: 偽陽性（false positive）だが、安全側に倒れるため問題なし

#### ハッシュベース比較の導入検討

**メリット**:
- ファイル内容の実際の変更を正確に検出
- 偽陽性を回避

**デメリット**:
- 大量ファイル（10,000件以上）でのパフォーマンス低下
- 実装の複雑化
- CAE業務での実用的な必要性は低い

#### 結論
- **Phase 1では mtime ベースのみで十分に実用的**
- CAE計算は通常数秒〜数時間かかるため、mtimeの精度問題はほぼ発生しない
- 問題が実際に発生した場合にのみ、**Phase 3以降でハッシュ比較をオプションとして追加を検討**
- パフォーマンス重視の方針を維持

---

### TODO 3: .jj/configの初期化タイミングとして、他に必要なタイミングはあるか?

#### 現状の方針
- `.jj/config/` フォルダが存在しない場合のみ自動初期化
- フォルダが既に存在する場合は初期化処理をスキップ
- 既存設定は上書きしない

#### 他の初期化タイミング候補

**1. 明示的な初期化コマンド**
```bash
jj config init
jj config init --force  # 既存設定を上書き
```
- **用途**: ユーザーが意図的に設定を初期化したい場合
- **優先度**: 中（Phase 2以降で検討）
- **実装タイミング**: Phase 2（設定管理層の拡張）

**2. 自動初期化のトリガー**
- `jj n` 初回実行時（既に計画済み）
- `jj r` 初回実行時（設定が必要な場合）
- `jj f` 初回実行時（設定が必要な場合）
- **優先度**: 高（Phase 1で `jj n` のみ対応、他はPhase 2）

**3. テンプレートベースの初期化**
```bash
jj config init --template abaqus
jj config init --template fluent
jj config init --template dyna
```
- **用途**: ソフト固有の設定テンプレートを適用
- **優先度**: 低（Phase 3以降で検討）
- **実装タイミング**: Phase 3（設定管理層の高度な機能）

**4. 設定のリセット**
```bash
jj config reset
jj config reset --keep-ssh  # SSH設定は保持
```
- **用途**: 設定を初期状態に戻す
- **優先度**: 低（Phase 3以降で検討）

#### 結論
- **Phase 1では「フォルダが存在しない場合のみ自動初期化」で十分**
- Phase 2以降で `jj config init` コマンドの追加を検討
- Phase 3以降でテンプレート機能、リセット機能の追加を検討
- 既存設定の保護を最優先（誤操作による設定喪失を防ぐ）

---

## 実装方針の確定

上記の分析結果を踏まえ、以下の方針で実装を進めます。

### Phase 1（直近）: 基盤整備

1. **設定管理層の統合**
   - `vocab.yaml`, `extensions.yaml`, `prefixes.yaml` の読込実装
   - Pydanticモデルの定義
   - `.jj/config/` の初期化処理（フォルダが存在しない場合のみ）
   - 対応言語: Python, Bash

2. **runコマンド層のproperties抽出拡張**
   - コメント記法（`# props start` - `# props end`）の実装
   - `sys.argv` 解析の実装（Python）
   - Bash変数（`$1`, `$2`）の解析（Bash）
   - 対応言語: Python, Bash のみ

3. **runコマンド層のファイル差分検出**
   - 実行前後のスナップショット機能（mtimeベース）
   - 差分検出ロジックの実装（タイムスタンプのみ）
   - 除外ルールの設定
   - `Relation(label=generated)` の自動生成

4. **コアデータモデル層の拡張**
   - グラフマージ機能
   - ノード/関係の更新・削除機能
   - トランザクション管理

### Phase 2（中期）: 機能拡張

- Tcl対応の追加検討
- `jj config init` コマンドの実装
- ジョブ型実装
- noteコマンドの実行履歴統合

### Phase 3（長期）: 高度な機能

- ハッシュベースの差分検出オプション（必要に応じて）
- 設定テンプレート機能
- Perl, Ruby対応の検討

---

## 次の担当者へ

### 今回の成果

status-011のTODOに対して、以下の方針を決定しました：

1. **properties抽出**: Phase 1では Python, Bash のみ対応（Tclは Phase 2で検討）
2. **スナップショット比較**: mtimeベースで十分（ハッシュ比較は Phase 3で検討）
3. **.jj/config初期化**: 自動初期化のみで十分（明示的なコマンドは Phase 2で検討）

### 次のタスク

Phase 1の実装を開始してください。優先順位は以下の通りです：

#### 優先度1: 設定管理層の統合

現在実装されていない設定ファイルの読込機能を実装します。

- [ ] `config/config_loader.py` の拡張
  - `load_vocab()` メソッドの実装
  - `load_extensions()` メソッドの実装
  - `load_prefixes()` メソッドの実装
- [ ] `types/config.py` にPydanticモデルを追加
  - `VocabConfig` モデル
  - `ExtensionsConfig` モデル
  - `PrefixesConfig` モデル
- [ ] `.jj/config/` の初期化処理
  - 初期化関数の実装（`init_config_dir()`）
  - デフォルト設定ファイルの生成
  - フォルダ存在チェックの実装
- [ ] 単体テストの追加
  - `tests/config/test_config_loader.py`

**参照**: [03-config.md](../specs/03-config.md)

#### 優先度2: runコマンド層のproperties抽出拡張

コメント記法とコマンドライン引数の解析を実装します。

- [ ] Pythonスクリプトの解析
  - `# props start` - `# props end` の検出
  - `sys.argv` 解析の実装
- [ ] Bashスクリプトの解析
  - `# props start` - `# props end` の検出
  - `$1`, `$2` 等の変数解析
- [ ] 単体テストの追加
  - `tests/services/test_run_properties.py`

**参照**: [04-run-command.md](../specs/04-run-command.md#5-properties抽出)

#### 優先度3: runコマンド層のファイル差分検出

スナップショット機能と差分検出を実装します。

- [ ] スナップショット機能の実装
  - 実行前スナップショット（mtime記録）
  - 実行後スナップショット（mtime記録）
- [ ] 差分検出ロジック
  - 新規ファイルの検出
  - 変更ファイルの検出（mtimeベース）
  - 除外ルールの適用
- [ ] グラフへの反映
  - `Relation(label=generated)` の自動生成
- [ ] 単体テストの追加
  - `tests/services/test_run_snapshot.py`

**参照**: [04-run-command.md](../specs/04-run-command.md#6-ファイル差分検出)

### 文書の更新ルール

- 実装完了時は `docs/status/status-013.md` を作成し、変更内容を記録
- `docs/roadmap.md` のチェックボックスを更新
- `README.md` の最新ステータスを更新

---

## コミット

以下のコミットメッセージを使用してください:

```
docs: analyze status-011 TODOs and finalize implementation policies

- properties抽出: Phase 1では Python, Bash のみ対応と決定
- Tclは Phase 2での追加を推奨
- スナップショット比較: mtimeベースで十分と判断
- ハッシュ比較は Phase 3でオプションとして検討
- .jj/config初期化: 自動初期化のみで十分と決定
- 明示的な初期化コマンドは Phase 2で検討
- Phase 1の実装タスクを明確化

https://claude.ai/code/session_01VstrP4Ta3vW5aBVqjPHkTD
```

---

## 参考資料

- [機能ドメイン別仕様書](../specs/README.md)
- [ロードマップ](../roadmap.md)
- [実装詳細](../detail.md)
- [前回のステータス](./status-011.md)
- [runコマンド層仕様書](../specs/04-run-command.md)
- [設定管理層仕様書](../specs/03-config.md)
