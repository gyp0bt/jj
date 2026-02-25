[READMEへ戻る](../../README.md)

# 実装状況 (status-011)

## 概要

- statusファイルのインデックスを010表記（ゼロパディング）に変更
- 仕様書の方針を明確化（properties抽出、スナップショット比較、.j2/config初期化）
- プロジェクト全体の参照を更新

## 変更点

### 1. statusファイルのインデックス変更

statusファイルのファイル名を010表記に統一しました。

**変更内容:**
- `status-1.md` → `status-001.md`
- `status-2.md` → `status-002.md`
- ...
- `status-10.md` → `status-010.md`

**更新ファイル:**
- 全てのstatusファイル（status-001.md 〜 status-010.md）
- README.md
- docs/roadmap.md
- docs/specs/README.md
- 各statusファイル内の相互参照

### 2. 仕様書の方針明確化

#### 2.1 properties抽出の方針

`docs/specs/04-run-command.md` の「5. properties抽出」セクションを更新しました。

**明確化した方針:**
- 決まったファイルフォーマットのもののみに対応
- 対応フォーマット: Python (`.py`), Bash (`.sh`)
- 上記以外のファイルフォーマット（Perl, Ruby等）は、コメント記法が明確でない場合はスキップ
- フォーマットが対応していなければ、properties抽出は行わず、実行履歴のみを記録

**関連更新:**
- `docs/specs/04-run-command.md` の Phase 2実装計画
- `docs/roadmap.md` の Phase 1 「3. runコマンド層のproperties抽出拡張」

#### 2.2 スナップショット比較の方針

`docs/specs/04-run-command.md` の「6. ファイル差分検出」セクションを更新しました。

**明確化した方針:**
- タイムスタンプ（mtime）ベースの差分検出を行う
- ファイルの中身は開かず、タイムスタンプが更新されていることをトリガーに判定
- ハッシュ値の計算やファイル内容の比較は行わない（パフォーマンス重視）
- タイムスタンプが更新されていれば「変更あり」として扱う

#### 2.3 .j2/config初期化の方針

`docs/specs/03-config.md` の「4. 初期化とデフォルト設定」セクションを更新しました。

**明確化した方針:**
- `.j2/config/` フォルダが存在しない場合のみ初期化を実行
- フォルダが既に存在する場合は、初期化処理をスキップ
- 既存の設定ファイルは上書きしない

## 次の担当者へ

### 実装優先度（Phase 1: 基盤整備）

引き続き、以下の順で実装を進めてください:

1. **設定管理層の統合**
   - `vocab.yaml`, `extensions.yaml`, `prefixes.yaml` の読込実装
   - Pydanticモデルの定義
   - `.j2/config/` の初期化処理（フォルダが存在しない場合のみ）
   - 参照: `docs/specs/03-config.md`

2. **runコマンド層のproperties抽出拡張**
   - コメント記法（`# props start` - `# props end`）の実装
   - `sys.argv` 解析の実装（Python）
   - Bash変数（`$1`, `$2`）の解析（Bash）
   - 対応フォーマット（Python, Bash）のみサポート
   - 参照: `docs/specs/04-run-command.md#5-properties抽出`

3. **runコマンド層のファイル差分検出**
   - 実行前後のスナップショット機能（mtimeベース）
   - 差分検出ロジックの実装（ファイル内容は開かない）
   - 除外ルールの設定
   - `Relation(label=generated)` の自動生成
   - 参照: `docs/specs/04-run-command.md#6-ファイル差分検出`

4. **コアデータモデル層の拡張**
   - グラフマージ機能
   - ノード/関係の更新・削除機能
   - トランザクション管理
   - 参照: `docs/specs/01-core-data-model.md#4-実装計画`

### 文書の更新ルール

- 実装完了時は `docs/status/status-012.md` を作成し、変更内容を記録。
- `docs/roadmap.md` のチェックボックスを更新。
- `README.md` の最新ステータスを更新。

### 設計上の懸念事項

今回の方針変更により、以下の点が明確になりました:

1. **properties抽出の対応範囲**
   - Python, Bashのみに対応することで、実装の複雑さを抑制
   - 他の言語（Perl, Ruby等）は今後の需要に応じて追加検討

2. **ファイル差分検出のパフォーマンス**
   - mtimeベースの判定により、大量ファイルでも高速に動作可能
   - ファイル内容のハッシュ化は行わないため、パフォーマンス重視

3. **設定管理の初期化タイミング**
   - `.j2/config/` の存在チェックにより、既存設定を保護
   - 初回実行時のみ自動生成、以降は手動更新を前提

## TODO

以下の確認事項があれば、statusファイルに追記してください：

- [ ] properties抽出の対応フォーマットとして、他に必要な言語はあるか？
- [ ] スナップショット比較で、タイムスタンプだけでは不十分なケースはあるか？
- [ ] .j2/configの初期化タイミングとして、他に必要なタイミングはあるか？

## コミット

次のコミット時には以下のメッセージを使用してください:

```
chore: update status file indexing to 010 format and clarify spec policies

- statusファイルを010表記に変更（status-1.md → status-001.md等）
- 全ての参照を更新（README.md、roadmap.md、各statusファイル）
- properties抽出: 決まったフォーマット（Python, Bash）のみ対応に明確化
- スナップショット比較: タイムスタンプベース、ファイル内容は開かないと明記
- .j2/config初期化: フォルダが存在する場合はスキップすると明記

https://claude.ai/code/session_01CZyeWi378A7w6qrob47Edu
```

## 参考資料

- [機能ドメイン別仕様書](../specs/README.md)
- [ロードマップ](../roadmap.md)
- [実装詳細](../detail.md)
- [前回のステータス](./status-010.md)
