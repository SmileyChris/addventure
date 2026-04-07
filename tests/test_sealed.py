from addventure.models import SealedText, Interaction, GameData
from addventure.compiler import compile_game
from addventure.parser import ParseError
from addventure.writer import GameWriter
from addventure.md_writer import generate_markdown
from addventure.pdf_writer import serialize_game_data
import pytest

def test_sealed_text_dataclass():
    st = SealedText(
        ref="Alpha",
        content="Secret finale text.",
        images=[],
        source_line=10,
        room="Dungeon",
    )
    assert st.ref == "Alpha"
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
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: fragment
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
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  - player -> "Exit"

  ::: fragment
  Secret text only.
  :::
"""
    game = compile_game(global_src, [room_src])
    ix = game.interactions[0]
    assert ix.narrative == ""
    assert ix.sealed_content == "Secret text only."

def test_parse_sealed_fence_outside_interaction_rejected():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY

::: fragment
This should fail.
:::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])

def test_parse_multiple_sealed_blocks_rejected():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text.

  ::: fragment
  First block.
  :::

  ::: fragment
  Second block.
  :::
"""
    with pytest.raises(ParseError):
        compile_game(global_src, [room_src])

def test_sealed_text_created_with_ref():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.
  - player -> "Exit"

  ::: fragment
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
    # Ref format: Greek letter name (e.g. "Alpha") or "Alpha-2" for overflow
    assert st.ref == "Alpha"

def test_sealed_text_refs_unique():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  Text one.

  ::: fragment
  Sealed one.
  :::

CHEST
+ LOOK:
  Text two.

  ::: fragment
  Sealed two.
  :::
"""
    game = compile_game(global_src, [room_src])
    assert len(game.sealed_texts) == 2
    refs = {st.ref for st in game.sealed_texts}
    assert len(refs) == 2  # unique

def test_sealed_text_linked_to_entry():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: fragment
  The hidden truth.
  :::
"""
    game = compile_game(global_src, [room_src])
    st = game.sealed_texts[0]
    # Find the resolved interaction
    ri = next(r for r in game.resolved if r.verb == "USE")
    assert st.entry_number == ri.entry_number

def test_sealed_instruction_extended_ledger():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: fragment
  Secret text.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    ri = next(r for r in game.resolved if r.verb == "USE" and "KEY" in r.targets)
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Turn to Fragment *{st.ref}*" in inst for inst in instructions)

def test_sealed_instruction_jigsaw():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: fragment
  Secret text.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game, jigsaw=True)
    ri = next(r for r in game.resolved if r.verb == "USE")
    instructions = writer._generate_instructions(ri)
    st = game.sealed_texts[0]
    assert any(f"Assemble Fragment *{st.ref}*" in inst for inst in instructions)

def test_markdown_sealed_section():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: fragment
  The hidden chamber awaits.
  :::
"""
    game = compile_game(global_src, [room_src])
    md, _ = generate_markdown(game)
    st = game.sealed_texts[0]
    assert f"## Fragments" in md
    assert f"### Fragment {st.ref}" in md
    assert "The hidden chamber awaits." in md
    assert "Do not read until directed" in md


def test_serialize_sealed_texts():
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = """# Dungeon
KEY
+ USE:
  You turn the key.

  ::: fragment
  The hidden chamber.
  :::
"""
    game = compile_game(global_src, [room_src])
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert "sealed_texts" in data
    assert len(data["sealed_texts"]) == 1
    assert data["sealed_texts"][0]["content"] == "The hidden chamber."
    assert "ref" in data["sealed_texts"][0]


from addventure.jigsaw import compute_grid, interleave_pieces

def test_compute_grid_basic():
    grid = compute_grid(
        content_w_mm=160, content_h_mm=50,
        cols=4, target_cell_h_mm=25,
    )
    assert grid["cols"] == 4
    assert grid["rows"] == 2
    assert grid["cell_w_mm"] == pytest.approx(40.0)
    assert grid["cell_h_mm"] == pytest.approx(25.0)

def test_compute_grid_rounds_up():
    grid = compute_grid(
        content_w_mm=160, content_h_mm=60,
        cols=4, target_cell_h_mm=25,
    )
    # 60/25 = 2.4 → ceil = 3 rows needed to cover content
    assert grid["rows"] == 3

def test_interleave_no_adjacent():
    """Pieces should not be adjacent to their original neighbors."""
    pieces = list(range(8))  # 4x2 grid, positions 0-7
    cols = 4
    result = interleave_pieces(pieces, cols)
    assert len(result) == 8
    assert set(result) == set(pieces)
    # Check no original horizontal neighbors are adjacent in result
    for i in range(len(result) - 1):
        a, b = result[i], result[i + 1]
        # Original neighbors: same row, columns differ by 1
        a_row, a_col = divmod(a, cols)
        b_row, b_col = divmod(b, cols)
        if a_row == b_row:
            assert abs(a_col - b_col) != 1, f"Pieces {a} and {b} are original neighbors"
