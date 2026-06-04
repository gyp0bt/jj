"""jj jobs コマンドのテスト

軸B（汎用レポジトリ＋一覧）の第一歩。ワークスペース内のRUNノード一覧を
表示する `jj jobs` のサービス層・CLI層をテストする。

- サービス層: GraphCommandService.jobs() がRUNノードをフィルタして返す
- CLI層: argparse解析（--type / --status / -f）と出力整形

[READMEへ戻る](../../README.md)
"""

from __future__ import annotations

from pathlib import Path

from jj_types import (
    RUN_INPUT,
    RUN_OUTPUT,
    GraphModel,
    Node,
    NodeCategory,
    Relation,
)
from services.service.graph_command import GraphCommandService, JobsResult


def _build_jobs_graph() -> GraphModel:
    """RUNノードを含むテスト用グラフ"""
    nodes = [
        # ファイル
        Node(id=1, type="file", name="job1.inp", format="inp"),
        Node(id=2, type="file", name="job1.odb", format="odb"),
        # Run群
        Node(
            id=100,
            type="cae_job",
            name="Run 1",
            format="",
            category=NodeCategory.RUN,
            properties={
                "run_type": "cae_job",
                "run_status": "completed",
                "started_at": "2026-06-01T10:00:00",
            },
        ),
        Node(
            id=101,
            type="cae_job",
            name="Run 2",
            format="",
            category=NodeCategory.RUN,
            properties={
                "run_type": "cae_job",
                "run_status": "latent",
                "started_at": "",
            },
        ),
        Node(
            id=200,
            type="ml_training",
            name="ML Run",
            format="",
            category=NodeCategory.RUN,
            properties={
                "run_type": "ml_training",
                "run_status": "completed",
                "started_at": "2026-06-02T09:30:00",
            },
        ),
    ]
    relations = [
        Relation(id=1, label=RUN_INPUT, node1_id=100, node2_id=1),
        Relation(id=2, label=RUN_OUTPUT, node1_id=100, node2_id=2),
    ]
    return GraphModel(nodes=nodes, relations=relations)


def _service_with_graph(tmp_path: Path, graph: GraphModel) -> GraphCommandService:
    """load()が指定グラフを返すGraphCommandServiceを構築"""
    service = GraphCommandService(tmp_path)
    service._graph_service.load = lambda **_kwargs: graph  # type: ignore[method-assign]
    return service


class TestJobsService:
    """GraphCommandService.jobs() のテスト"""

    def test_jobs_all(self, tmp_path: Path):
        """フィルタなしで全RUNノードを返す"""
        service = _service_with_graph(tmp_path, _build_jobs_graph())
        result = service.jobs()
        assert isinstance(result, JobsResult)
        assert result.empty is False
        assert {n.id for n in result.jobs} == {100, 101, 200}

    def test_jobs_filter_by_type(self, tmp_path: Path):
        """run_typeで絞り込める"""
        service = _service_with_graph(tmp_path, _build_jobs_graph())
        cae = service.jobs(run_type="cae_job")
        assert {n.id for n in cae.jobs} == {100, 101}
        ml = service.jobs(run_type="ml_training")
        assert {n.id for n in ml.jobs} == {200}

    def test_jobs_filter_by_status(self, tmp_path: Path):
        """run_statusで絞り込める"""
        service = _service_with_graph(tmp_path, _build_jobs_graph())
        completed = service.jobs(run_status="completed")
        assert {n.id for n in completed.jobs} == {100, 200}
        latent = service.jobs(run_status="latent")
        assert {n.id for n in latent.jobs} == {101}

    def test_jobs_filter_combined(self, tmp_path: Path):
        """run_type + run_status のAND条件で絞り込める"""
        service = _service_with_graph(tmp_path, _build_jobs_graph())
        result = service.jobs(run_type="cae_job", run_status="completed")
        assert {n.id for n in result.jobs} == {100}

    def test_jobs_empty_graph(self, tmp_path: Path):
        """空グラフではempty=Trueを返す"""
        service = _service_with_graph(tmp_path, GraphModel(nodes=[], relations=[]))
        result = service.jobs()
        assert result.empty is True
        assert result.jobs == []

    def test_jobs_no_run_nodes(self, tmp_path: Path):
        """RUNノードが無い場合は空リスト（empty=Falseのまま）"""
        graph = GraphModel(
            nodes=[Node(id=1, type="file", name="a.inp", format="inp")],
            relations=[],
        )
        service = _service_with_graph(tmp_path, graph)
        result = service.jobs()
        assert result.empty is False
        assert result.jobs == []


class TestJobsCLI:
    """jj jobs CLI層（argparse解析・出力整形）のテスト"""

    def test_parser_accepts_jobs(self):
        """build_parserがjobsサブコマンドを解析できる"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["jobs"])
        assert args.cmd == "jobs"

    def test_parser_accepts_type_and_status(self):
        """--type / --status / -f を解析できる"""
        from services.cli import build_parser

        parser = build_parser()
        args = parser.parse_args(["jobs", "--type", "cae_job", "--status", "completed", "-f", "graph.yaml"])
        assert args.cmd == "jobs"
        assert args.type == "cae_job"
        assert args.status == "completed"
        assert args.file == "graph.yaml"

    def test_dispatch_jobs_outputs_runs(self, tmp_path, monkeypatch, capsys):
        """jj jobs がRUNノード一覧を出力する"""
        import services.cli.graph as graph_cli
        from services.cli import build_parser, dispatch

        monkeypatch.setattr(graph_cli.Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            graph_cli.GraphCommandService,
            "jobs",
            lambda self, run_type=None, run_status=None, graph_filename=None: JobsResult(
                jobs=_build_jobs_graph().nodes[2:],
                empty=False,
            ),
        )

        args = build_parser().parse_args(["jobs"])
        rc = dispatch(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert "Run 1" in out
        assert "ML Run" in out
        assert "completed" in out

    def test_dispatch_jobs_empty(self, tmp_path, monkeypatch, capsys):
        """グラフが空のときは案内メッセージを出力する"""
        import services.cli.graph as graph_cli
        from services.cli import build_parser, dispatch

        monkeypatch.setattr(graph_cli.Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            graph_cli.GraphCommandService,
            "jobs",
            lambda self, run_type=None, run_status=None, graph_filename=None: JobsResult(jobs=[], empty=True),
        )

        args = build_parser().parse_args(["jobs"])
        rc = dispatch(args)
        out = capsys.readouterr().out
        assert rc == 1
        assert "parse" in out

    def test_dispatch_jobs_no_runs(self, tmp_path, monkeypatch, capsys):
        """RUNノードが無い場合は0件メッセージを出力する"""
        import services.cli.graph as graph_cli
        from services.cli import build_parser, dispatch

        monkeypatch.setattr(graph_cli.Path, "cwd", lambda: tmp_path)
        monkeypatch.setattr(
            graph_cli.GraphCommandService,
            "jobs",
            lambda self, run_type=None, run_status=None, graph_filename=None: JobsResult(jobs=[], empty=False),
        )

        args = build_parser().parse_args(["jobs"])
        rc = dispatch(args)
        out = capsys.readouterr().out
        assert rc == 0
        assert "0" in out or "見つかりません" in out
