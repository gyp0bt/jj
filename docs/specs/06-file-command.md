[READMEへ戻る](../../README.md)

# fileコマンド層 仕様書

## 1. 概要

本ドメインは、ファイルテンプレートの生成、リネーム、移動、SSH送受信など、ファイル操作全般を担当します。操作履歴をグラフデータとして記録し、トレーサビリティを確保します。

### 目的

- ファイル操作の履歴をグラフデータとして記録
- 依存関係を保ったファイル操作（リネーム、移動）
- SSH経由のファイル送受信の統合管理
- テンプレートからのファイル生成

### 責務範囲

- `services/file/` : ファイル操作とテンプレート生成
- `services/ssh/` : SSH送受信（`file` から利用）

---

## 2. コマンド構文

### 2.1 テンプレート生成

```bash
jj f template <template_name> [options]
```

#### 例

```bash
jj f template abaqus --idx 1 --ver 1 --ncpu 4
# 生成: go_ncpu4_v1_idx1.inp, mesh_v1_idx1.cdb, material_v1_idx1.mat
```

### 2.2 リネーム

```bash
jj f rename <old_name> <new_name> [--cascade]
```

#### 例

```bash
jj f rename go_sample_v1_idx1.inp go_sample_v2_idx1.inp --cascade
# go_sample_v1_idx1.inp -> go_sample_v2_idx1.inp
# 関連ファイルも自動リネーム（--cascadeオプション）
```

### 2.3 移動

```bash
jj f move <source> <destination> [--keep-relations]
```

#### 例

```bash
jj f move go_sample_v1_idx1.inp archive/
# ファイルを移動し、関係も更新
```

### 2.4 SSH送信

```bash
jj f send <file> <remote_host>:<remote_path>
```

#### 例

```bash
jj f send go_sample_v1_idx1.inp server01:/work/project/
```

### 2.5 SSH受信

```bash
jj f recv <remote_host>:<remote_path> <local_path>
```

#### 例

```bash
jj f recv server01:/work/project/result.odb ./results/
```

---

## 3. テンプレート機能

### 3.1 テンプレートの定義

テンプレートは `.j2/templates/` に配置されます。

```
.j2/templates/
├── abaqus/
│   ├── go.inp.j2
│   ├── mesh.cdb.j2
│   └── material.mat.j2
├── fluent/
│   ├── go.cas.h5.j2
│   └── input.jou.j2
└── dyna/
    ├── go.k.j2
    └── material.k.j2
```

### 3.2 テンプレート記法（Jinja2）

```jinja2
*Heading
{{ project_name }} - Index {{ idx }} Version {{ ver }}

*Node
...

*Element, type=C3D8R
...

*Material, name=Steel
*Elastic
{{ youngs_modulus }}, {{ poisson_ratio }}
```

### 3.3 テンプレート生成時のパラメータ

| パラメータ | 型 | デフォルト | 説明 |
|-----------|-----|----------|------|
| `--idx` | `int` | 1 | インデックス番号 |
| `--ver` | `int` | 1 | バージョン番号 |
| `--props` | `dict` | `{}` | カスタムプロパティ（例: `ncpu=4,mem=8`） |
| `--tags` | `list[str]` | `[]` | タグリスト |

### 3.4 テンプレート生成フロー

1. テンプレートディレクトリからファイルを読み込み
2. パラメータをJinja2エンジンに渡してレンダリング
3. 命名規則に従ってファイル名を生成
4. ファイルを書き出し
5. `Node(type=file)` を生成し、`GraphStorage` に追加

---

## 4. リネーム機能

### 4.1 基本リネーム

ファイル名を変更し、グラフデータ内の参照も更新します。

#### フロー

1. 旧ファイル名のNodeを取得
2. ファイルシステム上でリネーム
3. Nodeの `name` フィールドを更新
4. `Relation(label=renamed)` を作成

### 4.2 カスケードリネーム（`--cascade`）

関連ファイル（同一indexのファイルグループ）も一括リネームします。

#### 例

**元のファイル群**:
```
go_sample_v1_idx1.inp
mesh_elem5000_v1_idx1.cdb
material_steel_v1_idx1.mat
```

**リネームコマンド**:
```bash
jj f rename go_sample_v1_idx1.inp go_newsample_v2_idx1.inp --cascade
```

**結果**:
```
go_newsample_v2_idx1.inp
mesh_elem5000_v2_idx1.cdb
material_steel_v2_idx1.mat
```

---

## 5. 移動機能

### 5.1 基本移動

ファイルを別ディレクトリに移動し、グラフデータを更新します。

#### フロー

1. 移動元ファイルのNodeを取得
2. ファイルシステム上で移動
3. Nodeの `properties["path"]` を更新
4. `Relation(label=moved)` を作成

### 5.2 関係保持（`--keep-relations`）

移動後も既存の関係（Relation）を維持します。

---

## 6. SSH送受信機能

### 6.1 SSH設定の読込

`.pyssh.yaml` から接続情報を取得します。

```yaml
hosts:
  server01:
    hostname: server01.example.com
    user: username
    port: 22
    key_file: ~/.ssh/id_rsa
```

### 6.2 送信（send）

#### フロー

1. ローカルファイルのNodeを取得
2. SSH接続を確立
3. `scp` または `rsync` でファイル転送
4. `Node(type=remote_file)` を作成
5. `Relation(label=sent)` を作成

### 6.3 受信（recv）

#### フロー

1. リモートファイルのパスを指定
2. SSH接続を確立
3. `scp` または `rsync` でファイル転送
4. ローカルに保存
5. `Node(type=file)` を作成
6. `Relation(label=received)` を作成

---

## 7. 操作履歴のグラフ化

### 7.1 リネーム履歴

```
Node(id=1, type="file", name="go_sample_v1_idx1.inp")
  ↓ (renamed)
Node(id=2, type="file", name="go_sample_v2_idx1.inp")
```

### 7.2 送信履歴

```
Node(id=1, type="file", name="go_sample_v1_idx1.inp")
  ↓ (sent)
Node(id=2, type="remote_file", name="server01:/work/project/go_sample_v1_idx1.inp")
```

### 7.3 受信履歴

```
Node(id=1, type="remote_file", name="server01:/work/project/result.odb")
  ↓ (received)
Node(id=2, type="file", name="results/result.odb")
```

---

## 8. 実装計画

### Phase 1: テンプレート機能（中期）

- [ ] テンプレートディレクトリの構造定義
- [ ] Jinja2によるテンプレートレンダリング
- [ ] 基本テンプレート（Abaqus, Fluent, Dyna）の作成
- [ ] `jj f template` コマンドの実装

### Phase 2: リネーム・移動機能（中期）

- [ ] 基本リネーム機能の実装
- [ ] カスケードリネーム機能の実装
- [ ] 基本移動機能の実装
- [ ] 関係保持オプションの実装

### Phase 3: SSH送受信機能（中期）

- [ ] SSH設定読込の実装
- [ ] 送信機能の実装
- [ ] 受信機能の実装
- [ ] 送受信履歴のグラフ化

### Phase 4: 高度な機能（長期）

- [ ] 複数ファイル一括操作
- [ ] ファイル比較機能（diff）
- [ ] ファイル履歴の可視化
- [ ] テンプレートのカスタマイズ機能

---

## 9. 設計上の注意事項

### 9.1 依存関係の整合性

- リネーム・移動時は必ずグラフデータも更新
- 関連ファイルの自動検出と一括操作

### 9.2 エラーハンドリング

- ファイル操作失敗時のロールバック
- SSH接続失敗時のリトライ

### 9.3 セキュリティ

- SSH鍵の安全な管理
- リモートパスのサニタイズ

---

## 10. テスト方針

### 単体テスト（pytest）

- `tests/services/test_file.py` : FileServiceの各機能テスト
- `tests/services/test_ssh.py` : SSH送受信のテスト

### テストケース例

- テンプレート生成の正確性
- リネームの動作
- カスケードリネームの動作
- 移動の動作
- SSH送受信の動作
- グラフデータの整合性

---

## 11. 他ドメインとの関係

| ドメイン | 依存関係 | 説明 |
|---------|---------|------|
| コアデータモデル層 | ← fileコマンド層 | 操作履歴をNode/Relationとして保存 |
| 設定管理層 | ← fileコマンド層 | SSH設定を取得 |
| パーサー層 | → fileコマンド層 | ファイル名の解析に利用 |
| runコマンド層 | ← fileコマンド層 | 実行前の準備としてファイル生成 |

---

## 12. 参考資料

- [実装詳細](../detail.md)
- [ロードマップ](../roadmap.md)
- [コアデータモデル仕様書](./01-core-data-model.md)
- [設定管理層仕様書](./03-config.md)
