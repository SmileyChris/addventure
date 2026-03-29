"""
Addventure CLI — load .adv files and run the compiler + writer pipeline.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from addventure import compile_game, print_full_report


def load_game(game_dir: Path) -> tuple[str, list[str]]:
    """Load global.adv and all room .adv files from a game directory."""
    global_file = game_dir / "global.adv"
    if not global_file.exists():
        print(f"ERROR: No global.adv found in {game_dir}")
        sys.exit(1)

    global_source = global_file.read_text()
    room_sources = [
        f.read_text()
        for f in sorted(game_dir.glob("*.adv"))
        if f.name != "global.adv"
    ]
    return global_source, room_sources


if __name__ == "__main__":
    game_dir = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("games/example")
    global_source, room_sources = load_game(game_dir)
    game = compile_game(global_source, room_sources)
    print_full_report(game)
