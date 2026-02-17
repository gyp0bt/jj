[← README.md](../../README.md) | [← roadmap](../roadmap.md)

# 解析結果の保存構造見直し仕様書

**日付**: 2026-02-17
**マイルストーン**: M2（マルチソルバー基盤）
**ステータス**: 設計段階

---

## 背景と課題

### 現行構造

```
results/
├── go_idx0.v29_stress.json           # results/直下（JSONメタデータ）
├── go_idx1.v3_stress.json
├── go_idx2.v3_stress.json
├── step0_frame10/                    # step/frameベースのサブディレクトリ
│   ├── go_idx1.v3_S-S33_vmax10.0_vmin5.0.png
│   └── go_idx1.v3_U-U3_vmax1.0_vmin0.5.png
└── step1_frame20/
    └── go_idx1.v3_S-S33_vmax15.0_vmin3.0.png
```

### 現行構造の課題

1. **GOノード横断的な結果検索が困難**: step/frameベースのディレクトリ構造では、特定GOノードの全結果を収集するためにディレクトリ横断が必要
2. **ファイル名にGOベース名が埋め込まれている**: `go_idx1.v3_S-S33_vmax10.0_vmin5.0.png` のようにGOベース名がプレフィックスになっており、冗長
3. **結果ファイルの整理が困難**: 特定ケースの結果を一括削除・移動する際にディレクトリを跨ぐ必要がある
4. **マルチソルバー対応での拡張性**: ソルバーごとに結果ディレクトリの構造が異なる（OpenFOAM: タイムステップディレクトリ、Fluent: case/data形式等）

---

## 提案: GOノードベースのディレクトリ構造

### 新構造

```
results/
├── go_idx1_v1/                       # GOノード名がディレクトリ名
│   ├── S-S33_step0_frame10_vmax10.0_vmin5.0.png
│   ├── U-U3_step0_frame10_vmax1.0_vmin0.5.png
│   ├── S-S33_step1_frame20_vmax15.0_vmin3.0.png
│   └── stress.json
├── go_idx2_v1/
│   └── stress.json
└── go_idx0_v29/
    └── stress.json
```

### 命名規則

| 要素 | 現行 | 新規 |
|------|------|------|
| ディレクトリ | `step{N}_frame{M}/` | `{go_basename}/` |
| ファイル名 | `{go_basename}_{result_key}_{params}.{ext}` | `{result_key}_{step/frame}_{params}.{ext}` |
| JSONメタデータ | `results/{go_basename}_{key}.json` | `results/{go_basename}/{key}.json` |

### ファイル名パターン詳細

```
{result_key}[_{step_info}][_{params}].{ext}

result_key: S-S33, U-U3, PEEQ, stress 等
step_info:  step0_frame10 等（オプショナル）
params:     vmax10.0_vmin5.0 等（オプショナル）
ext:        png, csv, json 等
```

---

## 設計判断

### GOノード名の正規化

- `go_idx1.v1.inp` → `go_idx1.v1`（拡張子除去）
- ディレクトリ名には `.` を含めるか `_` に置換するか検討が必要
  - **推奨**: ドット維持（`go_idx1.v1/`）。ファイルシステム互換性は問題なし

### 後方互換性

- **移行期間**: 新旧両方の構造をパーサーが認識する必要がある
- `ResultsMetadataParser` に新構造の解析ロジックを追加し、旧構造のコードは保持
- 新構造の検出: `results/` 直下のサブディレクトリ名が `go_` で始まる場合は新構造と判定

### パーサー変更箇所

| ファイル | 変更内容 |
|---------|---------|
| `services/parse/parsers/results_metadata_parser.py` | 新ディレクトリ構造の検出・メタデータ抽出ロジック追加 |
| `services/parse/parsers/output_parser.py` | result_of リレーション作成時の新パス対応 |
| テストフィクスチャ | 新構造のテストデータ追加 |

### マルチソルバー対応

GOノードベースのディレクトリ構造は、ソルバー間で共通の原則として適用:

| ソルバー | results/内の構造 |
|---------|-----------------|
| Abaqus | `results/{go_basename}/` |
| Fluent | `results/{case_name}/` |
| OpenFOAM | `results/{case_name}/` |
| LS-DYNA | `results/{go_basename}/` |

ソルバー固有のサブ構造（OpenFOAMのタイムステップディレクトリ等）はGOノードディレクトリの下に配置する。

---

## 影響範囲

### コア変更
- `ResultsMetadataParser`: 新構造の解析ロジック（旧構造との共存）
- テストフィクスチャ: 新構造のテストデータ

### 影響なし（変更不要）
- `SavedViewConfig`: 結果パスは既にプロパティとして格納されるため、ディレクトリ構造に依存しない
- `DashboardPageConnector`: 結果データはプロパティ経由でアクセスするため直接影響なし
- HTMLエクスポート: 同上

---

## 実装ステップ

1. **テストフィクスチャの作成**: 新構造のテストデータを `tests/fixtures/` に追加
2. **ResultsMetadataParser の拡張**: 新構造の検出・解析ロジックを追加（旧構造は維持）
3. **output_parser.py の更新**: 新パス形式での result_of リレーション対応
4. **既存テストの維持**: 旧構造のテストは全て通過すること
5. **新構造のテスト追加**: 新構造固有のテストケース

---

## TODO（実装時）

- [ ] テストフィクスチャ作成（新構造）
- [ ] ResultsMetadataParser 新構造解析ロジック
- [ ] output_parser.py 新パス対応
- [ ] テスト追加・既存テスト維持確認
- [ ] マイグレーションスクリプト（旧→新の変換ツール、オプショナル）
