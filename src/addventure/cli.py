"""
Addventure CLI — `adv run [dir]` and `adv new [dir]`.
"""

import sys
from pathlib import Path

from . import compile_game, print_full_report, generate_pdf, find_typst


def load_game(game_dir: Path) -> tuple[str, list[str]]:
    """Load index.md and all room .md files from a game directory."""
    index_file = game_dir / "index.md"
    if not index_file.exists():
        print(f"ERROR: No index.md found in {game_dir}")
        sys.exit(1)

    global_source = index_file.read_text()
    room_sources = [
        f.read_text()
        for f in sorted(game_dir.glob("*.md"))
        if f.name != "index.md"
    ]
    return global_source, room_sources


def cmd_run(args: list[str]):
    """Compile a game and output PDF (default) or text."""
    import argparse
    parser = argparse.ArgumentParser(prog="adv run", description="Compile and output a game")
    parser.add_argument("game_dir", nargs="?", default="games/example",
                        help="Path to game directory (default: games/example)")
    parser.add_argument("--text", action="store_true",
                        help="Output plain text instead of PDF")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PDF path (default: <game_name>.pdf)")
    parser.add_argument("--theme", type=str, default="default",
                        help="Typst template theme (default: default)")
    parsed = parser.parse_args(args)

    game_dir = Path(parsed.game_dir)
    global_source, room_sources = load_game(game_dir)
    game = compile_game(global_source, room_sources)

    if parsed.text:
        print_full_report(game)
        return

    if find_typst() is None:
        print("WARNING: typst not found on PATH, falling back to text output",
              file=sys.stderr)
        print_full_report(game)
        return

    output_path = Path(parsed.output) if parsed.output else Path(f"{game_dir.name}.pdf")
    if generate_pdf(game, output_path, theme=parsed.theme):
        print(f"PDF written to {output_path}")


def cmd_new(args: list[str]):
    """Scaffold a new game directory with index.md."""
    if not args:
        print("Usage: adv new <directory>")
        sys.exit(1)

    game_dir = Path(args[0])

    if (game_dir / "index.md").exists():
        print(f"ERROR: {game_dir / 'index.md'} already exists")
        sys.exit(1)

    title = input("Game title: ").strip()
    author = input("Author: ").strip()
    default_verbs = "LOOK, USE, TAKE"
    verbs_input = input(f"Starting verbs (comma-separated, default: {default_verbs}): ").strip()
    verbs = [v.strip() for v in (verbs_input or default_verbs).split(",")]

    game_dir.mkdir(parents=True, exist_ok=True)

    lines = ["---"]
    if title:
        lines.append(f"title: {title}")
    if author:
        lines.append(f"author: {author}")
    lines.append("---")
    lines.append("")
    lines.append("# Verbs")
    for v in verbs:
        lines.append(v)
    lines.append("")
    lines.append("# Items")
    lines.append("")

    (game_dir / "index.md").write_text("\n".join(lines) + "\n")
    print(f"\nCreated {game_dir / 'index.md'}")


COMMANDS = {
    "run": cmd_run,
    "new": cmd_new,
}

USAGE = """\
Usage: adv <command> [args]

Commands:
  run [dir] [--text] [-o FILE] [--theme NAME]
                     Compile game to PDF (default) or text
  new <dir>          Scaffold a new game directory with index.md\
"""


def main():
    args = sys.argv[1:]

    if not args:
        print(USAGE)
        sys.exit(0)

    cmd_name = args[0]
    if cmd_name in ("-h", "--help"):
        print(USAGE)
        sys.exit(0)

    cmd = COMMANDS.get(cmd_name)
    if cmd:
        cmd(args[1:])
    else:
        # Backwards compat: bare directory arg = run
        cmd_run(args)
