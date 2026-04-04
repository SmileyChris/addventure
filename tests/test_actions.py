from addventure.models import Action, Arrow, GameData


def test_action_dataclass():
    action = Action(
        name="GO_NORTH",
        room="Forest",
        narrative="You head north.",
        arrows=[Arrow("player", '"Clearing"', 5)],
        discovered=False,
    )
    assert action.name == "GO_NORTH"
    assert action.room == "Forest"
    assert action.narrative == "You head north."
    assert action.discovered is False
    assert action.ledger_id == 0
    assert len(action.arrows) == 1


def test_gamedata_has_actions():
    game = GameData()
    assert game.actions == {}
