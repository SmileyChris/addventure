from addventure.models import SealedText, Interaction, GameData

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
