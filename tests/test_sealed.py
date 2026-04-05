from addventure.models import SealedText, Interaction, GameData
from addventure.compiler import compile_game
from addventure.parser import ParseError
from addventure.writer import GameWriter
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

def test_sealed_text_created_with_ref():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: sealed
  Secret chamber revealed.
  :::

# Exit
"""
    game = compile_game(global_src, [room_src])
    assert len(game.sealed_texts) == 1
    st = game.sealed_texts[0]
    assert st.content == "Secret chamber revealed."
    assert st.room == "Dungeon"
    assert st.entry_number > 0
    # Ref format: letter-digit(s)
    assert len(st.ref) >= 3
    assert st.ref[0].isalpha()
    assert st.ref[1] == "-"
    assert st.ref[2:].isdigit()

def test_sealed_text_refs_unique():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text one.

  ::: sealed
  Sealed one.
  :::

CHEST
+ LOOK:
  Text two.

  ::: sealed
  Sealed two.
  :::
"""
    game = compile_game(global_src, [room_src])
    assert len(game.sealed_texts) == 2
    refs = {st.ref for st in game.sealed_texts}
    assert len(refs) == 2  # unique

def test_sealed_text_linked_to_entry():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  The hidden truth.
  :::
"""
    game = compile_game(global_src, [room_src])
    st = game.sealed_texts[0]
    # Find the resolved interaction
    ri = next(r for r in game.resolved if r.verb == "USE")
    assert st.entry_number == ri.entry_number

def test_sealed_instruction_extended_ledger():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  Secret text.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(r for r in game.resolved if r.verb == "USE" and "KEY" in r.targets)
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Turn to Sealed Text {st.ref}" in inst for inst in instructions)

def test_sealed_instruction_jigsaw():
    global_src = "# Verbs\nUSE\n\n# Items\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: sealed
  Secret text.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game, jigsaw=True)
    ri = next(r for r in game.resolved if r.verb == "USE")
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Find and assemble the {st.ref} pieces" in inst for inst in instructions)
