"""Tests for ``anvil.lib.latex_render``.

All tests are runnable without xelatex or pandoc installed. The subprocess
invocations are monkeypatched; the module-level binary availability checks
are patched via ``shutil.which``.

Test coverage:
- Template substitution: portrait, landscape, hero variants
- COMPILE_UNAVAILABLE when xelatex absent
- COMPILE_UNAVAILABLE when pandoc absent
- COMPILE_SKIPPED when pdf_output is False
- COMPILE_SKIPPED when pdf_output is absent
- xelatex passes run with max_print_line in env (issue #1545)
"""

from __future__ import annotations

import os
import shutil
import string
import subprocess
from pathlib import Path
from unittest.mock import patch

import pytest

from anvil.lib.latex_render import render_brief_to_pdf
from anvil.lib.render_gate import (
    COMPILE_OK,
    COMPILE_SKIPPED,
    COMPILE_UNAVAILABLE,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_TEMPLATE_PATH = Path(__file__).parent.parent.parent / "anvil" / "lib" / "latex" / "anvil-doc.tex.j2"
_CLS_PATH = Path(__file__).parent.parent.parent / "anvil" / "lib" / "latex" / "anvil-doc.cls"


def _render_template(brief: dict, body_latex: str) -> str:
    """Exercise the same template-substitution logic as latex_render.py."""
    template_text = _TEMPLATE_PATH.read_text(encoding="utf-8")
    tmpl = string.Template(template_text)
    orientation_option = (
        "landscape" if brief.get("orientation") == "landscape" else ""
    )
    return tmpl.substitute(
        orientation_option=orientation_option,
        signature_color=brief.get("signature_color", "6B7280"),
        title=brief.get("title", ""),
        studio=brief.get("studio", ""),
        date=brief.get("date", ""),
        stage=brief.get("stage", ""),
        hero=brief.get("hero", ""),
        body_latex=body_latex,
    )


# ---------------------------------------------------------------------------
# Template substitution tests — no subprocess needed
# ---------------------------------------------------------------------------


def test_template_substitution_portrait():
    """Portrait (default): \\documentclass[]{anvil-doc} with correct accent color."""
    brief = {
        "pdf_output": True,
        "title": "My Document",
        "studio": "Test Studio",
        "date": "June 2026",
        "stage": "DRAFT",
        "signature_color": "4A6FA5",
    }
    rendered = _render_template(brief, body_latex="\\section{Introduction}")

    assert r"\documentclass[]{anvil-doc}" in rendered
    assert r"\definecolor{accent}{HTML}{4A6FA5}" in rendered
    assert r"\anvildoctitle{My Document}" in rendered
    assert r"\anvildocstudio{Test Studio}" in rendered
    assert r"\anvildocdate{June 2026}" in rendered
    assert r"\anvildocstage{DRAFT}" in rendered
    assert r"\section{Introduction}" in rendered


def test_template_substitution_landscape():
    """Landscape orientation: \\documentclass[landscape]{anvil-doc}."""
    brief = {
        "pdf_output": True,
        "title": "Wide Doc",
        "orientation": "landscape",
        "signature_color": "B45309",
    }
    rendered = _render_template(brief, body_latex="body text")

    assert r"\documentclass[landscape]{anvil-doc}" in rendered
    assert r"\definecolor{accent}{HTML}{B45309}" in rendered


def test_template_substitution_hero():
    """Hero image path is substituted into \\herofigure{}."""
    brief = {
        "pdf_output": True,
        "hero": "figures/hero.png",
    }
    rendered = _render_template(brief, body_latex="")

    assert r"\herofigure{figures/hero.png}" in rendered


def test_template_substitution_default_color():
    """When signature_color absent, defaults to 6B7280 (neutral gray)."""
    brief = {"pdf_output": True, "title": "Gray Doc"}
    rendered = _render_template(brief, body_latex="")

    assert r"\definecolor{accent}{HTML}{6B7280}" in rendered
    assert r"\definecolor{rule}{HTML}{6B7280}" in rendered


def test_template_substitution_empty_hero():
    """When hero absent, \\herofigure{} is called with empty arg (no-op in cls)."""
    brief = {"pdf_output": True}
    rendered = _render_template(brief, body_latex="")

    assert r"\herofigure{}" in rendered


# ---------------------------------------------------------------------------
# anvil-doc.cls — text-level guard assertions (issue #422)
# ---------------------------------------------------------------------------


def test_cls_empty_guards_use_ifdefempty():
    """The empty-subtitle/hero guards use etoolbox's expansion-based
    \\ifdefempty, not \\ifx ... \\empty.

    \\ifx is prefix-sensitive: it is false whenever the operands differ in
    \\long/\\protected status, so the legacy idiom silently breaks if the
    macro initialization ever becomes \\long (e.g. older kernels'
    \\newcommand, or a future \\NewDocumentCommand refactor). Issue #422.
    """
    text = _CLS_PATH.read_text(encoding="utf-8")

    assert r"\ifx\anvil@subtitle\empty" not in text
    assert r"\ifx\anvil@hero\empty" not in text
    assert r"\RequirePackage{etoolbox}" in text
    assert r"\ifdefempty{\anvil@subtitle}" in text
    assert r"\ifdefempty{\anvil@hero}" in text


# ---------------------------------------------------------------------------
# render_brief_to_pdf — COMPILE_UNAVAILABLE paths (no real xelatex/pandoc)
# ---------------------------------------------------------------------------


def test_compile_unavailable_when_xelatex_absent(tmp_path, monkeypatch):
    """Returns COMPILE_UNAVAILABLE (not exception) when xelatex is absent."""
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    # xelatex absent, pandoc present
    def fake_which(name):
        if name == "xelatex":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(shutil, "which", fake_which)

    result = render_brief_to_pdf(
        brief={"pdf_output": True, "title": "Test"},
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_UNAVAILABLE
    assert result.passed is True  # graceful-degrade
    assert not out_pdf.exists()


def test_compile_unavailable_when_pandoc_absent(tmp_path, monkeypatch):
    """Returns COMPILE_UNAVAILABLE (not exception) when pandoc is absent."""
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    # xelatex present, pandoc absent
    def fake_which(name):
        if name == "pandoc":
            return None
        return f"/usr/bin/{name}"

    monkeypatch.setattr(shutil, "which", fake_which)

    result = render_brief_to_pdf(
        brief={"pdf_output": True, "title": "Test"},
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_UNAVAILABLE
    assert result.passed is True  # graceful-degrade
    assert not out_pdf.exists()


# ---------------------------------------------------------------------------
# render_brief_to_pdf — COMPILE_SKIPPED paths
# ---------------------------------------------------------------------------


def test_compile_skipped_when_pdf_output_false(tmp_path, monkeypatch):
    """Returns COMPILE_SKIPPED when pdf_output is explicitly False."""
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    # Both binaries present — should still skip before any subprocess call.
    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    result = render_brief_to_pdf(
        brief={"pdf_output": False, "title": "Test"},
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_SKIPPED
    assert result.passed is True


def test_compile_skipped_when_pdf_output_absent(tmp_path, monkeypatch):
    """Returns COMPILE_SKIPPED when pdf_output key is absent from BRIEF."""
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    result = render_brief_to_pdf(
        brief={"title": "Test"},  # no pdf_output key
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_SKIPPED
    assert result.passed is True


# ---------------------------------------------------------------------------
# render_brief_to_pdf — xelatex env contract (issue #1545)
# ---------------------------------------------------------------------------


class _FakeProc:
    """Minimal subprocess.CompletedProc stand-in: success, latex-ish body."""

    returncode = 0
    stdout = "\\section{Hello}"
    stderr = ""


def _fake_toolchain_run(cmd, **kwargs):
    """Fake subprocess.run: pandoc yields a LaTeX fragment; each xelatex
    pass writes a (fake) PDF + log into the compile cwd."""
    if cmd[0] == "xelatex":
        cwd = Path(kwargs["cwd"])
        (cwd / "doc.pdf").write_bytes(b"%PDF-1.4 fake")
        (cwd / "doc.log").write_text("fake log\n", encoding="utf-8")
    return _FakeProc()


def test_xelatex_passes_run_with_max_print_line_env(tmp_path, monkeypatch):
    """Both xelatex passes carry max_print_line=10000 in env (issue #1545).

    TeX wraps log lines at max_print_line (default 79), inserting a bare
    newline that can split a home path mid-prefix and defeat downstream
    home-path redaction. The render must raise it so paths stay contiguous,
    preserve the caller's other env vars, and leave the pandoc call's env
    untouched (pandoc writes no TeX log).
    """
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")

    calls = []

    def fake_run(cmd, **kwargs):
        calls.append((list(cmd), kwargs))
        return _fake_toolchain_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_brief_to_pdf(
        brief={"pdf_output": True, "title": "Test"},
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_OK
    assert result.passed is True

    xelatex_calls = [(cmd, kw) for cmd, kw in calls if cmd[0] == "xelatex"]
    assert len(xelatex_calls) == 2, "expected the two-pass xelatex compile"
    for _cmd, kw in xelatex_calls:
        env = kw.get("env")
        assert isinstance(env, dict), "xelatex must receive an explicit env"
        assert env["max_print_line"] == "10000"
        # Caller's other env vars are preserved.
        assert env["PATH"] == os.environ["PATH"]

    pandoc_calls = [(cmd, kw) for cmd, kw in calls if cmd[0] == "pandoc"]
    assert len(pandoc_calls) == 1
    assert pandoc_calls[0][1].get("env") is None, "pandoc env must stay untouched"


def test_xelatex_env_caller_max_print_line_wins(tmp_path, monkeypatch):
    """A caller-set max_print_line is not overridden (issue #1545 edge case)."""
    body_md = tmp_path / "body.md"
    body_md.write_text("# Hello\n")
    out_pdf = tmp_path / "out.pdf"

    monkeypatch.setattr(shutil, "which", lambda name: f"/usr/bin/{name}")
    monkeypatch.setenv("max_print_line", "200")

    seen_envs = []

    def fake_run(cmd, **kwargs):
        if cmd[0] == "xelatex":
            seen_envs.append(kwargs.get("env"))
        return _fake_toolchain_run(cmd, **kwargs)

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = render_brief_to_pdf(
        brief={"pdf_output": True, "title": "Test"},
        body_md=body_md,
        out_pdf=out_pdf,
    )

    assert result.compile_status == COMPILE_OK
    assert len(seen_envs) == 2
    for env in seen_envs:
        assert env["max_print_line"] == "200"
