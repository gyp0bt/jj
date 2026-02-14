# 典型パターンからの属性抽出起点

> [← README.md](../README.md)

本ドキュメントは、各ファイル形式からエンティティ属性（sysProps / sysTags / userProps / Relation）を
自動抽出するロジックの起点と拡張方針を定義する。

---

## 設計方針

1. **Next.js側は即時・軽量処理のみ** — D&D時のプレビュー生成に使用
2. **高度な解析はprefect側へ委譲** — 本ドキュメントはNext.js側の抽出ロジック一覧
3. **フォーマット検出 → 属性抽出の2段階** — まずフォーマットを判定し、形式固有のルールを適用

---

## 1. Abaqus INP (`*.inp`)

### 現状の抽出（GenericUploader: `extractMaterialsFromText`）

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| 材料名 | `*Material, name=XXX` パース | `userTags[]` |
| 材料キーワード | `*Elastic`, `*Plastic`, `*Density` 等のマッチ | `userTags[]` |
| 材料ブロック | `*Material` 〜 次の非材料行までを切り出し | `body` |
| フォーマット | 拡張子 `.inp` → `"abaqus_inp"` | `sysProps.format` |

### 拡張候補（P2以降）

| 対象 | 方針 |
|---|---|
| ブロック単位分割 | `*Material` ごとに別エンティティに分割（3-13） |
| Section/Assembly抽出 | `*Section`, `*Assembly` ブロックの認識 |
| Include参照 | `*Include, Input=...` のRelation生成 |

### マッチキーワード一覧

```
*elastic, *plastic, *density, *expansion, *damage initiation,
*damage evolution, *conductivity, *electrical conductivity,
*specific heat, *creep, *hyper elastic
```

---

## 2. CSV (`*.csv`)

### 現状の抽出

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| フォーマット | 拡張子 `.csv` → `"csv"` | `sysProps.format` |
| 本文 | ファイル全体をbodyに格納 | `body` |

### 拡張候補

| 対象 | 方針 |
|---|---|
| ヘッダー行解析 | 1行目をカラム名として `userProps` に展開 |
| 数値列統計 | min/max/mean を `userProps` に追加 |
| 行数・列数 | `sysProps.rows`, `sysProps.columns` として記録 |

---

## 3. JSON (`*.json`)

### 現状の抽出

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| フォーマット | 拡張子 `.json` → `"json"` | `sysProps.format` |
| 本文 | ファイル全体をbodyに格納 | `body` |

### 拡張候補

| 対象 | 方針 |
|---|---|
| トップレベルキー | JSONオブジェクトのキーを `userTags` に展開 |
| 配列長 | 配列の場合 `sysProps.array_length` に記録 |
| ネスト深度 | `sysProps.max_depth` に記録 |
| スキーマ検出 | 既知のJSON構造（package.json等）を識別してタグ付け |

---

## 4. YAML (`*.yaml`, `*.yml`)

### 現状の抽出

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| フォーマット | 拡張子 `.yaml` → `"yaml"` | `sysProps.format` |
| 本文 | ファイル全体をbodyに格納 | `body` |

### 拡張候補

| 対象 | 方針 |
|---|---|
| トップレベルキー | YAML辞書のキーを `userTags` に展開 |
| 補正ルール参照 | 同名YAMLファイルのplaceholder修正（全仕様.md §5） |

---

## 5. Markdown (`*.md`)

### 現状の抽出

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| フォーマット | 拡張子 `.md` → `"markdown"` | `sysProps.format` |
| 本文 | ファイル全体をbodyに格納 | `body` |

### 拡張候補（P2以降）

| 対象 | 方針 |
|---|---|
| Heading分割 | `# heading` ごとに別エンティティに分割（3-13） |
| フロントマター | YAML front matter（`---`区間）を `userProps` に展開 |
| リンク抽出 | `[text](url)` パターンからRelation候補を生成 |
| 見出し一覧 | 見出し構造を `sysProps.toc` に記録 |

---

## 6. フォルダ / ディレクトリ

### 現状の抽出（`buildDraftEntities`）

| 抽出対象 | ロジック | 格納先 |
|---|---|---|
| 種別 | `sysTags: ["directory"]` | `sysTags` |
| タイプ | `sysProps.type: "directory"` | `sysProps` |
| 階層Relation | 親フォルダ→子フォルダ: `child`, 親→ファイル: `contains` | `Relation` |
| パス情報 | `_relativePath` で管理（保存時に除去） | 内部用 |

### 拡張候補

| 対象 | 方針 |
|---|---|
| フォルダ命名規則 | 命名パターンから `userTags` を推定（例: `materials/` → `material`） |
| ファイル数統計 | 子ファイル数を `sysProps.file_count` に記録 |

---

## 7. フォーマット検出フロー

```
ファイルD&D
  ↓
拡張子判定 (extToFormat)
  .inp → "abaqus_inp"
  .csv → "csv"
  .json → "json"
  .md  → "markdown"
  他   → ""
  ↓
sysProps.format に格納
  ↓
BodyRenderer.detectFormat（表示時）
  sysProps.format > userProps.format > domain > extension > 内容解析
  ↓
形式固有レンダリング
```

---

## 8. prefect側との分担

| 処理 | Next.js | prefect |
|---|---|---|
| フォーマット検出 | 拡張子ベース（即時） | 内容ベース（高精度） |
| INP材料ブロック抽出 | キーワードマッチ | 構文解析 |
| ブロック分割 | 未実装（P2） | 実装予定 |
| YAML補正ルール適用 | placeholder修正 | スキーマ検証 |
| 統計計算 | 未実装 | 数値解析 |
