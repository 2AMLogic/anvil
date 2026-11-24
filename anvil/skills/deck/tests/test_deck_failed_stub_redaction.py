"""Redaction coverage for per-slot failure stubs (issues #1534 / #1546).

``_write_failed_stub`` embeds the exception ``str()`` verbatim in the
tracked ``<slot>.png-FAILED.md`` stub, and adapter ``BackendError``
messages routinely name absolute paths (``/home/<user>/venv/...``) — the
exact leak class #1534 fixed for compile logs. These tests pin the #1546
contract: the captured exception text passes through
``anvil.lib.sidecar.redact_home_paths()`` before it lands in the stub,
while the prompt echo (author text, not tool output) is left untouched,
and every deck command doc that writes a ``*-FAILED.md`` stub from
captured tool/exception output states the same contract.

Follows the ``test_*_redaction_doc.py`` pattern from #1544; distinct
filename per the #58 packaging convention.
"""

from __future__ import annotations

import sys
from pathlib import Path

from anvil.lib.testing import read_text

# The deck skill keeps lib modules under its own ``lib/`` (issue #31 D4,
# same pattern as ``test_imagegen.py``); put it on ``sys.path`` so the
# writer is importable without a package install step.
_HERE = Path(__file__).resolve().parent
_LIB = _HERE.parent / "lib"
if str(_LIB) not in sys.path:
    sys.path.insert(0, str(_LIB))

from imagegen import _write_failed_stub  # noqa: E402

_COMMANDS = _HERE.parent / "commands"


def test_failed_stub_redacts_home_paths_in_exception_text(tmp_path: Path) -> None:
    home = str(Path.home())
    exc = RuntimeError(f"{home}/venv/lib/x.py failed")
    _write_failed_stub(tmp_path, "hero", "a prompt with no paths", "line-art", exc)
    text = (tmp_path / "hero.png-FAILED.md").read_text(encoding="utf-8")
    assert "~/venv/lib/x.py failed" in text
    assert f"{home}/venv" not in text


def test_failed_stub_leaves_prompt_echo_untouched(tmp_path: Path) -> None:
    home = str(Path.home())
    prompt = f"reference {home}/studio/assets/ref.png closely"
    _write_failed_stub(tmp_path, "hero", prompt, "line-art", RuntimeError("plain failure"))
    text = (tmp_path / "hero.png-FAILED.md").read_text(encoding="utf-8")
    # The prompt echo is the author's own text, not captured tool output:
    # it is deliberately NOT redacted (#1546 keeps #1534's scope).
    assert prompt in text


def test_failed_stub_leaves_home_free_exception_unchanged(tmp_path: Path) -> None:
    _write_failed_stub(
        tmp_path, "hero", "a prompt with no paths", "line-art",
        RuntimeError("plain failure with no path"),
    )
    text = (tmp_path / "hero.png-FAILED.md").read_text(encoding="utf-8")
    assert "plain failure with no path" in text


def test_deck_figures_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "deck-figures.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text


def test_deck_imagegen_doc_states_failed_stub_redaction() -> None:
    text = read_text(_COMMANDS / "deck-imagegen.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text


def test_deck_imagegen_adapter_doc_states_redaction_needs_no_adapter_cooperation() -> None:
    text = read_text(_COMMANDS / "deck-imagegen-adapter.md")
    assert "anvil.lib.sidecar.redact_home_paths" in text
    # Redaction is anvil's job on the captured str(exc); adapters do not
    # have to cooperate (#1546 acceptance criterion).
    assert "no adapter cooperation" in text
