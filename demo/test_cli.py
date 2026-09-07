"""The demo CLI entry point.

Regression cover for the Windows crash the V1.1 audit found: ``validate``
prints ``↔`` and ``—``, which a legacy cp1252 console cannot encode, so the
command aborted with ``UnicodeEncodeError`` before printing its verdict. The
CLI now reconfigures the standard streams to UTF-8 with ``errors="replace"``,
so the command completes on any console.
"""

from __future__ import annotations

import io
import sys

from app.demo.__main__ import main


class _Cp1252Stream(io.TextIOWrapper):
    """A text stream backed by a cp1252 buffer, like a Windows console.

    Crucially it exposes ``reconfigure`` (as the real console streams do), so
    the CLI can switch it to UTF-8. Before the fix, writing ``↔`` here raised
    ``UnicodeEncodeError``.
    """

    def __init__(self) -> None:
        super().__init__(io.BytesIO(), encoding="cp1252", errors="strict", newline="")


def test_validate_does_not_crash_on_a_legacy_console(monkeypatch) -> None:
    stream = _Cp1252Stream()
    monkeypatch.setattr(sys, "stdout", stream)
    monkeypatch.setattr(sys, "stderr", stream)

    # A short window keeps this fast; the point is that printing the unicode
    # verdict does not raise, not what the verdict is.
    exit_code = main(["validate"])

    stream.seek(0)
    output = stream.buffer.getvalue().decode("utf-8", errors="replace")
    assert exit_code == 0
    assert "↔" in output  # the character that used to crash the command
    assert "demonstrates everything it claims" in output
