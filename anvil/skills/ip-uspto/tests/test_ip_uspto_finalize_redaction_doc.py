"""Doc-coverage guard for the spec.build.log home-path redaction (#1534).

``ip-uspto-finalize`` writes the pdflatex log to the tracked
``<thread>.final/spec.build.log`` when the finalize compile fails. The
raw log names every loaded file by absolute path, so a per-user texmf
tree leaks ``/home/<user>/...`` (and the local username) into the
package dir — in a public consumer repo that cannot be undone after
push. The doc must route the capture through the ``sidecar copy
--redact-home`` primitive (issue #1534) so the landed log is redacted
before it becomes part of the tracked package.
"""

from __future__ import annotations

import functools
from pathlib import Path

from anvil.lib.testing import read_text

DOC = Path(__file__).resolve().parent.parent / "commands" / "ip-uspto-finalize.md"

_read = functools.partial(read_text, DOC)


def test_finalize_doc_redacts_spec_build_log_capture():
    text = _read()
    assert "spec.build.log" in text
    assert "--redact-home" in text
    assert "redact_home" in text
