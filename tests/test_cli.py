from __future__ import annotations

from minoverlap.cli import build_parser


def test_cli_exposes_research_gates() -> None:
    parser = build_parser()
    help_text = parser.format_help()
    assert "audit" in help_text
    assert "verify-baseline" in help_text
    assert "verify-independent" in help_text
