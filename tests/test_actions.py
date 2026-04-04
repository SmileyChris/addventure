from addventure.models import Action, Arrow, GameData, ResolvedInteraction
from addventure.compiler import compile_game
from addventure.writer import GameWriter, _display_name


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
