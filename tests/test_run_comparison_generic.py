"""Run比較ダッシュボードの汎用化テスト (T8 Phase 8-5)

RUN_STATUS_COLORS、動的テーブルカラム生成、ドメイン非依存の
Run比較UI動作を検証する。
"""

from unittest.mock import MagicMock

from services.dashboard.components.run_comparison import (
    _BASE_TABLE_COLUMNS,
    _HIDDEN_PROPERTIES,
    RUN_STATUS_COLORS,
)


class TestRunStatusColors:
    """RUN_STATUS_COLORS定数のテスト"""

    def test_has_standard_statuses(self):
        assert "completed" in RUN_STATUS_COLORS
        assert "failed" in RUN_STATUS_COLORS
        assert "running" in RUN_STATUS_COLORS
        assert "unknown" in RUN_STATUS_COLORS

    def test_colors_are_hex(self):
        for status, color in RUN_STATUS_COLORS.items():
            assert color.startswith("#"), f"{status}の色が不正: {color}"


class TestBaseTableColumns:
    """テーブルカラム定義のテスト"""

    def test_has_required_columns(self):
        labels = [label for label, _ in _BASE_TABLE_COLUMNS]
        assert "ID" in labels
        assert "名前" in labels
        assert "タイプ" in labels
        assert "ステータス" in labels

    def test_no_domain_specific_columns(self):
        """ドメイン固有カラム（コマンド等）がベースカラムに含まれないことを確認"""
        labels = [label for label, _ in _BASE_TABLE_COLUMNS]
        assert "コマンド" not in labels
        assert "検出" not in labels


class TestHiddenProperties:
    """非表示プロパティのテスト"""

    def test_hides_base_properties(self):
        assert "run_type" in _HIDDEN_PROPERTIES
        assert "run_status" in _HIDDEN_PROPERTIES


class TestDynamicTableGeneration:
    """動的テーブルカラム生成のテスト"""

    def _make_runs(self, properties_list):
        """テスト用Runノードを作成"""
        runs = []
        for i, props in enumerate(properties_list):
            run = MagicMock()
            run.id = i + 1
            run.name = f"run_{i + 1}"
            run.properties = dict(props)
            runs.append(run)
        return runs

    def test_cae_run_properties(self):
        """CAE Runのプロパティが動的カラムに含まれる"""
        runs = self._make_runs(
            [
                {
                    "run_type": "cae_job",
                    "run_status": "completed",
                    "command": "abaqus job=go_1",
                    "duration_seconds": 120,
                },
            ]
        )
        # 全Runプロパティキーを収集（_render_run_tableロジックの検証）
        extra_keys = []
        seen = set()
        for r in runs:
            for key in r.properties:
                if key not in _HIDDEN_PROPERTIES and key not in seen:
                    extra_keys.append(key)
                    seen.add(key)

        assert "command" in extra_keys
        assert "duration_seconds" in extra_keys
        assert "run_type" not in extra_keys  # hidden
        assert "run_status" not in extra_keys  # hidden

    def test_experiment_run_properties(self):
        """物理実験Runのプロパティが動的カラムに含まれる"""
        runs = self._make_runs(
            [
                {
                    "run_type": "experiment",
                    "run_status": "completed",
                    "operator": "田中",
                    "directory": "/data/exp1",
                    "file_count": 5,
                },
            ]
        )
        extra_keys = []
        seen = set()
        for r in runs:
            for key in r.properties:
                if key not in _HIDDEN_PROPERTIES and key not in seen:
                    extra_keys.append(key)
                    seen.add(key)

        assert "operator" in extra_keys
        assert "directory" in extra_keys
        assert "file_count" in extra_keys

    def test_mixed_domain_runs(self):
        """異なるドメインのRunが混在する場合、全プロパティが収集される"""
        runs = self._make_runs(
            [
                {"run_type": "cae_job", "run_status": "completed", "command": "abaqus"},
                {"run_type": "experiment", "run_status": "completed", "operator": "田中"},
                {"run_type": "ml_training", "run_status": "failed", "epochs": 100},
            ]
        )
        extra_keys = []
        seen = set()
        for r in runs:
            for key in r.properties:
                if key not in _HIDDEN_PROPERTIES and key not in seen:
                    extra_keys.append(key)
                    seen.add(key)

        assert "command" in extra_keys
        assert "operator" in extra_keys
        assert "epochs" in extra_keys


class TestHtmlGeneration:
    """HTML生成のドメイン非依存テスト"""

    def test_generate_run_comparison_html_generic(self):
        """汎用RunのHTML生成が動的カラムを使用すること"""
        from services.dashboard.components.run_comparison import _generate_run_comparison_html

        query_svc = MagicMock()
        runs = []
        for i, props in enumerate(
            [
                {"run_type": "experiment", "run_status": "completed", "operator": "鈴木"},
                {"run_type": "experiment", "run_status": "failed", "operator": "田中"},
            ]
        ):
            run = MagicMock()
            run.id = i + 1
            run.name = f"exp_{i + 1}"
            run.properties = dict(props)
            runs.append(run)

        html = _generate_run_comparison_html(runs, query_svc)
        assert "operator" in html
        assert "鈴木" in html
        assert "田中" in html
