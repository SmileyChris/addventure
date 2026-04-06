import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure.models import Cue, Arrow, GameData
from addventure.compiler import compile_game
from addventure.md_writer import generate_markdown
from addventure.pdf_writer import serialize_game_data
from addventure.writer import GameWriter


def _make_game_with_cues(cue_count: int):
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_lines = ["# Room A", "LOOK: A."]
    for idx in range(1, cue_count + 1):
        room_lines.extend([
            "",
            f"TRIGGER_{idx}",
            "+ USE:",
            f"  Trigger cue {idx}.",
            f'  - ? -> "Room B{idx}"',
            f"    Cue {idx}.",
        ])
    for idx in range(1, cue_count + 1):
        room_lines.extend([
            "",
            f"# Room B{idx}",
            f"LOOK: B{idx}.",
        ])
    return compile_game(global_src, ["\n".join(room_lines) + "\n"])


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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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


def test_inventory_sheet_has_cue_checks_when_cues_exist():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    md, _warnings = generate_markdown(game)
    assert "### Cue Checks" in md
    assert "Cue Checks" in md


def test_inventory_sheet_no_cue_checks_without_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\nKEY\n"
    room_src = """# Room
LOOK: A room.

BOX
+ LOOK: A box.
+ USE + KEY:
  You open it.
  - BOX -> BOX__OPEN
    + LOOK: Open box.
  - KEY -> trash
"""
    game = compile_game(global_src, [room_src])
    md, _warnings = generate_markdown(game)
    assert "### Cue Checks" not in md


@pytest.mark.parametrize(
    ("cue_count", "expected_placeholders", "expected_rows"),
    [
        (1, 6, 1),
        (6, 6, 1),
        (7, 7, 2),
        (11, 11, 2),
        (12, 12, 2),
        (13, 13, 3),
    ],
)
def test_cue_checks_table_scales_cleanly(cue_count, expected_placeholders, expected_rows):
    game = _make_game_with_cues(cue_count)
    md, _warnings = generate_markdown(game)

    cue_section = md.split("### Cue Checks", 1)[1].split("### Master Potentials List", 1)[0]
    table_lines = [line for line in cue_section.splitlines() if line.startswith("|")]

    assert len(table_lines) == expected_rows + 1
    assert table_lines[1] == "| ---: | ---: | ---: | ---: | ---: | ---: |"
    assert md.count("`____`") >= expected_placeholders

    for line in table_lines:
        assert line.count("|") == 7

    cue_rows = [line for idx, line in enumerate(table_lines) if idx != 1]
    assert sum(line.count("`____`") for line in cue_rows) == expected_placeholders


def test_serialize_includes_cue_slots():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    data = serialize_game_data(game, writer)
    assert "cue_slots" in data
    assert data["cue_slots"] > 0


def test_serialize_no_cue_slots_without_cues():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\nKEY\n"
    room_src = """# Room
LOOK: A room.

BOX
+ LOOK: A box.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert data["cue_slots"] == 0


def test_cue_resolves_in_all_room_states():
    """A cue targeting 'Room B' resolves in base AND all states of Room B."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    Something changed.
    - WIDGET -> room

SWITCH
+ LOOK: A switch.
+ USE:
  You flip the switch.
  - room -> room__DARK

# Room A__DARK
LOOK: It is dark.

# Room B
LOOK: B.

BUTTON
+ USE:
  You press the button.
  - room -> room__FLOODED

# Room B__FLOODED
LOOK: Water everywhere.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]

    # Should have resolved interactions for base Room B AND Room B__FLOODED
    room_b = game.rooms["Room B"]
    room_b_flooded = game.rooms["Room B__FLOODED"]

    cue_sums = {ri.sum_id for ri in game.resolved if ri.verb == "CUE"}
    assert cue.id + room_b.id in cue_sums
    assert cue.id + room_b_flooded.id in cue_sums

    # All cue resolved interactions should share the same entry number
    cue_entries = {ri.entry_number for ri in game.resolved if ri.verb == "CUE"}
    assert len(cue_entries) == 1


def test_cue_targets_specific_room_state():
    """A cue targeting 'Room B__FLOODED' only resolves in that state."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B__FLOODED"
    The water reveals something.
    - WIDGET -> room

# Room B
LOOK: B.

BUTTON
+ USE:
  You press the button.
  - room -> room__FLOODED

# Room B__FLOODED
LOOK: Water everywhere.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]

    room_b = game.rooms["Room B"]
    room_b_flooded = game.rooms["Room B__FLOODED"]

    cue_sums = {ri.sum_id for ri in game.resolved if ri.verb == "CUE"}
    # Only the flooded state should match
    assert cue.id + room_b_flooded.id in cue_sums
    assert cue.id + room_b.id not in cue_sums


def test_cue_targets_base_state_only():
    """A cue targeting 'Room B__' only resolves in the base state."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B__"
    Something in the calm water.
    - WIDGET -> room

# Room B
LOOK: B.

BUTTON
+ USE:
  You press the button.
  - room -> room__FLOODED

# Room B__FLOODED
LOOK: Water everywhere.
"""
    game = compile_game(global_src, [room_src])
    cue = game.cues[0]

    room_b = game.rooms["Room B"]
    room_b_flooded = game.rooms["Room B__FLOODED"]

    cue_sums = {ri.sum_id for ri in game.resolved if ri.verb == "CUE"}
    # Only the base state should match
    assert cue.id + room_b.id in cue_sums
    assert cue.id + room_b_flooded.id not in cue_sums


def test_cue_all_states_no_duplicate_ledger():
    """A cue resolving in multiple states should produce only one ledger entry."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A room.

LEVER
+ LOOK: A lever.
+ USE:
  You pull the lever.
  - ? -> "Room B"
    Something changed.
    - WIDGET -> room

# Room B
LOOK: B.

BUTTON
+ USE:
  You press the button.
  - room -> room__FLOODED

# Room B__FLOODED
LOOK: Water everywhere.
"""
    game = compile_game(global_src, [room_src])
    ledger, _warnings = generate_markdown(game)
    # "Something changed." should appear exactly once in the ledger
    assert ledger.count("Something changed.") == 1


def test_room_sheet_no_alerts():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
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
    sheet, _warnings = generate_markdown(game)
    assert "Alert" not in sheet
    assert "alert" not in sheet


def test_unknown_target_does_not_resolve_from_another_room():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A.

KEY
+ LOOK: A key.

# Room B
LOOK: B.

DOOR
+ USE + KEY:
  It unlocks.
"""
    try:
        compile_game(global_src, [room_src])
        assert False, "Should have raised for KEY missing from Room B"
    except Exception as e:
        assert "Unknown target: KEY" in str(e)


def test_compile_requires_positive_retry_budget():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n"
    room_src = "# Room\nLOOK: A.\n"
    try:
        compile_game(global_src, [room_src], max_retries=0)
        assert False, "Should reject zero allocation attempts"
    except ValueError as e:
        assert "max_retries" in str(e)


def test_reachability_applies_verb_reveals_from_cues():
    from addventure.validator import validate_reachability

    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A.

LEVER
+ USE:
  Pull.
  - ? -> "Room B"
    Unlocking a new verb.
    -  -> TAKE

DOOR
+ USE:
  Enter B.
  - player -> "Room B"

# Room B
LOOK: B.
CHEST
+ TAKE:
  You take it somehow.
"""
    game = compile_game(global_src, [room_src])
    warnings = validate_reachability(game)
    assert not any("TAKE + CHEST" in warning for warning in warnings)


def test_base_state_cue_objects_are_not_rendered_as_initial_objects():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A.

LEVER
+ USE:
  Pull.
  - ? -> "Room B__"
    A gate appears.
    - GATE -> room

DOOR
+ USE:
  Enter B.
  - player -> "Room B"

# Room B
LOOK: B.
GATE
+ LOOK: The gate is here.
"""
    game = compile_game(global_src, [room_src])
    markdown, _warnings = generate_markdown(game)
    room_b = next(r for r in serialize_game_data(game, GameWriter(game))["rooms"] if r["name"] == "Room B")

    assert "| GATE |" not in markdown
    assert room_b["objects"] == []


def test_auto_register_item_from_player_arrow():
    """A room object with -> player should auto-create an Item."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    assert "KEY" in game.inventory


def test_auto_register_requires_take_verb():
    """Compiler should error if -> player exists but no TAKE verb."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ USE:
  You grab it.
  - KEY -> player
"""
    try:
        compile_game(global_src, [room_src])
        assert False, "Should have raised"
    except Exception as e:
        assert "TAKE" in str(e)


def test_auto_register_name_collision_across_rooms():
    """Two room objects with same name in different rooms both with -> player should error."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room A
LOOK: A.

LEVER
+ TAKE:
  You take it.
  - LEVER -> player

# Room B
LOOK: B.

LEVER
+ TAKE:
  You take it.
  - LEVER -> player
"""
    try:
        compile_game(global_src, [room_src])
        assert False, "Should have raised"
    except Exception as e:
        assert "LEVER" in str(e)


def test_explicit_item_skips_auto_register():
    """If an item is declared in # Inventory, auto-registration is skipped."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\nKEY\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You pick it up.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key_item = game.inventory["KEY"]
    # Explicit item keeps its own allocated ID (from entity pool, 100-999)
    assert 100 <= key_item.id <= 999


def test_auto_item_id_derived_from_take():
    """Auto-registered item ID should be TAKE_id + noun_id."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key_noun = game.objects["Room::KEY"]
    key_item = game.inventory["KEY"]
    take_id = game.verbs["TAKE"].id
    assert key_item.id == take_id + key_noun.id


def test_auto_item_id_not_in_entity_ids():
    """The derived inventory ID should not collide with any other entity ID."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player

BOX
+ LOOK: A box.
"""
    game = compile_game(global_src, [room_src])
    key_item = game.inventory["KEY"]
    all_entity_ids = set()
    for n in game.objects.values():
        all_entity_ids.add(n.id)
    for r in game.rooms.values():
        all_entity_ids.add(r.id)
    assert key_item.id not in all_entity_ids


def test_interactions_duplicated_for_inventory_id():
    """LOOK + room object and LOOK + inventory_id should both appear in resolved."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key_noun = game.objects["Room::KEY"]
    key_item = game.inventory["KEY"]
    look_id = game.verbs["LOOK"].id

    # LOOK + room object_id should exist
    noun_look = [ri for ri in game.resolved
                 if ri.sum_id == look_id + key_noun.id and ri.narrative == "A brass key."]
    assert len(noun_look) == 1

    # LOOK + inventory_id should also exist (same narrative)
    inv_look = [ri for ri in game.resolved
                if ri.sum_id == look_id + key_item.id and ri.narrative == "A brass key."]
    assert len(inv_look) == 1


def test_take_interaction_is_not_duplicated_for_inventory_id():
    """TAKE should only resolve against the room object, not the inventory copy."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.
+ TAKE:
  You pick up the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    take_entries = [ri for ri in game.resolved if ri.verb == "TAKE" and ri.targets == ["KEY"]]
    assert len(take_entries) == 1


def test_multi_target_duplicated_for_inventory_id():
    """USE + DOOR + KEY should work with both room object and inventory KEY IDs."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player

DOOR
+ LOOK: A locked door.
+ USE + KEY:
  You unlock the door.
  - DOOR -> trash
"""
    game = compile_game(global_src, [room_src])
    key_item = game.inventory["KEY"]
    use_id = game.verbs["USE"].id
    door_id = game.objects["Room::DOOR"].id
    key_noun_id = game.objects["Room::KEY"].id

    # USE + DOOR + KEY(room object) should exist
    noun_sum = use_id + door_id + key_noun_id
    assert any(ri.sum_id == noun_sum for ri in game.resolved)

    # USE + DOOR + KEY(inventory) should also exist
    inv_sum = use_id + door_id + key_item.id
    assert any(ri.sum_id == inv_sum for ri in game.resolved)


def test_pickup_instruction_uses_inventory_id():
    """The pickup instruction should reference the inventory ID, not the room object ID."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    key_noun = game.objects["Room::KEY"]

    # Find the TAKE + KEY resolved interaction (using room object ID, not inventory ID)
    take_ri = [ri for ri in game.resolved
               if ri.verb == "TAKE" and "KEY" in ri.targets
               and ri.sum_id == game.verbs["TAKE"].id + key_noun.id]
    assert len(take_ri) == 1
    instructions = writer._generate_instructions(take_ri[0])

    # Direct TAKE pickup should not restate the already-computed room object ID
    assert any("Cross out KEY on this room sheet." in inst for inst in instructions)
    assert not any(str(key_noun.id) in inst for inst in instructions)
    # Should mention writing to Inventory
    assert any("Inventory" in inst for inst in instructions)


def test_pickup_via_take_says_write_your_sum():
    """When pickup is triggered by TAKE directly, use 'Write your sum'."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A key.
+ TAKE:
  You grab it.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    key_noun = game.objects["Room::KEY"]

    take_ri = [ri for ri in game.resolved
               if ri.verb == "TAKE" and "KEY" in ri.targets
               and ri.sum_id == game.verbs["TAKE"].id + key_noun.id]
    assert len(take_ri) == 1
    instructions = writer._generate_instructions(take_ri[0])
    inv_instr = [i for i in instructions if "Inventory" in i]
    assert len(inv_instr) == 1
    assert "your sum" in inv_instr[0].lower()


def test_pickup_via_other_verb_states_id_explicitly():
    """When pickup is triggered by a non-TAKE verb, state the inventory ID."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

CRATE
+ LOOK: A crate.
+ USE:
  You smash it open. A gem falls out.
  - GEM -> player

GEM
+ LOOK: A sparkling gem.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    gem_item = game.inventory["GEM"]

    # Find USE + CRATE (which triggers GEM -> player)
    use_crate = [ri for ri in game.resolved
                 if ri.verb == "USE" and "CRATE" in ri.targets]
    assert len(use_crate) >= 1
    instructions = writer._generate_instructions(use_crate[0])
    inv_instr = [i for i in instructions if "Inventory" in i]
    assert len(inv_instr) == 1
    # Should state the number explicitly, not "your sum"
    assert str(gem_item.id) in inv_instr[0]
