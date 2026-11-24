"""Doc-coverage guard for the .report-build.log redaction exemption (#1534).

``report-review``'s ``log_path`` input references a compile log
"captured by report-figures at ``<thread>.{N}/.report-build.log``".
No command in the report skill currently writes that file (report-figures
has no LaTeX compile step), so there is no capture site to redact — but
the reference must SAY so, and must name the redaction contract any
future writer inherits, so a future persistent build log does not land
un-redacted home paths in a tracked version dir.
"""

from __future__ import annotations

import functools
from pathlib import Path

from anvil.lib.testing import read_text

DOC = Path(__file__).resolve().parent.parent / "commands" / "report-review.md"

_read = functools.partial(read_text, DOC)


def test_report_review_doc_states_build_log_redaction_disposition():
    text = _read()
    assert ".report-build.log" in text
    assert "--redact-home" in text
