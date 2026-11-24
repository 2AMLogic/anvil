"""Redaction coverage for report figure-adapter failure stubs (#1546).

``report-figures`` dispatches ``run_figure_adapters``, whose per-unit
failure path writes ``<adapter>.<ext>.FAILED.md`` stubs with captured
adapter stderr as the body. Per the #1534 redaction contract extended to
failure stubs by #1546, that captured text passes through
``anvil.lib.sidecar.redact_home_paths()`` before it lands in the tracked
version dir — a leaked ``/home/<user>/...`` cannot be un-pushed from a
public consumer repo. The doc tests pin the contract in both command
docs; the unit tests pin the writer itself.

Follows the ``test_*_redaction_doc.py`` pattern from #1544; distinct
filename per the #58 packaging convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

from anvil.lib.testing import read_text

_HERE = Path(__file__).resolve().parent
_REPO_ROOT = _HERE.parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from anvil.skills.report.lib.figure_adapters import (  # noqa: E402
    AdapterSpec,
    _write_failed_stub,
)

_COMMANDS = _HERE.parent / "commands"


def _write_stub(tmp_path: Path, stderr: str) -> str:
    spec = AdapterSpec("render", "render {input} {output}", "src/*/*.sp", "svg")
    output = tmp_path / "exhibits" / "blocks" / "adc" / "render.svg"
    _write_failed_stub(
        output,
        adapter=spec,
        unit="adc",
        input_path="src/adc/schematic.sp",
        argv=["render", "src/adc/schematic.sp", str(output)],
        reason="non-zero exit",
        stderr=stderr,
    )
    stub = tmp_path / "exhibits" / "blocks" / "adc" / "render.svg.FAILED.md"
    return stub.read_text(encoding="utf-8")


def test_failed_stub_redacts_home_paths_in_captured_stderr(tmp_path: Path) -> None:
    home = str(Path.home())
    text = _write_stub(tmp_path, f"Traceback (most recent call last):\n  File \"{home}/venv/lib/x.py\", line 1\nboom\n")
    assert "~/venv/lib/x.py" in text
    assert f"{home}/venv" not in text


def test_failed_stub_leaves_home_free_stderr_unchanged(tmp_path: Path) -> None:
    text = _write_stub(tmp_path, "syntax error in schematic\n")
    assert "syntax error in schematic" in text


def test_report_figure_adapter_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "report-figure-adapter.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text


def test_report_figures_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "report-figures.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text
