[READMEへ戻る](../../README.md)

# 設定管理層 仕様書

## 1. 概要

本ドメインは、プロジェクト固有の設定を一元管理し、各ドメインから参照可能にする機能を提供します。語彙マッピング、SSH接続情報、ソフト固有の設定などを統一的に扱います。

### 目的

- プロジェクトごとの設定を `.j2/config/` に集約
- SSH接続情報（`.pyssh.yaml`）の読込と管理
- 語彙マッピング（`vocab.yaml`）の提供
- ソフト固有設定（拡張子、接頭辞など）の集約

### 責務範囲

- `config/` : 設定ローダーと設定モデル
- `.j2/config/` : プロジェクト固有設定の保存先

---

## 2. 設定ファイルの種類

### 2.1 vocab.yaml（語彙マッピング）

プロジェクト固有の用語や略語を統一的に管理します。

#### 配置場所

```
.j2/config/vocab.yaml
```

#### フォーマット

```yaml
# プロパティ名の正規化
properties:
  ncpu: "CPU数"
  mem: "メモリ使用量(GB)"
  time: "計算時間(秒)"

# タグの正規化
tags:
  abq: "Abaqus"
  flu: "Fluent"
  dyn: "LS-DYNA"

# ファイルタイプの説明
file_types:
  calculation_input: "計算入力ファイル"
  mesh: "メッシュファイル"
  material: "材料定義ファイル"
  step: "ステップ定義ファイル"
```

#### 用途

- Obsidianノート生成時の説明文
- レポート生成時の可読性向上
- ユーザーへの情報提示

### 2.2 .pyssh.yaml（SSH接続情報）

SSH接続先のホスト情報を管理します。

#### 配置場所

```
.pyssh.yaml（プロジェクトルート）
```

#### フォーマット

```yaml
hosts:
  server01:
    hostname: server01.example.com
    user: username
    port: 22
    key_file: ~/.ssh/id_rsa
  server02:
    hostname: 192.168.1.100
    user: admin
    port: 2222
```

#### 用途

- `jj f` コマンドでのファイル送受信
- リモートでのコマンド実行

### 2.3 extensions.yaml（拡張子設定）

ソフト固有の拡張子マッピングを管理します。

#### 配置場所

```
.j2/config/extensions.yaml
```

#### フォーマット

```yaml
# 計算入力ファイルの拡張子
calculation_input:
  - .inp     # Abaqus
  - .cas.h5  # Fluent
  - .k       # LS-DYNA
  - .key     # LS-DYNA
  - .dat     # Generic

# メッシュファイルの拡張子
mesh:
  - .cdb     # ANSYS
  - .msh     # Fluent
  - .unv     # Universal

# 複数ドット拡張子（優先判定）
multi_dot:
  - .cas.h5
  - .dat.h5
  - .tar.gz
  - .tar.bz2
  - .tar.xz
```

#### 用途

- パーサー層での拡張子判定
- ファイルタイプの自動判別

### 2.4 prefixes.yaml（接頭辞設定）

ファイル名の接頭辞とファイルタイプのマッピングを管理します。

#### 配置場所

```
.j2/config/prefixes.yaml
```

#### フォーマット

```yaml
prefixes:
  go_: calculation_input
  mesh_: mesh
  material_: material
  step_: step
  post_: postprocess
  result_: output
```

#### 用途

- パーサー層でのファイルタイプ判別
- ファイルグループ化

---

## 3. 設定ローダー

### 3.1 ConfigLoaderインターフェース

#### メソッド一覧

| メソッド | 戻り値 | 説明 |
|---------|-------|------|
| `load_vocab()` | `VocabConfig` | vocab.yamlを読み込み |
| `load_ssh()` | `SSHConfig` | .pyssh.yamlを読み込み |
| `load_extensions()` | `ExtensionsConfig` | extensions.yamlを読み込み |
| `load_prefixes()` | `PrefixesConfig` | prefixes.yamlを読み込み |
| `get_config_dir()` | `Path` | `.j2/config/` のパスを取得 |

### 3.2 設定モデル（Pydantic）

#### VocabConfig

```python
from pydantic import BaseModel

class VocabConfig(BaseModel):
    properties: dict[str, str] = {}
    tags: dict[str, str] = {}
    file_types: dict[str, str] = {}
```

#### SSHConfig

```python
class SSHHost(BaseModel):
    hostname: str
    user: str
    port: int = 22
    key_file: str | None = None

class SSHConfig(BaseModel):
    hosts: dict[str, SSHHost] = {}
```

#### ExtensionsConfig

```python
class ExtensionsConfig(BaseModel):
    calculation_input: list[str] = []
    mesh: list[str] = []
    multi_dot: list[str] = []
```

#### PrefixesConfig

```python
class PrefixesConfig(BaseModel):
    prefixes: dict[str, str] = {}
```

---

## 4. 初期化とデフォルト設定

### 4.1 `.j2/config/` の初期化

プロジェクト初回実行時に `.j2/config/` ディレクトリとデフォルト設定を自動生成します。

#### 初期化条件

**`.j2/config/` フォルダが存在しない場合のみ初期化を実行します。**

- フォルダが既に存在する場合は、初期化処理をスキップします
- 既存の設定ファイルは上書きしません

#### 生成タイミング

- `jj n` 初回実行時（`.j2/config/` が存在しない場合）
- `jj init` コマンド実行時（将来実装、`.j2/config/` が存在しない場合）

#### デフォルトファイル

- `vocab.yaml` : 空の辞書
- `extensions.yaml` : 基本的な拡張子セット
- `prefixes.yaml` : 基本的な接頭辞マッピング

### 4.2 デフォルト設定の埋め込み

設定ファイルが存在しない場合、コード内にハードコードされたデフォルト値を使用します。

#### 実装例

```python
DEFAULT_EXTENSIONS = {
    "calculation_input": [".inp", ".cas.h5", ".k", ".key", ".dat"],
    "mesh": [".cdb", ".msh", ".unv"],
    "multi_dot": [".cas.h5", ".dat.h5", ".tar.gz"],
}

DEFAULT_PREFIXES = {
    "go_": "calculation_input",
    "mesh_": "mesh",
    "material_": "material",
    "step_": "step",
}
```

---

## 5. 設定の優先順位

複数の設定ソースが存在する場合、以下の優先順位で適用されます。

1. プロジェクト固有設定（`.j2/config/`）
2. コードのデフォルト設定
3. コマンドライン引数（将来実装）

---

## 6. 実装計画

### Phase 1: 基本設定読込（完了）

- [x] `.pyssh.yaml` の読込機能
- [x] `SSHConfig` モデルの定義

### Phase 2: プロジェクト設定の統合（直近）

- [ ] `vocab.yaml` の読込機能
- [ ] `extensions.yaml` の読込機能
- [ ] `prefixes.yaml` の読込機能
- [ ] 各設定モデルの定義
- [ ] `.j2/config/` の初期化処理

### Phase 3: 設定の拡張（中期）

- [ ] 設定ファイルのバリデーション
- [ ] 設定エディタ機能（`jj config edit`）
- [ ] 設定テンプレート機能（`jj config init --template abaqus`）
- [ ] 設定のマージ機能（複数プロジェクトの設定統合）

### Phase 4: 高度な設定管理（長期）

- [ ] 環境変数からの設定上書き
- [ ] 設定のバージョン管理（migration）
- [ ] 設定のインポート/エクスポート
- [ ] チーム共有設定（`.j2/config/shared/`）

---

## 7. 設計上の注意事項

### 7.1 セキュリティ

- `.pyssh.yaml` には秘密鍵のパスのみを記載し、鍵本体は含めない
- `.pyssh.yaml` は `.gitignore` に追加（誤コミット防止）

### 7.2 互換性

- 既存の設定ファイルとの後方互換性を維持
- 設定フォーマット変更時はマイグレーション機能を提供

### 7.3 パフォーマンス

- 設定ファイルの読込は初回のみ、以降はキャッシュを利用
- 大量の設定項目でも高速に読み込めるよう最適化

---

## 8. テスト方針

### 単体テスト（pytest）

- `tests/config/test_config_loader.py` : 各設定ファイルの読込テスト
- `tests/config/test_config_models.py` : Pydanticモデルのバリデーション

### テストケース例

- 正常な設定ファイルの読込
- 不正なYAMLフォーマットのエラーハンドリング
- デフォルト設定の適用
- 設定の優先順位の検証
- 設定ファイルが存在しない場合の動作

---

## 9. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| パーサー層 | → 設定管理層 | 拡張子・接頭辞設定を取得 |
| runコマンド層 | → 設定管理層 | SSH設定を取得 |
| fileコマンド層 | → 設定管理層 | SSH設定、語彙設定を取得 |
| noteコマンド層 | → 設定管理層 | 語彙設定を取得してObsidianノート生成 |
| アダプター層 | → 設定管理層 | ソフト固有設定を取得 |

---

## 10. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [パーサー層仕様書](./02-parser.md)
