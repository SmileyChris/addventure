from addventure.models import GameData
from addventure.compiler import compile_game


def test_gamedata_has_suppressed_interactions():
    game = GameData()
    assert game.suppressed_interactions == []


def test_player_arrow_parses_inline_look():
    """+ LOOK under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
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
    key_item = game.items["KNIFE"]
    look_id = game.verbs["LOOK"].id

    # Inventory LOOK should use item-specific text, not the room noun text
    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + key_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."


def test_player_arrow_parses_inline_action():
    """+ USE with arrows under -> player should create an item interaction."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
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
    knife_item = game.items["KNIFE"]

    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 1
    assert "gem" in inv_use[0].narrative.lower()
    assert any(a.destination == "room" for a in inv_use[0].arrows)


def test_items_section_parses_interactions():
    """# Items with indented + lines should create item interactions."""
    global_src = """# Verbs
USE
TAKE
LOOK

# Items

COMPASS
  + LOOK: A brass compass, needle spinning wildly.
  + USE:
    The compass settles, pointing north.
"""
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    compass = game.items["COMPASS"]
    look_id = game.verbs["LOOK"].id
    use_id = game.verbs["USE"].id

    look_ri = [ri for ri in game.resolved if ri.sum_id == look_id + compass.id]
    assert len(look_ri) == 1
    assert look_ri[0].narrative == "A brass compass, needle spinning wildly."

    use_ri = [ri for ri in game.resolved if ri.sum_id == use_id + compass.id]
    assert len(use_ri) == 1
    assert "north" in use_ri[0].narrative.lower()


def test_items_section_plain_names_still_work():
    """# Items with just names (no interactions) should still work."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\nCOMPASS\nROPE\n"
    room_src = """# Room
LOOK: A room.
"""
    game = compile_game(global_src, [room_src])
    assert "COMPASS" in game.items
    assert "ROPE" in game.items


def test_acquisition_interaction_not_duplicated():
    """An interaction with -> player arrow should not be duplicated to inventory."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
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
    knife_item = game.items["KNIFE"]

    # USE should not be duplicated for inventory — it's the acquisition action
    inv_use = [ri for ri in game.resolved
               if ri.verb == "USE" and ri.sum_id == use_id + knife_item.id]
    assert len(inv_use) == 0


def test_explicit_item_interaction_overrides_duplication():
    """An inline LOOK under -> player should replace the auto-duplicated one."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
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
    knife_item = game.items["KNIFE"]
    look_id = game.verbs["LOOK"].id

    inv_looks = [ri for ri in game.resolved
                 if ri.sum_id == look_id + knife_item.id]
    assert len(inv_looks) == 1
    assert inv_looks[0].narrative == "Strange markings near the hilt."


def test_partial_override_still_duplicates_other_verbs():
    """Defining LOOK under -> player should not prevent USE from being duplicated."""
    global_src = "# Verbs\nUSE\nTAKE\nLOOK\n\n# Items\n"
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
    knife_item = game.items["KNIFE"]
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
