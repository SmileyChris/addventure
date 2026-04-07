"""Tests for chapter-aware building: prefix assignment, discovery, conflict detection."""

import textwrap
from pathlib import Path

import pytest

from addventure.compiler import compile_game
from addventure.md_writer import generate_markdown
from addventure.cli import (
    _find_chapters,
    _next_chapter_prefix,
    _read_entry_prefix,
)


# ── Prefix reading ────────────────────────────────────────────────────────────

def test_read_entry_prefix(tmp_path):
    index = tmp_path / "index.md"
    index.write_text("---\nentry_prefix: B\n---\n\n# Verbs\nLOOK\n")
    assert _read_entry_prefix(index) == "B"


def test_read_entry_prefix_missing(tmp_path):
    index = tmp_path / "index.md"
    index.write_text("# Verbs\nLOOK\n")
    assert _read_entry_prefix(index) is None


def test_read_entry_prefix_no_file(tmp_path):
    assert _read_entry_prefix(tmp_path / "nope.md") is None


# ── Chapter discovery ─────────────────────────────────────────────────────────

def test_find_chapters(tmp_path):
    # Parent game
    (tmp_path / "index.md").write_text("# Verbs\nLOOK\n\n# Inventory\n")

    # Valid chapter
    ch = tmp_path / "chapter-b"
    ch.mkdir()
    (ch / "index.md").write_text("---\nentry_prefix: B\n---\n\n# Verbs\nLOOK\n\n# Inventory\n")

    # Not a chapter (no # Verbs)
    notch = tmp_path / "notes"
    notch.mkdir()
    (notch / "index.md").write_text("# Notes\nJust some notes.\n")

    # Not a chapter (no index.md)
    (tmp_path / "empty").mkdir()

    chapters = _find_chapters(tmp_path)
    assert len(chapters) == 1
    assert chapters[0].name == "chapter-b"


def test_find_chapters_sorted(tmp_path):
    (tmp_path / "index.md").write_text("# Verbs\nLOOK\n\n# Inventory\n")
    for name in ["zeta", "alpha", "middle"]:
        d = tmp_path / name
        d.mkdir()
        (d / "index.md").write_text("# Verbs\nLOOK\n\n# Inventory\n")

    chapters = _find_chapters(tmp_path)
    assert [c.name for c in chapters] == ["alpha", "middle", "zeta"]


# ── Prefix assignment ─────────────────────────────────────────────────────────

def test_next_prefix_no_chapters(tmp_path):
    (tmp_path / "index.md").write_text("# Verbs\nLOOK\n\n# Inventory\n")
    assert _next_chapter_prefix(tmp_path) == "B"


def test_next_prefix_skips_used(tmp_path):
    (tmp_path / "index.md").write_text("# Verbs\nLOOK\n\n# Inventory\n")

    for name, prefix in [("ch-b", "B"), ("ch-c", "C")]:
        d = tmp_path / name
        d.mkdir()
        (d / "index.md").write_text(f"---\nentry_prefix: {prefix}\n---\n\n# Verbs\nLOOK\n\n# Inventory\n")

    assert _next_chapter_prefix(tmp_path) == "D"


# ── Entry prefix in compiled output ──────────────────────────────────────────

def _make_chapter(prefix):
    global_src = textwrap.dedent(f"""\
        ---
        title: Chapter {prefix}
        entry_prefix: {prefix}
        ---

        # Verbs
        LOOK

        # Inventory
    """)
    room_src = textwrap.dedent("""\
        # Room

        THING
        + LOOK: A thing.
    """)
    return global_src, [room_src]


def test_entry_prefix_in_markdown():
    global_src, room_sources = _make_chapter("B")
    game = compile_game(global_src, room_sources)
    md, _ = generate_markdown(game)
    # Ledger entries should use B- prefix
    assert "B-" in md
    # Should NOT have A- prefix
    assert "A-" not in md


def test_default_prefix_is_a():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n"
    room_src = "# Room\n\nTHING\n+ LOOK: A thing.\n"
    game = compile_game(global_src, [room_src])
    md, _ = generate_markdown(game)
    assert "A-" in md


# ── Combined chapter build (markdown) ────────────────────────────────────────

def test_combined_chapters_have_distinct_prefixes():
    """Two chapters compiled separately should have distinct prefixed entries."""
    _, rooms_a = _make_chapter("A")
    game_a = compile_game(
        "---\ntitle: Main\n---\n\n# Verbs\nLOOK\n\n# Inventory\n",
        rooms_a,
    )
    md_a, _ = generate_markdown(game_a)

    global_b, rooms_b = _make_chapter("B")
    game_b = compile_game(global_b, rooms_b)
    md_b, _ = generate_markdown(game_b)

    assert "A-" in md_a
    assert "B-" in md_b
    # Combined output has both
    combined = md_a + "\n\n---\n\n" + md_b
    assert "A-" in combined
    assert "B-" in combined
