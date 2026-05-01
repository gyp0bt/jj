[← status-index.md](status-index.md)

# status-089 — プラグイン構造統合 (v0.2.1)

- **日付**: 2024-04-30
- **ブランチ**: master
- **バージョン**: 0.2.1

---

## 概要

コネクタ・プラグインが分散していてコンテキストを食っている問題を解消し、プラグイン単位で凝集させた。

### 実施内容

1. **plugins/base/ 作成**: 基底クラス群を集約
   - `plugins/base/parser.py`: AbstractFileParser（旧 services/parse/base.py）
   - `plugins/base/dashboard.py`: DashboardPageConnector（旧 services/dashboard/connectors/__init__.py）
   - `plugins/base/exporter.py`: AbstractExporter（旧 services/export/__init__.py）

2. **plugins/abaqus/ 統合**: Abaqus関連コードを1箇所に
   - `plugins/abaqus/parse/`: パーサー群（旧 services/parse/connectors/abaqus/）
   - `plugins/abaqus/dashboard.py`: ダッシュボードコネクター（旧 services/dashboard/connectors/abaqus.py + abaqus_query.py）
   - `plugins/abaqus/submit.py`: ジョブ投入サービス（旧 services/plugins/abaqus/submit.py）

3. **plugins/obsidian/ 統合**: Obsidian関連コードを1箇所に
   - `plugins/obsidian/parse/`: パーサー群（旧 services/parse/connectors/obsidian/）
   - `plugins/obsidian/export.py`: エクスポーター（旧 services/export/connectors/obsidian/__init__.py）

4. **後方互換**: 旧パスからのimportを引き続きサポート（re-export）

5. **pyproject.toml 更新**:
   - entry-points: `services.plugins.*` → `plugins.*`
   - packages.find: `plugins*` 追加
   - isort known-first-party: `plugins` 追加
   - version: 0.2.0 → 0.2.1

---

## ディレクトリ構造変更

### Before (v0.2.0)

```
services/
├── plugins/abaqus/           # 登録マネージャー
├── parse/connectors/abaqus/  # パーサー群
├── dashboard/connectors/     # ダッシュボード
└── export/connectors/        # エクスポーター群
```

### After (v0.2.1)

```
plugins/
├── base/                     # 基底クラス群
│   ├── parser.py
│   ├── dashboard.py
│   └── exporter.py
├── abaqus/                   # Abaqusプラグイン（全て凝集）
│   ├── __init__.py
│   ├── parse/
│   ├── dashboard.py
│   └── submit.py
└── obsidian/                 # Obsidianプラグイン（全て凝集）
    ├── __init__.py
    ├── parse/
    └── export.py

services/                     # 後方互換re-exportのみ
├── parse/connectors/         # → plugins.*.parse にre-export
├── dashboard/connectors/     # → plugins.*.dashboard にre-export
└── export/connectors/        # → plugins.*.export にre-export
```

---

## 効果

- **Abaqus関連**: 4箇所 → 1箇所（plugins/abaqus/）
- **Obsidian関連**: 3箇所 → 1箇所（plugins/obsidian/）
- **コンテキスト削減**: プラグイン単位で完結、走査範囲縮小

---

## 変更ファイル

### 新規作成
- `plugins/__init__.py`
- `plugins/base/__init__.py`
- `plugins/base/parser.py`
- `plugins/base/dashboard.py`
- `plugins/base/exporter.py`
- `plugins/abaqus/__init__.py`
- `plugins/abaqus/parse/*`
- `plugins/abaqus/dashboard.py`
- `plugins/abaqus/submit.py`
- `plugins/obsidian/__init__.py`
- `plugins/obsidian/parse/*`
- `plugins/obsidian/export.py`

### 後方互換re-exportに変換
- `services/parse/base.py`
- `services/dashboard/connectors/__init__.py`
- `services/export/__init__.py`
- `services/plugins/abaqus/__init__.py`
- `services/plugins/obsidian/__init__.py`
- `services/parse/connectors/abaqus/*`
- `services/parse/connectors/obsidian/*`
- `services/dashboard/connectors/abaqus.py`
- `services/dashboard/connectors/abaqus_query.py`
- `services/export/connectors/obsidian/__init__.py`

### 更新
- `CLAUDE.md`: ディレクトリ構成・プラグイン拡張パターン更新
- `pyproject.toml`: entry-points、packages.find、version更新

---

## 検証コマンド

```bash
pip install -e ".[dev,dashboard]"
pytest tests/ -v
jj parse
jj dashboard
ruff check .
```

---

## TODO

- [ ] テストのimportパスを新パスに更新（オプション）
- [ ] 既存テストが通ることを確認
