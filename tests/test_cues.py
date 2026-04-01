import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure.models import Cue, Arrow, GameData
from addventure.compiler import compile_game


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
