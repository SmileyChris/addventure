import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure.models import Cue, Arrow, GameData
from addventure.compiler import compile_game
from addventure.writer import GameWriter


def test_cue_dataclass():
    cue = Cue(
        target_room="Basement",
        narrative="A shaft of light appears.",
        arrows=[Arrow("LIGHT", "room", 5)],
        source_line=10,
        trigger_room="Control Room",
    )
    assert cue.target_room == "Basement"
    assert cue.trigger_room == "Control Room"
    assert cue.id == 0
    assert cue.sum_id == 0
    assert cue.entry_number == 0
    assert len(cue.arrows) == 1


def test_gamedata_has_cues():
    game = GameData()
    assert game.cues == []
    game.cues.append(Cue(
        target_room="X", narrative="n", arrows=[],
        source_line=1, trigger_room="Y",
    ))
    assert len(game.cues) == 1


def test_parse_cue_arrow():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    assert len(game.cues) == 1
    cue = game.cues[0]
    assert cue.target_room == "Room B"
    assert cue.trigger_room == "Room A"
    assert cue.narrative == "A gate appears."
    assert len(cue.arrows) == 1
    assert cue.arrows[0].subject == "GATE"
    assert cue.arrows[0].destination == "room"


def test_parse_multiple_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room
  - ? -> "Room C"
    A panel slides open.
    - PANEL -> room

# Room B
LOOK: B.

# Room C
LOOK: C.
"""
    game = compile_game(global_src, [room_src])
    assert len(game.cues) == 2
    targets = {c.target_room for c in game.cues}
    assert targets == {"Room B", "Room C"}


def test_cue_gets_id_and_sum():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    assert cue.id != 0, "Cue should have an allocated ID"
    assert 100 <= cue.id <= 999, "Cue ID should be in entity range"
    room_b = game.rooms["Room B"]
    assert cue.sum_id == cue.id + room_b.id


def test_cue_appears_in_resolved():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    # Find the resolved interaction for this cue
    cue_ri = [ri for ri in game.resolved if ri.sum_id == cue.sum_id]
    assert len(cue_ri) == 1
    ri = cue_ri[0]
    assert ri.narrative == "A gate appears."
    assert ri.entry_number > 0
    assert cue.entry_number == ri.entry_number


def test_cue_sum_in_collision_check():
    """Cue sums participate in collision detection."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]
    # The cue's resolved interaction should be in the resolved list
    sums = [ri.sum_id for ri in game.resolved]
    assert cue.sum_id in sums


def test_trigger_instruction_writes_cue():
    """The ledger entry that triggers a cue should say 'Write N in your Cue Checks.'"""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    cue = game.cues[0]

    # Find the USE + LEVER resolved interaction
    use_lever = [ri for ri in game.resolved if ri.verb == "USE" and "LEVER" in ri.targets]
    assert len(use_lever) == 1
    instructions = writer._generate_instructions(use_lever[0])
    cue_instr = [i for i in instructions if "Cue Checks" in i]
    assert len(cue_instr) == 1
    assert str(cue.id) in cue_instr[0]
    assert "Write" in cue_instr[0]


def test_resolution_instruction_crosses_out_cue():
    """The cue resolution ledger entry should say 'Cross out N from your Cue Checks.'"""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    A gate appears.
    - GATE -> room

# Room B
LOOK: B.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    cue = game.cues[0]

    # Find the cue's resolved interaction
    cue_ri = [ri for ri in game.resolved if ri.sum_id == cue.sum_id]
    assert len(cue_ri) == 1
    instructions = writer._generate_instructions(cue_ri[0])
    cross_out = [i for i in instructions if "Cross out" in i]
    assert len(cross_out) == 1
    assert str(cue.id) in cross_out[0]
    assert "Cue Checks" in cross_out[0]
