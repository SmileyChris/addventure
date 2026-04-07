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
