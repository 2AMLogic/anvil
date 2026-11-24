"""Doc-coverage guard for the slides ``*-FAILED.md`` stub redaction (#1546).

``slides-figures`` writes ``figures/<name>.png-FAILED.md`` stubs whose
diagnostic text comes from captured ``mmdc`` / ``marp`` / ``python3``
output. Per the #1534 redaction contract extended to failure stubs by
#1546, that captured text must pass through
``anvil.lib.sidecar.redact_home_paths()`` before it is written into the
tracked version dir — a leaked ``/home/<user>/...`` cannot be un-pushed
from a public consumer repo.

Follows the ``test_*_redaction_doc.py`` pattern from #1544; distinct
filename per the #58 packaging convention.
"""

from __future__ import annotations

import functools
from pathlib import Path

from anvil.lib.testing import read_text

DOC = Path(__file__).resolve().parent.parent / "commands" / "slides-figures.md"

_read = functools.partial(read_text, DOC)


def test_slides_figures_doc_states_failed_stub_redaction() -> None:
    text = _read()
    assert "anvil.lib.sidecar.redact_home_paths" in text
    assert "#1546" in text
