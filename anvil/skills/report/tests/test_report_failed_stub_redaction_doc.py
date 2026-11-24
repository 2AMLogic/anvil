"""Redaction coverage for report figure-adapter failure stubs (#1546, #1550).

``report-figures`` dispatches ``run_figure_adapters``, whose per-unit
failure path writes ``<adapter>.<ext>.FAILED.md`` stubs with captured
adapter stderr as the body. Per the #1534 redaction contract extended to
failure stubs by #1546, that captured text passes through
``anvil.lib.sidecar.redact_home_paths()`` before it lands in the tracked
version dir — a leaked ``/home/<user>/...`` cannot be un-pushed from a
public consumer repo. The doc tests pin the contract in both command
docs; the unit tests pin the writer itself.

#1550 extends the same contract to the stub's ``**Command**`` line: the
dispatcher substitutes ``{input}``/``{output}`` with unconditionally
absolute, home-prefixed paths, so the displayed argv is redacted
per-argument **before** shell quoting — with an apostrophe in the home
prefix (``/home/O'Neil``), quoting splits the prefix and redacting the
joined line can no longer match it.

Follows the ``test_*_redaction_doc.py`` pattern from #1544; distinct
filename per the #58 packaging convention.
"""

from __future__ import annotations

import shlex
import sys
from pathlib import Path

import pytest

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


_UNSET = object()


def _write_stub(
    tmp_path: Path, stderr: str, argv: list[str] | None | object = _UNSET
) -> str:
    spec = AdapterSpec("render", "render {input} {output}", "src/*/*.sp", "svg")
    output = tmp_path / "exhibits" / "blocks" / "adc" / "render.svg"
    if argv is _UNSET:
        argv = ["render", "src/adc/schematic.sp", str(output)]
    _write_failed_stub(
        output,
        adapter=spec,
        unit="adc",
        input_path="src/adc/schematic.sp",
        argv=argv,
        reason="non-zero exit",
        stderr=stderr,
    )
    stub = tmp_path / "exhibits" / "blocks" / "adc" / "render.svg.FAILED.md"
    return stub.read_text(encoding="utf-8")


def _command_field(text: str) -> str:
    """Return the ``**Command**`` field's contents (between the backticks)."""
    marker = "- **Command**: `"
    for line in text.splitlines():
        if line.startswith(marker):
            return line[len(marker) :].rsplit("`", 1)[0]
    raise AssertionError("no **Command** field in stub")


def test_failed_stub_redacts_home_paths_in_captured_stderr(tmp_path: Path) -> None:
    home = str(Path.home())
    text = _write_stub(tmp_path, f"Traceback (most recent call last):\n  File \"{home}/venv/lib/x.py\", line 1\nboom\n")
    assert "~/venv/lib/x.py" in text
    assert f"{home}/venv" not in text


def test_failed_stub_leaves_home_free_stderr_unchanged(tmp_path: Path) -> None:
    text = _write_stub(tmp_path, "syntax error in schematic\n")
    assert "syntax error in schematic" in text


def test_failed_stub_command_line_redacts_home_prefixed_args(
    tmp_path: Path,
) -> None:
    home = str(Path.home())
    argv = ["render", f"{home}/src/a b.sp", f"{home}/x/out.svg"]
    text = _write_stub(tmp_path, "", argv=argv)
    assert shlex.split(_command_field(text)) == [
        "render",
        "~/src/a b.sp",
        "~/x/out.svg",
    ]
    assert home not in text


def test_failed_stub_command_line_redacts_apostrophe_home(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    home = "/home/O'Neil"
    monkeypatch.setenv("HOME", home)
    argv = ["render", f"{home}/src/a b.sp", f"{home}/x.svg"]
    text = _write_stub(tmp_path, "", argv=argv)
    assert shlex.split(_command_field(text)) == ["render", "~/src/a b.sp", "~/x.svg"]
    assert "O'Neil" not in text


def test_failed_stub_command_line_round_trips_home_free_args(
    tmp_path: Path,
) -> None:
    argv = ["render", "src/a b.sp", "out.svg"]
    text = _write_stub(tmp_path, "", argv=argv)
    assert shlex.split(_command_field(text)) == argv


def test_failed_stub_command_line_not_invoked_without_argv(tmp_path: Path) -> None:
    assert _command_field(_write_stub(tmp_path, "", argv=None)) == "(not invoked)"
    assert _command_field(_write_stub(tmp_path, "", argv=[])) == "(not invoked)"


def test_report_figure_adapter_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "report-figure-adapter.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text
    assert "**Command**" in text
    assert "#1550" in text


def test_report_figures_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "report-figures.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text
