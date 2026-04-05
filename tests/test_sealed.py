from addventure.models import SealedText, Interaction, GameData
from addventure.compiler import compile_game
from addventure.parser import ParseError
import pytest

def test_sealed_text_dataclass():
    st = SealedText(
        ref="K-7",
        content="Secret finale text.",
        images=[],
        source_line=10,
        room="Dungeon",
    )
    assert st.ref == "K-7"
    assert st.entry_number == 0

def test_interaction_sealed_content_default():
    ix = Interaction(
        verb="USE", target_groups=[["KEY"]],
        narrative="You use the key.", room="Dungeon",
    )
    assert ix.sealed_content is None

def test_gamedata_sealed_texts_default():
    game = GameData()
    assert game.sealed_texts == []


def test_parse_sealed_block():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: sealed
  The door opens to reveal a hidden chamber.
  Ancient treasures glitter in the torchlight.
  :::
"""
    game = compile_game(global_src, [room_src])
    ix = game.interactions[0]
    assert ix.narrative == "You turn the key."
    assert ix.sealed_content == (
        "The door opens to reveal a hidden chamber.\n\n"
        "Ancient treasures glitter in the torchlight."
    )

def test_parse_sealed_block_no_outer_narrative():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  - player -> "Exit"

  ::: sealed
  Secret text only.
  :::
"""
    game = compile_game(global_src, [room_src])
    ix = game.interactions[0]
    assert ix.narrative == ""
    assert ix.sealed_content == "Secret text only."

def test_parse_sealed_fence_outside_interaction_rejected():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY

::: sealed
This should fail.
:::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])

def test_parse_multiple_sealed_blocks_rejected():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text.

  ::: sealed
  First block.
  :::

  ::: sealed
  Second block.
  :::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])
