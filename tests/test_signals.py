"""Tests for cross-chapter signals."""

import hashlib

from addventure.models import Signal, SignalCheck, Arrow, GameData


def test_signal_dataclass():
    s = Signal(name="EVERYONE_OUT_ESCAPE", id=10347)
    assert s.name == "EVERYONE_OUT_ESCAPE"
    assert s.id == 10347


def test_signal_check_dataclass():
    sc = SignalCheck(
        signal_name="EVERYONE_OUT_ESCAPE",
        narrative="A companion appears.",
        arrows=[Arrow("COMPANION", '"Forest Road"', 5)],
    )
    assert sc.signal_name == "EVERYONE_OUT_ESCAPE"
    assert sc.entry_number == 0  # default


def test_signal_check_otherwise():
    sc = SignalCheck(signal_name=None, narrative="You are alone.", arrows=[])
    assert sc.signal_name is None


def test_game_data_signal_fields():
    game = GameData()
    assert game.signals == {}
    assert game.signal_checks == []
    assert game.signal_emissions == set()


from addventure.compiler import compile_game, signal_id


def test_signal_id_deterministic():
    a = signal_id("EVERYONE_OUT_ESCAPE")
    b = signal_id("EVERYONE_OUT_ESCAPE")
    assert a == b


def test_signal_id_in_range():
    for name in ["FOO", "EVERYONE_OUT_ESCAPE", "WITNESS_ESCAPE", "A_VERY_LONG_SIGNAL_NAME"]:
        sid = signal_id(name)
        assert 10010 <= sid <= 99999, f"{name} -> {sid} out of range"


def test_signal_id_different_names_differ():
    a = signal_id("EVERYONE_OUT_ESCAPE")
    b = signal_id("WITNESS_ESCAPE")
    assert a != b


def test_parse_signals_section():
    global_src = (
        "# Verbs\nLOOK\n\n"
        "# Inventory\n\n"
        "# Signals\nEVERYONE_OUT_ESCAPE\nWITNESS_ESCAPE\n"
    )
    game = compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])
    assert "EVERYONE_OUT_ESCAPE" in game.signals
    assert "WITNESS_ESCAPE" in game.signals
    assert game.signals["EVERYONE_OUT_ESCAPE"].id == signal_id("EVERYONE_OUT_ESCAPE")


def test_parse_signals_section_empty():
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\n# Signals\n"
    game = compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])
    assert game.signals == {}


def test_parse_signals_rejects_invalid_names():
    import pytest
    from addventure.parser import ParseError
    global_src = "# Verbs\nLOOK\n\n# Inventory\n\n# Signals\nlowercase\n"
    with pytest.raises(ParseError, match="Invalid signal name"):
        compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])


def test_signal_emission_arrow():
    global_src = "# Verbs\nLOOK\nUSE\n\n# Inventory\n"
    room_src = (
        "# Room\n\n"
        "THING\n"
        "+ USE:\n"
        "  You do it.\n"
        "  - -> signal EVERYONE_OUT_ESCAPE\n"
    )
    game = compile_game(global_src, [room_src])
    assert "EVERYONE_OUT_ESCAPE" in game.signal_emissions
    # The arrow should be on the resolved interaction
    ri = [r for r in game.resolved if r.verb == "USE"][0]
    signal_arrows = [a for a in ri.arrows if a.signal_name]
    assert len(signal_arrows) == 1
    assert signal_arrows[0].signal_name == "EVERYONE_OUT_ESCAPE"


def test_signal_emission_rejects_invalid_name():
    import pytest
    from addventure.parser import ParseError
    global_src = "# Verbs\nUSE\n\n# Inventory\n"
    room_src = (
        "# Room\n\n"
        "THING\n"
        "+ USE:\n"
        "  Text.\n"
        "  - -> signal lowercase_bad\n"
    )
    with pytest.raises(ParseError, match="Invalid signal name"):
        compile_game(global_src, [room_src])


def test_parse_index_signal_checks():
    global_src = (
        "---\ntitle: Test\n---\n\n"
        "Common intro text.\n\n"
        "SIGNAL_A?\n"
        "  Branch A text.\n"
        "  - COMPANION -> \"Room\"\n"
        "SIGNAL_B?\n"
        "  Branch B text.\n"
        "otherwise?\n"
        "  Default text.\n\n"
        "# Verbs\nLOOK\n\n"
        "# Inventory\n\n"
        "# Signals\nSIGNAL_A\nSIGNAL_B\n"
    )
    game = compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])
    assert "Common intro text." in game.metadata.get("description", "")
    assert len(game.signal_checks) == 3
    assert game.signal_checks[0].signal_name == "SIGNAL_A"
    assert "Branch A" in game.signal_checks[0].narrative
    assert len(game.signal_checks[0].arrows) == 1
    assert game.signal_checks[1].signal_name == "SIGNAL_B"
    assert game.signal_checks[2].signal_name is None  # otherwise


def test_parse_index_signal_checks_no_otherwise():
    global_src = (
        "Common intro.\n\n"
        "SIGNAL_A?\n"
        "  Branch A.\n\n"
        "# Verbs\nLOOK\n\n"
        "# Inventory\n\n"
        "# Signals\nSIGNAL_A\n"
    )
    game = compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])
    assert len(game.signal_checks) == 1
    assert game.signal_checks[0].signal_name == "SIGNAL_A"


def test_parse_otherwise_before_signal_check_errors():
    import pytest
    from addventure.parser import ParseError
    global_src = (
        "otherwise?\n"
        "  Default first.\n"
        "SIGNAL_A?\n"
        "  Branch A.\n\n"
        "# Verbs\nLOOK\n\n# Inventory\n\n# Signals\nSIGNAL_A\n"
    )
    with pytest.raises(ParseError, match="otherwise\\? must be the last branch"):
        compile_game(global_src, ["# Room\n\nTHING\n+ LOOK: A thing.\n"])


def test_parse_interaction_signal_checks():
    global_src = (
        "# Verbs\nLOOK\nUSE\n\n"
        "# Inventory\n\n"
        "# Signals\nSIGNAL_A\n"
    )
    room_src = (
        "# Room\n\n"
        "THING\n"
        "+ USE:\n"
        "  Common narrative.\n"
        "  SIGNAL_A?\n"
        "    Branch A narrative.\n"
        "  otherwise?\n"
        "    Default narrative.\n"
    )
    game = compile_game(global_src, [room_src])
    # Find the USE interaction
    use_interactions = [ix for ix in game.interactions if ix.verb == "USE"]
    assert len(use_interactions) == 1
    ix = use_interactions[0]
    assert "Common narrative" in ix.narrative
    assert len(ix.signal_checks) == 2
    assert ix.signal_checks[0].signal_name == "SIGNAL_A"
    assert "Branch A" in ix.signal_checks[0].narrative
    assert ix.signal_checks[1].signal_name is None  # otherwise


def test_interaction_signal_checks_with_unconditional_arrows():
    global_src = (
        "# Verbs\nUSE\n\n"
        "# Inventory\n\n"
        "# Signals\nSIGNAL_A\n"
    )
    room_src = (
        "# Room\n\n"
        "THING\n"
        "+ USE:\n"
        "  Common text.\n"
        "  - THING -> trash\n"
        "  SIGNAL_A?\n"
        "    Signal text.\n"
        "    - BONUS -> room\n"
        "  otherwise?\n"
        "    Other text.\n"
    )
    game = compile_game(global_src, [room_src])
    ix = [i for i in game.interactions if i.verb == "USE"][0]
    assert len(ix.arrows) == 1  # Unconditional arrow
    assert ix.arrows[0].destination == "trash"
    assert len(ix.signal_checks) == 2
    assert len(ix.signal_checks[0].arrows) == 1  # Conditional arrow
    assert ix.signal_checks[0].arrows[0].subject == "BONUS"
