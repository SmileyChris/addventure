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
