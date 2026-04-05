import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure import compile_game, GameWriter
from addventure.pdf_writer import serialize_game_data, find_typst, generate_pdf


def _make_game():
    global_src = "# Verbs\nUSE\nLOOK\n\n# Items\nKEY\n"
    room_src = "# Room\nLOOK: A room.\n\nBOX\n+ LOOK: A box.\n+ USE + KEY:\n  You open it.\n  - BOX -> BOX__OPEN\n    + LOOK: An open box.\n  - KEY -> trash\n"
    return compile_game(global_src, [room_src])


def test_serialize_top_level_keys():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert set(data.keys()) == {"metadata", "verbs", "rooms", "inventory_slots", "cue_slots", "potentials", "ledger", "start_room", "entry_prefix", "blind", "jigsaw", "sealed_texts"}


def test_serialize_verbs():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    base_verbs = [v for v in data["verbs"] if "__" not in v["name"]]
    assert len(base_verbs) == 2
    assert all("name" in v and "id" in v for v in data["verbs"])


def test_serialize_rooms():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    base_rooms = [r for r in data["rooms"] if r.get("state") is None]
    assert len(base_rooms) == 1
    room = base_rooms[0]
    assert room["name"] == "Room"
    assert isinstance(room["id"], int)
    assert isinstance(room["objects"], list)
    assert isinstance(room["discovery_slots"], int)


def test_serialize_potentials():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert len(data["potentials"]) == len(game.resolved)
    assert all("sum" in p and "entry" in p for p in data["potentials"])
    sums = [p["sum"] for p in data["potentials"]]
    assert sums == sorted(sums), "Potentials should be sorted by sum"


def test_serialize_ledger():
    game = _make_game()
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    assert len(data["ledger"]) == len(game.resolved)
    for entry in data["ledger"]:
        assert "entry" in entry
        assert "narrative" in entry
        assert "instructions" in entry
        assert isinstance(entry["instructions"], list)


def test_serialize_copies_metadata():
    game = _make_game()
    game.metadata["image"] = "cover.png"
    writer = GameWriter(game)
    data = serialize_game_data(game, writer)
    data["metadata"]["image"] = "resolved/path/cover.png"
    assert game.metadata["image"] == "cover.png"


def test_find_typst():
    result = find_typst()
    assert result is None or Path(result).name.startswith("typst")


def test_generate_pdf(tmp_path):
    game = _make_game()
    output = tmp_path / "test-output.pdf"
    result, _warnings = generate_pdf(game, output)
    if find_typst() is None:
        assert result is False
    else:
        assert result is True
        assert output.exists()
        assert output.stat().st_size > 0


def test_generate_pdf_custom_theme_missing(tmp_path):
    if find_typst() is None:
        return  # skip if typst not installed
    game = _make_game()
    output = tmp_path / "test-output.pdf"
    try:
        generate_pdf(game, output, theme="nonexistent")
        assert False, "Should have raised"
    except FileNotFoundError:
        pass


def test_end_to_end_example_game(tmp_path):
    """Compile the example game and generate a PDF."""
    if find_typst() is None:
        return  # skip if typst not installed

    gd = Path(__file__).resolve().parent.parent / "games" / "example"
    gs = (gd / "index.md").read_text()
    rs = [f.read_text() for f in sorted(gd.glob("*.md")) if f.name != "index.md"]
    game = compile_game(gs, rs)

    output = tmp_path / "example.pdf"
    success, _warnings = generate_pdf(game, output, game_dir=gd)
    assert success is True
    assert output.exists()
    # PDF should have reasonable size (at least a few KB for multiple pages)
    assert output.stat().st_size > 1000
