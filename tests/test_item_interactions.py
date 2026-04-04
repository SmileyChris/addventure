from addventure.models import GameData


def test_gamedata_has_suppressed_interactions():
    game = GameData()
    assert game.suppressed_interactions == []
