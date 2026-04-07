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
