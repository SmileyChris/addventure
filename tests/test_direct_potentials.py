"""Tests for direct potentials — NUMBER: syntax for code/password puzzles."""

import pytest

from addventure.compiler import compile_game, check_potential_collisions
from addventure.parser import ParseError, parse_global, parse_room_file, _expand_permutations
from addventure.models import GameData, DirectPotential


GLOBAL_SRC = """---
title: Test
start: Room
---
# Verbs
LOOK
USE
ENTER
# Inventory
"""


def test_expand_permutations():
    """^DIGITS generates all unique permutations, excluding the given number."""
    perms = _expand_permutations("312", 312)
    assert perms == {123, 132, 213, 231, 321}


def test_expand_permutations_with_duplicate_digits():
    """Duplicate digits should only produce unique results."""
    perms = _expand_permutations("112", 112)
    assert perms == {121, 211}


def test_expand_permutations_skip_leading_zero():
    """Permutations starting with 0 are skipped to maintain digit count."""
    perms = _expand_permutations("012", 12)
    # 012=12 (excluded), 021=21 (leading zero, skipped), 102, 120, 201, 210
    assert perms == {102, 120, 201, 210}


def test_parse_direct_potential_in_room_body():
    """Room-level direct potential: NUMBER: at indent 0."""
    room = """# Room
LOOK: You are in a room.
312: You enter the code.
  - ^312
  - KEY -> player
"""
    game = parse_global(GLOBAL_SRC)
    parse_room_file(room, game)

    assert len(game.direct_potentials) == 1
    dp = game.direct_potentials[0]
    assert dp.number == 312
    assert dp.narrative == "You enter the code."
    assert len(dp.arrows) == 1
    assert dp.arrows[0].subject == "KEY"
    assert dp.arrows[0].destination == "player"
    assert dp.avoids == {123, 132, 213, 231, 321}
    assert 312 in game.avoided_numbers
    assert 123 in game.avoided_numbers


def test_direct_potential_under_entity_is_error():
    """Direct potentials are room-level only — nesting under an entity is invalid."""
    room = """# Room
TERMINAL
  312: You type the code.
    - ^312
"""
    game = parse_global(GLOBAL_SRC)
    with pytest.raises(ParseError):
        parse_room_file(room, game)


def test_parse_multiple_direct_potentials():
    """Multiple direct potentials in the same room."""
    room = """# Room
123: First code.
  - ^123
456: Second code.
"""
    game = parse_global(GLOBAL_SRC)
    parse_room_file(room, game)

    assert len(game.direct_potentials) == 2
    assert game.direct_potentials[0].number == 123
    assert game.direct_potentials[1].number == 456
    # Both codes and their permutation avoids are tracked
    assert 123 in game.avoided_numbers
    assert 456 in game.avoided_numbers


def test_parse_direct_potential_explicit_avoids():
    """Explicit - NUMBER avoids."""
    room = """# Room
312: The code.
  - 123
  - 456
"""
    game = parse_global(GLOBAL_SRC)
    parse_room_file(room, game)

    dp = game.direct_potentials[0]
    assert dp.avoids == {123, 456}
    assert 123 in game.avoided_numbers
    assert 456 in game.avoided_numbers


def test_parse_direct_potential_inline_narrative():
    """Narrative can be inline after the colon."""
    room = """# Room
312: The safe clicks open. You find a key.
  - KEY -> player
"""
    game = parse_global(GLOBAL_SRC)
    parse_room_file(room, game)

    dp = game.direct_potentials[0]
    assert dp.narrative == "The safe clicks open. You find a key."


def test_compile_with_direct_potential():
    """Full compile: direct potential appears in resolved interactions."""
    room = """# Room
LOOK: You are in a room.
312: You enter the code.
  - ^312
  - player -> \"Vault\"
"""
    game = compile_game(GLOBAL_SRC, [room], max_retries=200)

    # Direct potential should be in resolved
    direct_ris = [ri for ri in game.resolved if ri.is_direct]
    assert len(direct_ris) == 1
    assert direct_ris[0].sum_id == 312
    assert direct_ris[0].narrative == "You enter the code."
    assert direct_ris[0].entry_number > 0


def test_compile_avoids_prevent_collisions():
    """Avoided numbers should trigger retries if a verb+entity sum hits them."""
    room = """# Room
LOOK: You are in a room.
312: The code.
  - ^312
"""
    # With only one verb (LOOK) and a few entities, permutations should be avoidable
    game = compile_game(GLOBAL_SRC, [room], max_retries=200)

    # Check no avoided number is an authored collision
    resolved_sums = {ri.sum_id for ri in game.resolved if not ri.is_direct}
    avoided = game.avoided_numbers
    collisions = resolved_sums & avoided
    assert not collisions, f"Collisions found: {collisions}"

    # Also check full potential collisions
    pc = check_potential_collisions(game)
    avoided_collisions = [e for e in pc if "avoided" in e]
    assert not avoided_collisions, f"Avoided collisions: {avoided_collisions}"


def test_direct_potential_duplicate_number_is_error():
    """Two direct potentials with the same number should collide."""
    room = """# Room
312: First code.
312: Duplicate code.
"""
    game = parse_global(GLOBAL_SRC)
    parse_room_file(room, game)

    # Both are parsed (parsing is permissive)
    assert len(game.direct_potentials) == 2

    # But compiling should fail due to collision
    with pytest.raises(RuntimeError):
        compile_game(GLOBAL_SRC, [room], max_retries=10)


def test_invalid_permutation_pattern():
    """^ followed by non-digits is an error."""
    room = """# Room
312: Code.
  - ^abc
"""
    game = parse_global(GLOBAL_SRC)
    with pytest.raises(ParseError, match="Invalid permutation pattern"):
        parse_room_file(room, game)


def test_retry_loop_rejects_avoided_collisions():
    """Compiler retry loop catches and rejects allocations with avoided collisions."""
    # 30 objects + 3-digit code — ~53% of seeds have avoided collisions.
    # The retry loop must find a clean one.
    obj_lines = '\n'.join(f'OBJ{i}\n+ LOOK: Thing {i}.' for i in range(30))
    room = f'''# Room
LOOK: You are in a room.
{obj_lines}
312: The code.\n  - ^312\n'''
    game = compile_game(GLOBAL_SRC, [room], max_retries=200)
    # Verify no avoided collisions in the result
    from addventure.compiler import check_potential_collisions
    pc = check_potential_collisions(game)
    avoided = [e for e in pc if 'avoided' in e]
    assert not avoided, f'Avoided collisions in final result: {avoided}'
