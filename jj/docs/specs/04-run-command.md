[READMEへ戻る](../../README.md)

# runコマンド層 仕様書

## 1. 概要

本ドメインは、CAEソフトやスクリプトの実行履歴をトレースし、グラフデータ化する機能を提供します。実行前後のファイル差分を検出し、入力と出力の関係を自動で記録します。

### 目的

- コマンド実行履歴の記録とトレーサビリティの確保
- 実行条件（properties）の自動抽出
- 生成ファイルとの関係をグラフ化
- 再現性の高い計算環境の構築

### 責務範囲

- `services/run/` : コマンド実行とトレース機能
- `.j2/storage/run/` : 実行ログの保存先

---

## 2. コマンド構文

### 2.1 基本形式

```bash
jj r -- <command> [args...]
```

#### 例

```bash
jj r -- python calculate.py 120 60
jj r -- abaqus job=model input=go_sample_v1_idx1.inp cpus=4
jj r -- fluent -t4 -i input.jou
```

### 2.2 オプション（将来実装）

```bash
jj r --mode=job -- abaqus job=model input=go_sample_v1_idx1.inp
jj r --no-trace -- python script.py
```

---

## 3. 実行モードの分類

### 3.1 スクリプト型（Script Mode）

#### 特徴

- 短時間（数秒〜数分）で完了する処理
- 主にPythonスクリプトやシェルスクリプト
- 実行前後のファイル差分を自動検出

#### 対象

- `python *.py`
- `bash *.sh`
- 短時間のプリ/ポスト処理

#### トレース方法

1. 実行前のプロジェクトスナップショットを取得
2. コマンドを実行
3. 実行後のプロジェクトスナップショットを取得
4. 差分から新規/変更ファイルを検出
5. `Relation(label=generated)` を作成

### 3.2 ジョブ型（Job Mode）

#### 特徴

- 長時間（数時間〜数日）かかる処理
- CAE計算本体（Abaqus, Fluent, Dynaなど）
- 生成ファイルをソフト固有のルールで予測

#### 対象

- `abaqus job=...`
- `fluent -t4 -i ...`
- `ls-dyna i=...`

#### トレース方法

1. 入力ファイルとコマンドライン引数を解析
2. ソフト固有のルールで生成ファイルを予測
3. 実行完了後、予測ファイルの存在を確認
4. `Relation(label=generated)` を作成

---

## 4. 実行ログの記録

### 4.1 ログ保存先

```
.j2/storage/run/run-<timestamp>.json
```

#### 例

```
.j2/storage/run/run-2026-02-04-120000.json
```

### 4.2 ログフォーマット

```json
{
  "id": "run-2026-02-04-120000",
  "mode": "script",
  "command": "python calculate.py 120 60",
  "script_path": "/path/to/calculate.py",
  "start_time": "2026-02-04T12:00:00",
  "end_time": "2026-02-04T12:02:05",
  "duration": 125.3,
  "user": "username",
  "host": "server01",
  "properties": {
    "time_limit": "120",
    "step_size": "60"
  },
  "generated_files": [
    "result_v1_idx1.csv",
    "output_v1_idx1.dat"
  ],
  "exit_code": 0
}
```

### 4.3 Node生成

実行ログは `Node(type=run)` として保存されます。

```python
Node(
    id=1001,
    type="run",
    name="run-2026-02-04-120000",
    format=None,
    properties={
        "mode": "script",
        "duration": 125.3,
        "user": "username",
        "host": "server01",
        "time_limit": "120",
        "step_size": "60",
    }
)
```

---

## 5. properties抽出

### 5.1 スクリプト型のproperties抽出

#### 対応方針

**決まったファイルフォーマットのもののみに対応します。**

- 対応フォーマット: Python (`.py`), Bash (`.sh`)
- 上記以外のファイルフォーマット（Perl, Ruby等）は、コメント記法が明確でない場合はスキップします
- フォーマットが対応していなければ、properties抽出は行わず、実行履歴のみを記録します

#### 抽出元

1. **コメント記法**: スクリプト内の特定コメント区間
2. **コマンドライン引数**: `sys.argv` や `$1` への割り当て

#### コメント記法の仕様

スクリプト内に以下のコメント区間を設ける:

```python
# props start
time_limit = 120
step_size = 60
# props end

import sys
time_limit = int(sys.argv[1])
step_size = int(sys.argv[2])
```

#### 抽出ルール

- `# props start` と `# props end` の間の `変数名 = 値` を抽出
- `sys.argv[N]` に割り当てられた変数名を取得し、コマンドライン引数と対応付け

#### 抽出例

**スクリプト（calculate.py）**:
```python
# props start
# time_limit: 計算時間上限（秒）
# step_size: ステップサイズ（秒）
# props end

import sys
time_limit = int(sys.argv[1])
step_size = int(sys.argv[2])
```

**実行コマンド**:
```bash
jj r -- python calculate.py 120 60
```

**抽出されるproperties**:
```python
{
    "time_limit": "120",
    "step_size": "60"
}
```

### 5.2 ジョブ型のproperties抽出

#### 抽出元

1. **コマンドライン引数**: `cpus=4`, `memory=8G` など
2. **入力ファイルのパース**: ソフト固有の設定値

#### 抽出例（Abaqus）

**実行コマンド**:
```bash
jj r -- abaqus job=model input=go_sample_v1_idx1.inp cpus=4 memory=8
```

**抽出されるproperties**:
```python
{
    "job": "model",
    "input": "go_sample_v1_idx1.inp",
    "cpus": "4",
    "memory": "8"
}
```

---

## 6. ファイル差分検出

### 6.1 スクリプト型の差分検出

#### 検出方針

**タイムスタンプ（mtime）ベースの差分検出を行います。**

- ファイルの中身は開かず、タイムスタンプが更新されていることをトリガーに判定します
- ハッシュ値の計算やファイル内容の比較は行いません（パフォーマンス重視）
- タイムスタンプが更新されていれば「変更あり」として扱います

#### 検出手順

1. **実行前スナップショット**: プロジェクト内の全ファイルパスとmtimeを記録
2. **コマンド実行**: スクリプトを実行
3. **実行後スナップショット**: 再度全ファイルを走査
4. **差分検出**:
   - 新規ファイル: 実行前に存在しなかったファイル
   - 変更ファイル: mtimeが更新されたファイル（ファイル内容は開かない）

#### 除外対象

以下のファイル/ディレクトリは差分検出から除外:

- `.j2/`
- `.git/`
- `__pycache__/`
- `*.pyc`
- `.DS_Store`

### 6.2 ジョブ型の生成ファイル予測

#### Abaqusの場合

入力ファイルが `go_sample_v1_idx1.inp` の場合、以下のファイルが生成されると予測:

- `model.odb`
- `model.dat`
- `model.msg`
- `model.sta`
- `model.log`

#### Fluentの場合

入力ファイルが `input.cas.h5` の場合、以下のファイルが生成されると予測:

- `output.dat.h5`
- `convergence.out`

---

## 7. 既存submit機能のリファクタリング

### 7.1 現状

- `services/ssh/submit.py` にAbaqus投入機能が実装済み
- SSH経由でサーバーにジョブを投入

### 7.2 リファクタリング方針

1. `submit` 機能を `run --mode=job --remote` に統合
2. SSH経由の実行も `run` コマンドで統一
3. リモート実行ログも `.j2/storage/run/` に保存

### 7.3 実装計画

#### Phase 1: ローカル実行の完成（直近）

- [x] スクリプト型の基本実装
- [x] 実行ログの保存
- [x] メタ情報（duration, user, host）の記録
- [ ] properties抽出の拡張（コメント記法の完全対応）
- [ ] ファイル差分検出の実装

#### Phase 2: ジョブ型の実装（中期）

- [ ] ジョブ型の基本実装
- [ ] Abaqusアダプターの実装
- [ ] 生成ファイル予測機能
- [ ] 実行ログのGraphStorageへの反映

#### Phase 3: リモート実行の統合（中期）

- [ ] `--remote` オプションの実装
- [ ] SSH経由の実行
- [ ] 既存submit機能の移行
- [ ] リモートログの同期

---

## 8. GraphStorageへの反映

### 8.1 Node生成

実行ログは `Node(type=run)` として `GraphStorage` に追加されます。

### 8.2 Relation生成

生成されたファイルとの関係を `Relation(label=generated)` で記録します。

#### 例

**実行コマンド**:
```bash
jj r -- python calculate.py 120 60
```

**生成されたファイル**:
- `result_v1_idx1.csv`
- `output_v1_idx1.dat`

**グラフ構造**:
```
Node(id=1001, type="run", name="run-2026-02-04-120000")
  ↓ (generated)
Node(id=2001, type="file", name="result_v1_idx1.csv")
Node(id=2002, type="file", name="output_v1_idx1.dat")
```

---

## 9. 実装計画

### Phase 1: スクリプト型の基本実装（完了）

- [x] `jj r -- <command>` の実行
- [x] 実行ログの保存
- [x] メタ情報（duration, user, host, script_path）の記録
- [x] 単体テスト

### Phase 2: properties抽出の拡張（直近）

- [ ] コメント記法（`# props start` - `# props end`）の実装
- [ ] `sys.argv` 解析の実装（Python）
- [ ] Bash変数（`$1`, `$2`）の解析（Bash）
- [ ] 対応フォーマット（Python, Bash）の完全実装

### Phase 3: ファイル差分検出（直近）

- [ ] 実行前後のスナップショット機能
- [ ] 差分検出ロジックの実装
- [ ] 除外ルールの設定
- [ ] `Relation(label=generated)` の自動生成

### Phase 4: ジョブ型の実装（中期）

- [ ] `--mode=job` オプションの実装
- [ ] Abaqusアダプターの実装
- [ ] 生成ファイル予測機能
- [ ] ジョブ型の単体テスト

### Phase 5: リモート実行の統合（中期）

- [ ] `--remote` オプションの実装
- [ ] SSH経由の実行
- [ ] 既存submit機能の移行

---

## 10. 設計上の注意事項

### 10.1 パフォーマンス

- 大量ファイル（10,000件以上）のスナップショット取得は並列化
- mtimeのみを記録し、ファイル内容のハッシュ化は行わない

### 10.2 エラーハンドリング

- コマンドの実行失敗時も実行ログを保存
- `exit_code` を記録してエラー状況を追跡可能に

### 10.3 セキュリティ

- リモート実行時のSSH鍵の取り扱いに注意
- 実行ログに秘密情報を含めない

---

## 11. テスト方針

### 単体テスト（pytest）

- `tests/services/test_run.py` : RunServiceの各機能テスト

### テストケース例

- スクリプト型の基本実行
- properties抽出の正確性
- ファイル差分検出の正確性
- ジョブ型の生成ファイル予測
- 実行失敗時のログ記録
- リモート実行の動作

---

## 12. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| コアデータモデル層 | ← runコマンド層 | 実行履歴をNode/Relationとして保存 |
| 設定管理層 | ← runコマンド層 | SSH設定を取得 |
| パーサー層 | ← runコマンド層 | 生成ファイルをパースしてNode化 |
| アダプター層 | → runコマンド層 | ソフト固有の実行ロジックを提供 |

---

## 13. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [設定管理層仕様書](./03-config.md)
