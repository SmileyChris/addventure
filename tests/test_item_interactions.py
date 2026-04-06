import pytest

from addventure.models import GameData
from addventure.compiler import compile_game
from addventure import GameWriter
from addventure.parser import ParseError


def test_gamedata_has_suppressed_interactions():
    game = GameData()
    assert game.suppressed_interactions == []


def test_player_arrow_parses_inline_look():
    """+ LOOK under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick up the knife.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
"""
    game = compile_game(global_src, [room_src])
    key_item = game.inventory["KNIFE"]
    look_id = game.verbs["LOOK"].id

    # Inventory LOOK should use item-specific text, not the room object text
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + key_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."


def test_player_arrow_parses_inline_action():
    """+ USE with arrows under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + USE:
      You pry the hilt open, revealing a gem!
      - GEM -> room
"""
    game = compile_game(global_src, [room_src])
    use_id = game.verbs["USE"].id
    knife_item = game.inventory["KNIFE"]

    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 1
    assert "gem" in inv_use[0].narrative.lower()
    assert any(a.destination == "room" for a in inv_use[0].arrows)


def test_items_section_parses_interactions():
    """# Inventory with indented + lines should create item interactions."""
    global_src = """# Verbs
USE
TAKE
LOOK

# Inventory

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
"""
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    compass = game.inventory["COMPASS"]
    look_id = game.verbs["LOOK"].id
    use_id = game.verbs["USE"].id

    look_ri = [ri for ri in game.resolved if ri.sum_id == look_id + compass.id]
    assert len(look_ri) == 1
    assert look_ri[0].narrative == "A brass compass, needle spinning wildly."

    use_ri = [ri for ri in game.resolved if ri.sum_id == use_id + compass.id]
    assert len(use_ri) == 1
    assert "north" in use_ri[0].narrative.lower()


def test_items_section_plain_names_still_work():
    """# Inventory with just names (no interactions) should still work."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\nCOMPASS\nROPE\n"
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    assert "COMPASS" in game.inventory
    assert "ROPE" in game.inventory


def test_arbitrary_space_indentation_is_accepted():
    """Structure is based on deeper indentation, not 2-space buckets."""
    global_src = "# Verbs\nLOOK\nTAKE\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
 + LOOK: A brass key.
 + TAKE:
  You pocket the key.
  - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    key = game.inventory["KEY"]
    look_id = game.verbs["LOOK"].id

    inv_looks = [ri for ri in game.resolved if ri.sum_id == look_id + key.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "A brass key."


def test_tab_indentation_is_rejected():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n"
    room_src = "# Room\nLOOK: A room.\n\nKEY\n\t+ LOOK: Invalid tab indent.\n"

    with pytest.raises(ParseError, match="Tabs are not allowed for indentation"):
        compile_game(global_src, [room_src])


def test_acquisition_interaction_not_duplicated():
    """An interaction with -> player arrow should not be duplicated to inventory."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ USE:
  You grab the knife from the wall mount.
  - KNIFE -> player
"""
    game = compile_game(global_src, [room_src])
    use_id = game.verbs["USE"].id
    knife_item = game.inventory["KNIFE"]

    # USE should not be duplicated for inventory — it's the acquisition action
    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 0


def test_explicit_item_interaction_overrides_duplication():
    """An inline LOOK under -> player should replace the auto-duplicated one."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A rusty blade on the ground.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Strange markings near the hilt.
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.inventory["KNIFE"]
    look_id = game.verbs["LOOK"].id

    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."


def test_partial_override_still_duplicates_other_verbs():
    """Defining LOOK under -> player should not prevent USE from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade.
+ USE:
  You wave the knife around.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK: Blade with markings.
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.inventory["KNIFE"]
    use_id = game.verbs["USE"].id
    look_id = game.verbs["LOOK"].id

    # LOOK should be the explicit one
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Blade with markings."

    # USE should still be duplicated (not overridden)
    inv_use = [ri for ri in game.resolved
               if ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 1
    assert inv_use[0].narrative == "You wave the knife around."


def test_empty_interaction_suppresses_duplication():
    """+ LOOK: with no text should prevent LOOK from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KNIFE
+ LOOK: A blade on the ground.
+ TAKE:
  You pick it up.
  - KNIFE -> player
    + LOOK:
"""
    game = compile_game(global_src, [room_src])
    knife_item = game.inventory["KNIFE"]
    look_id = game.verbs["LOOK"].id

    # No inventory LOOK should exist — suppressed by empty interaction
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 0


def test_stated_noun_to_player_registers_base_item():
    """KEY__HIDDEN -> player should register item as KEY, not KEY__HIDDEN."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

KEY
+ LOOK: A brass key.

KEY__HIDDEN
+ LOOK: Something glints in the shadows.
+ USE:
  You reach in and grab it.
  - KEY__HIDDEN -> trash
  - KEY -> room
    + TAKE:
      You pocket the key.
      - KEY -> player
"""
    game = compile_game(global_src, [room_src])
    assert "KEY" in game.inventory
    assert "KEY__HIDDEN" not in game.inventory
    assert "KEY" in game.auto_inventory


def test_stated_noun_direct_to_player_registers_base_item():
    """GEM__ROUGH -> player should register item as GEM."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

GEM
+ LOOK: A gem.

GEM__ROUGH
+ LOOK: An uncut gem.
+ TAKE:
  You pocket the rough gem.
  - GEM__ROUGH -> player
"""
    game = compile_game(global_src, [room_src])
    assert "GEM" in game.inventory
    assert "GEM__ROUGH" not in game.inventory


def test_noun_revealed_under_entity_state_is_discovery():
    """Nouns revealed via -> room under an entity state transform should not
    appear as initial objects — they're discoveries."""
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Room
LOOK: A room.

BOX
+ LOOK: A locked box.
+ USE:
  You open the box.
  - BOX -> BOX__OPEN
    + LOOK: The box is open. A gem and a note lie inside.
    - GEM -> room
    - NOTE -> room

GEM
+ LOOK: A sparkling gem.

NOTE
+ LOOK: A crumpled note.
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    initial = writer._initial_objects("Room")
    initial_names = [n.name for n in initial]
    assert "BOX" in initial_names
    assert "GEM" not in initial_names
    assert "NOTE" not in initial_names
    # GEM and NOTE should be marked discovered
    assert game.objects["Room::GEM"].discovered is True
    assert game.objects["Room::NOTE"].discovered is True
    # The interaction should have the -> room arrows propagated
    use_ix = next(ix for ix in game.interactions if ix.verb == "USE" and ix.room == "Room")
    arrow_subjects = [a.subject for a in use_ix.arrows]
    assert "GEM" in arrow_subjects
    assert "NOTE" in arrow_subjects


def test_state_revert_generates_transform_instruction():
    """DOOR__LOCKED -> DOOR should generate a 'Change' instruction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Inventory\nKEY\n"
    room_src = """# Room
LOOK: A room.

DOOR
+ LOOK: A wooden door.

DOOR__LOCKED
+ LOOK: A locked door.
+ USE + KEY:
  You unlock the door.
  - DOOR__LOCKED -> DOOR
  - KEY -> trash
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)

    door_base = game.objects["Room::DOOR"]
    ri = next(ri for ri in game.resolved
              if ri.narrative == "You unlock the door.")
    instructions = writer._generate_instructions(ri)
    assert any("Change" in i and str(door_base.id) in i for i in instructions)
