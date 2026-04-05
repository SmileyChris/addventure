import pytest

from addventure.models import Action, Arrow, GameData, ResolvedInteraction
from addventure.compiler import compile_game
from addventure.parser import ParseError
from addventure.writer import GameWriter, _display_name
from addventure.pdf_writer import serialize_game_data
from addventure.md_writer import generate_markdown


def test_action_dataclass():
    action = Action(
        name="GO_NORTH",
        room="Forest",
        narrative="You head north.",
        arrows=[Arrow("player", '"Clearing"', 5)],
        discovered=False,
    )
    assert action.name == "GO_NORTH"
    assert action.room == "Forest"
    assert action.narrative == "You head north."
    assert action.discovered is False
    assert action.ledger_id == 0
    assert len(action.arrows) == 1


def test_gamedata_has_actions():
    game = GameData()
    assert game.actions == {}


def test_parse_room_level_action():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A dense forest.

> GO_NORTH
  You head north through the trees.
  - player -> "Clearing"

# Clearing
LOOK: A sunlit clearing.
"""
    game = compile_game(global_src, [room_src])
    assert "Forest::GO_NORTH" in game.actions
    action = game.actions["Forest::GO_NORTH"]
    assert action.name == "GO_NORTH"
    assert action.room == "Forest"
    assert action.narrative == "You head north through the trees."
    assert action.discovered is False
    assert len(action.arrows) == 1
    assert action.arrows[0].subject == "player"
    assert action.arrows[0].destination == '"Clearing"'


def test_parse_discoverable_action():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A gnarled oak.
+ USE:
  You push the tree aside.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path is revealed.
    - player -> "Cave"

# Cave
LOOK: A dark cave.
"""
    game = compile_game(global_src, [room_src])
    assert "Forest::HIDDEN_PATH" in game.actions
    action = game.actions["Forest::HIDDEN_PATH"]
    assert action.discovered is True
    assert action.narrative == "A path is revealed."
    assert len(action.arrows) == 1
    assert action.arrows[0].destination == '"Cave"'


def test_action_gets_ledger_id():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    action = game.actions["Forest::GO_NORTH"]
    assert action.ledger_id > 0


def test_action_deduplication():
    """Actions with identical arrows and compatible narratives share ledger IDs."""
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head to the clearing.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.

> GO_SOUTH
  - player -> "Forest"

# Village
LOOK: A village.

> GO_SOUTH
  You walk south to the forest.
  - player -> "Forest"
"""
    game = compile_game(global_src, [room_src])
    clearing_action = game.actions["Clearing::GO_SOUTH"]
    village_action = game.actions["Village::GO_SOUTH"]
    assert clearing_action.ledger_id == village_action.ledger_id
    assert clearing_action.narrative == "You walk south to the forest."


def test_action_dedup_different_narratives():
    """Actions with same arrows but different narratives get separate ledger IDs."""
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You walk through towering pines.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.

> GO_SOUTH
  You retrace your steps through wildflowers.
  - player -> "Forest"

# Village
LOOK: A village.

> GO_SOUTH
  You follow a dirt road south.
  - player -> "Forest"
"""
    game = compile_game(global_src, [room_src])
    clearing_action = game.actions["Clearing::GO_SOUTH"]
    village_action = game.actions["Village::GO_SOUTH"]
    assert clearing_action.ledger_id != village_action.ledger_id


def test_action_trash_instruction():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You cross the bridge.
  - player -> "Clearing"

LEVER
+ LOOK: A rusty lever.
+ USE:
  You pull the lever. The bridge collapses!
  - GO_NORTH -> trash

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "LEVER" in ri.targets)
    instructions = writer._generate_instructions(ri)
    assert any("Cross out" in inst and "GO NORTH" in inst for inst in instructions)


def test_action_ledger_entry_instructions():
    """Actions generate ledger entries with instructions like regular interactions."""
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    action = game.actions["Forest::GO_NORTH"]
    writer = GameWriter(game)
    ri = ResolvedInteraction(
        verb="ACTION", targets=[], sum_id=0,
        narrative=action.narrative, arrows=action.arrows,
        source_line=0, room=action.room, parent_label=action.name,
    )
    instructions = writer._generate_instructions(ri)
    assert any("Switch to" in inst and "Clearing" in inst for inst in instructions)


def test_discoverable_action_counts_toward_discovery_slots():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A tree.
+ USE:
  You push the tree.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path revealed.
    - player -> "Cave"

# Cave
LOOK: A cave.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    assert writer._max_discovery_slots() >= 1


def test_markdown_room_shows_actions():
    from addventure.md_writer import generate_markdown

    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    md, warnings = generate_markdown(game)
    assert "GO NORTH" in md
    entry_prefix = game.metadata.get("entry_prefix", "A")
    action = game.actions["Forest::GO_NORTH"]
    assert f"{entry_prefix}-{action.ledger_id}" in md


def test_markdown_ledger_includes_action_entries():
    from addventure.md_writer import generate_markdown

    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    md, warnings = generate_markdown(game)
    action = game.actions["Forest::GO_NORTH"]
    entry_prefix = game.metadata.get("entry_prefix", "A")
    assert f"{entry_prefix}-{action.ledger_id}" in md
    assert "You head north." in md


def test_arrow_room_context_after_player_transition():
    """Arrows after player -> 'Room' should resolve against the destination room."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

BRIDGE
+ LOOK: A rickety bridge.
+ USE:
  You cross the bridge. A fountain appears!
  - BRIDGE -> trash
  - player -> "Clearing"
  - FOUNTAIN -> room

# Clearing
LOOK: A clearing.

FOUNTAIN
+ LOOK: A sparkling fountain.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "BRIDGE" in ri.targets)
    instructions = writer._generate_instructions(ri)
    # BRIDGE -> trash should reference Forest (exit room)
    bridge_inst = next(i for i in instructions if "BRIDGE" in i)
    assert "room sheet" in bridge_inst
    # FOUNTAIN -> room should reference Clearing (entry room)
    fountain_inst = next(i for i in instructions if "FOUNTAIN" in i)
    assert "room sheet" in fountain_inst

    # The fountain ID should be from the Clearing room, not Forest
    clearing_fountain = game.nouns.get("Clearing::FOUNTAIN")
    assert clearing_fountain is not None
    assert str(clearing_fountain.id) in fountain_inst


def test_discoverable_action_instruction():
    """When an interaction reveals an action, the instruction says to write it on the room sheet."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

OLD_TREE
+ LOOK: A gnarled oak.
+ USE:
  You push the tree aside.
  - OLD_TREE -> trash
  > HIDDEN_PATH
    A path is revealed.
    - player -> "Cave"

# Cave
LOOK: A cave.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(ri for ri in game.resolved if ri.verb == "USE" and "OLD_TREE" in ri.targets)
    instructions = writer._generate_instructions(ri)
    action = game.actions["Forest::HIDDEN_PATH"]
    prefix = game.metadata.get("entry_prefix", "A")
    assert any(
        "HIDDEN PATH" in inst and f"{prefix}-{action.ledger_id}" in inst and "discovery" in inst.lower()
        for inst in instructions
    )


def test_pdf_serialization_includes_actions():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  You head north.
  - player -> "Clearing"

# Clearing
LOOK: A clearing.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    forest = next(r for r in data["rooms"] if r["name"] == "Forest")
    assert "actions" in forest
    assert len(forest["actions"]) == 1
    assert forest["actions"][0]["name"] == "GO_NORTH"
    assert forest["actions"][0]["entry"] > 0
    action_entry = game.actions["Forest::GO_NORTH"].ledger_id
    assert any(e["entry"] == action_entry for e in data["ledger"])


def test_full_action_game():
    """End-to-end test: game with pre-printed actions, discoverable actions, and action removal."""
    global_src = """---
title: Action Test
start: Village
---
# Verbs
LOOK
USE

# Items
"""
    room_src = """# Village
LOOK: A quiet village.

> GO_NORTH
  You walk north to the forest.
  - player -> "Forest"

> GO_EAST
  You head east to the river.
  - player -> "River"

# Forest
LOOK: A dense forest.

> GO_SOUTH
  You return to the village.
  - player -> "Village"

OLD_TREE
+ LOOK: A massive oak tree.
+ USE:
  You push the tree aside revealing a hidden trail.
  - OLD_TREE -> trash
  > HIDDEN_TRAIL
    - player -> "Glade"

# River
LOOK: A rushing river.

> GO_WEST
  You head back to the village.
  - player -> "Village"

BRIDGE
+ LOOK: A rope bridge.
+ USE:
  The bridge snaps behind you!
  - GO_WEST -> trash
  - player -> "Island"

# Glade
LOOK: A peaceful glade.

# Island
LOOK: A small island.
"""
    game = compile_game(global_src, [room_src])

    # Check all actions parsed
    assert "Village::GO_NORTH" in game.actions
    assert "Village::GO_EAST" in game.actions
    assert "Forest::GO_SOUTH" in game.actions
    assert "Forest::HIDDEN_TRAIL" in game.actions
    assert "River::GO_WEST" in game.actions

    # Check pre-printed vs discovered
    assert game.actions["Village::GO_NORTH"].discovered is False
    assert game.actions["Forest::HIDDEN_TRAIL"].discovered is True

    # All actions have ledger IDs
    for action in game.actions.values():
        assert action.ledger_id > 0

    # Actions should NOT appear in the potentials list
    action_ledger_ids = {a.ledger_id for a in game.actions.values()}
    for ri in game.resolved:
        assert ri.entry_number not in action_ledger_ids or ri.verb == "ACTION"

    # Markdown output succeeds
    md, warnings = generate_markdown(game)
    assert "GO NORTH" in md
    assert "GO EAST" in md
    assert "GO SOUTH" in md
    assert "GO WEST" in md

    # Ledger entries exist for actions
    entry_prefix = game.metadata.get("entry_prefix", "A")
    for action in game.actions.values():
        assert f"{entry_prefix}-{action.ledger_id}" in md


def test_action_cannot_nest_under_action():
    global_src = "# Verbs\nLOOK\n\n# Items\n"
    room_src = """# Forest
LOOK: A forest.

> GO_NORTH
  > SECRET_PATH
    - player -> "Cave"

# Cave
LOOK: A cave.
"""
    with pytest.raises(ParseError, match="cannot nest"):
        compile_game(global_src, [room_src])
