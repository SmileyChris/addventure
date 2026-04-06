"""Tests for parser strictness — room root and global root reject unexpected lines."""

import pytest

from addventure.compiler import compile_game
from addventure.parser import ParseError, parse_global, parse_room_file
from addventure.models import GameData


GLOBAL_SRC = "# Verbs\nLOOK\n\n# Inventory\n"


# ── Room root strictness ──────────────────────────────────────────────────────


def test_room_rejects_stray_dash_line():
    room_src = "# Forest\n- some stray line\n"
    with pytest.raises(ParseError, match="Unexpected line in room body"):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_rejects_stray_plus_line():
    room_src = "# Forest\n+ orphan interaction\n"
    with pytest.raises(ParseError, match="Unexpected line in room body"):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_rejects_stray_plain_text():
    room_src = "# Forest\nJust some random text here.\n"
    with pytest.raises(ParseError):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_rejects_wrongly_indented_interaction():
    room_src = "# Forest\n  LOOK: A forest.\n"
    with pytest.raises(ParseError, match="Unexpected line in room body"):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_rejects_equals_label_line():
    room_src = "# Forest\n= Forest Display Name\n"
    with pytest.raises(ParseError):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_allows_valid_content():
    """Valid room body lines should still parse correctly."""
    room_src = """# Forest
LOOK: A dense forest.
CRATE
  + LOOK: A wooden crate.
  - CRATE -> CRATE__OPEN
    CRATE__OPEN
      + LOOK: The crate is open.
> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "Forest" in game.rooms
    assert "Clearing" in game.rooms


def test_room_allows_comments_and_blank_lines():
    room_src = "# Forest\n\n// a comment\nLOOK: A forest.\n"
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "Forest" in game.rooms


# ── Room file root strictness ─────────────────────────────────────────────────


def test_room_file_rejects_stray_line_before_header():
    room_src = "some stray line\n# Forest\nLOOK: A forest.\n"
    with pytest.raises(ParseError, match="Unexpected line in room file"):
        compile_game(GLOBAL_SRC, [room_src])


def test_room_file_rejects_stray_line_between_rooms():
    room_src = "# Forest\nLOOK: A forest.\n\nstray text\n\n# Clearing\nLOOK: A clearing.\n"
    with pytest.raises(ParseError):
        compile_game(GLOBAL_SRC, [room_src])


# ── Global root strictness ────────────────────────────────────────────────────


def test_global_rejects_stray_line_between_sections():
    """Stray text between # Verbs and # Inventory is caught by the verbs parser."""
    global_src = "# Verbs\nLOOK\n\nstray text\n\n# Inventory\n"
    with pytest.raises(ParseError):
        parse_global(global_src)


def test_global_rejects_stray_text_after_items():
    """Stray text after # Inventory is caught by the items section parser."""
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\nstray text after sections\n"
    with pytest.raises(ParseError):
        parse_global(global_src)


def test_global_rejects_stray_arrow_after_items():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\nFOO -> BAR\n"
    with pytest.raises(ParseError, match="Invalid inventory object declaration"):
        parse_global(global_src)


def test_global_rejects_stray_action_after_items():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\n> GO_NORTH\n"
    with pytest.raises(ParseError, match="Invalid inventory object declaration"):
        parse_global(global_src)


def test_global_rejects_unknown_section():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\n# Unknown\n"
    with pytest.raises(ParseError, match="Unknown global section"):
        parse_global(global_src)


# ── Frontmatter key warnings ──────────────────────────────────────────────────


def test_unknown_frontmatter_key_warns():
    global_src = "---\ntitle: Test\nfoobar: baz\n---\n# Verbs\nLOOK\n\n# Inventory\n"
    game = parse_global(global_src)
    assert any("Unknown frontmatter key: foobar" in w for w in game.warnings)


def test_known_frontmatter_keys_no_warnings():
    global_src = "---\ntitle: Test\nauthor: Me\nstart: Forest\nname_style: title\n---\n# Verbs\nLOOK\n\n# Inventory\n"
    game = parse_global(global_src)
    assert game.warnings == []


# ── Room name rules ───────────────────────────────────────────────────────────


def test_room_name_is_free_text():
    """Room names accept any non-empty text after '# '."""
    room_src = "# The Grand Hall (2nd Floor)\nLOOK: A grand hall.\n"
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "The Grand Hall (2nd Floor)" in game.rooms


def test_room_name_whitespace_trimmed():
    """Leading/trailing whitespace is trimmed from room names."""
    room_src = "#   Spaced Room   \nLOOK: A room.\n"
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "Spaced Room" in game.rooms


def test_quoted_room_target_matches_exactly():
    """Quoted room targets must match room names exactly."""
    room_src = '# Forest\nLOOK: Trees.\nplayer -> "The Cave"\n\n# The Cave\nLOOK: Dark.\n'
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "Forest" in game.rooms
    assert "The Cave" in game.rooms


def test_room_name_with_special_chars():
    """Room names can contain characters that would be invalid in identifiers."""
    room_src = "# Room #3: The Lab\nLOOK: Science.\n"
    game = compile_game(GLOBAL_SRC, [room_src])
    assert "Room #3: The Lab" in game.rooms


# ── Valid content acceptance ──────────────────────────────────────────────────


def test_global_allows_valid_content():
    global_src = """---
title: Test
---

A game description.

# Verbs
LOOK
USE

// a comment between sections

# Inventory
KEY
"""
    game = parse_global(global_src)
    assert "LOOK" in game.verbs
    assert "KEY" in game.inventory
