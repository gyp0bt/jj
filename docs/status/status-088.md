# status-088: コードベース軽量化

## 概要

93,000行のコードベースを大幅削減し、Abaqus業務に必要な機能のみを残す軽量化を実施。

## 変更内容

### 削除したプラグイン
- services/plugins/: calculix, experiment, flow3d, fluent, hfss, lsdyna, ml, office, ollama, openfoam
- services/parse/connectors/: calculix, experiment, flow3d, fluent, hfss, lsdyna, ml, office, openfoam
- services/dashboard/connectors/: ai_assistant.py, job_monitor.py, ml.py, ml_query.py

### 削除したサービス層
- services/api/ (FastAPI)
- services/job/ (リモートジョブ)
- services/sync/ (同期機構)
- services/ai/ (Ollama連携)

### 削除したCLIコマンド
- jj job (T5リモートジョブ)
- jj prefect (Prefect統合)
- jj ai (T7 Ollama)
- jj push/clone/sync (T9共有フォルダ)
- submit/list/check/files (旧凍結CLI)

### 削除したテスト
- test_ai_assistant_connector.py
- test_ai_service.py
- test_api_extension.py, test_api_service.py
- test_experiment_plugin.py
- test_gitlab_backend.py
- test_job_service.py
- test_ml_dashboard.py, test_ml_parsers.py, test_ml_run_discoverer.py
- test_neo4j_connector.py
- test_office_integration.py
- test_shared_folder_backend.py
- test_surrogate_framework.py
- test_sync_*.py

### 維持したもの
- **プラグイン**: abaqus, obsidian
- **UI**: Dashboard (Streamlit)
- **CLI**: init, parse, show, export, info, diff, run, dashboard, config

### pyproject.toml更新
- version: 0.1.0 → 0.2.0
- entry-points: abaqus, obsidianのみ
- optional-dependencies: pymesh, abaqus, obsidian, dashboard, dev, all

## 検証結果

```bash
pip install -e ".[dev,dashboard]"  # OK
python -c "from services.cli import main"  # OK
pytest tests/test_app.py tests/config/ -v  # 40 passed
ruff check services/cli/__init__.py  # All checks passed
ruff format --check services/cli/__init__.py  # 1 file already formatted
```

## 関連ファイル
- CLAUDE.md: 軽量化後の構成に更新
- pyproject.toml: v0.2.0、依存関係整理
- services/cli/__init__.py: 不要コマンド削除
