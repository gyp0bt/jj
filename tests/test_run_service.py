from __future__ import annotations

from pathlib import Path

from services.run import RunService


def test_run_service_script_mode_tracks_files_and_props(tmp_path: Path) -> None:
    script_path = tmp_path / "script.py"
    script_path.write_text(
        """
# props start
ncpu=4
# props end
import sys
size = sys.argv[1]
with open("output.txt", "w", encoding="utf-8") as f:
    f.write(size)
""".strip()
        + "\n",
        encoding="utf-8",
    )

    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", str(script_path), "128"],
        cwd=tmp_path,
        mode="script",
    )

    assert result.exit_code == 0
    assert result.script_path == script_path.resolve()
    assert "output.txt" in result.trace_files
    assert result.properties["ncpu"] == "4"
    assert result.properties["size"] == "128"
    assert result.log_path is not None
    assert result.log_path.exists()


def test_run_service_job_mode_skips_trace(tmp_path: Path) -> None:
    service = RunService(storage_dirname=".j2/storage/run")
    result = service.execute(
        command=["python", "-c", "print('hello')"],
        cwd=tmp_path,
    )

    assert result.mode == "job"
    assert result.trace_files == []
    assert result.script_path is None
