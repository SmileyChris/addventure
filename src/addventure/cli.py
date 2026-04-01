"""
Addventure CLI — `adv run [dir]` and `adv new [name]`.
"""

import re
import sys
from pathlib import Path

from . import compile_game, print_build_summary, generate_pdf, find_typst, generate_markdown


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


def cmd_build(args: list[str]):
    """Compile a game and output PDF (default) or markdown."""
    import argparse
    parser = argparse.ArgumentParser(prog="adv build", description="Compile and output a game")
    parser.add_argument("game_dir", nargs="?", default=None,
                        help="Path to game directory (default: cwd if index.md exists, else games/example)")
    parser.add_argument("--markdown", "--md", action="store_true",
                        help="Output markdown to stdout (use -o to write to file)")
    parser.add_argument("--output", "-o", type=str, default=None,
                        help="Output PDF path (default: <game_name>.pdf)")
    parser.add_argument("--theme", type=str, default="default",
                        help="Typst template theme (default: default)")
    parser.add_argument("--paper", type=str, default=None,
                        help="Paper size: a4, letter (default: a4)")
    parser.add_argument("--blind", action="store_true",
                        help="Blind mode: room sheets hide names/IDs until discovered via LOOK")
    parsed = parser.parse_args(args)

    if parsed.game_dir:
        game_dir = Path(parsed.game_dir)
    elif _in_game_dir():
        game_dir = Path(".")
    elif Path("games/example").is_dir():
        game_dir = Path("games/example")
    else:
        print("ERROR: No game directory specified and not in a game directory")
        print("Usage: adv build [dir]")
        sys.exit(1)
    global_source, room_sources = load_game(game_dir)
    game = compile_game(global_source, room_sources)

    if parsed.markdown:
        md = generate_markdown(game, blind=parsed.blind)
        if parsed.output:
            Path(parsed.output).write_text(md)
            print(f"Markdown written to {parsed.output}", file=sys.stderr)
        else:
            print(md, end="")
    else:
        if find_typst() is None:
            print("ERROR: typst not found on PATH (needed for PDF output)",
                  file=sys.stderr)
            print("  Install typst: https://github.com/typst/typst",
                  file=sys.stderr)
            print("  Or use: adv build --md", file=sys.stderr)
            sys.exit(1)

        if parsed.output:
            output_path = Path(parsed.output)
        else:
            name = game.metadata.get("title") or game_dir.resolve().name
            output_path = Path(f"{_slugify(name)}.pdf")
        if generate_pdf(game, output_path, theme=parsed.theme, game_dir=game_dir.resolve(), paper=parsed.paper, blind=parsed.blind):
            print(f"PDF written to {output_path}", file=sys.stderr)

    print_build_summary(game)


def _slugify(name: str) -> str:
    """Convert a name to a directory-friendly slug: lowercase, hyphens, no special chars."""
    slug = name.lower().strip()
    slug = re.sub(r'[^a-z0-9\s-]', '', slug)
    slug = re.sub(r'[\s_]+', '-', slug)
    slug = re.sub(r'-+', '-', slug).strip('-')
    return slug


def _resolve_game_dir(name: str) -> Path:
    """Resolve a game name to a directory path.
    If the name is a bare name (no separators) and we're in the project root
    (games/ directory exists), put it under games/.
    """
    slug = _slugify(name)
    path = Path(name)
    if path.is_absolute() or "/" in name or "\\" in name:
        return path
    if Path("games").is_dir():
        return Path("games") / slug
    return Path(slug)


def _in_game_dir() -> bool:
    """Check if cwd is inside an addventure game directory.
    Looks for index.md containing a # Verbs header.
    """
    index = Path("index.md")
    if not index.is_file():
        return False
    try:
        content = index.read_text()
        return "# Verbs" in content or "# verbs" in content
    except OSError:
        return False


def cmd_new(args: list[str]):
    """Scaffold a new game or chapter directory with index.md."""
    name = " ".join(args) if args else None

    if _in_game_dir():
        _cmd_new_chapter(name)
    else:
        _cmd_new_game(name)


def _cmd_new_game(name: str | None):
    """Scaffold a new game directory."""
    if not name:
        name = input("Game name: ").strip()
        if not name:
            print("ERROR: Game name is required")
            sys.exit(1)
        author = input("Author: ").strip()
        default_verbs = "LOOK, USE, TAKE"
        verbs_input = input(f"Starting verbs (comma-separated, default: {default_verbs}): ").strip()
        verbs = [v.strip() for v in (verbs_input or default_verbs).split(",")]
        title = name
    else:
        title = name
        author = ""
        verbs = ["LOOK", "USE", "TAKE"]

    game_dir = _resolve_game_dir(name)

    game_dir.mkdir(parents=True, exist_ok=True)

    lines = ["---"]
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
    print(f"\nCreated game: {game_dir / 'index.md'}")


def _cmd_new_chapter(name: str | None):
    """Scaffold a new chapter subdirectory within an existing game."""
    if not name:
        name = input("Chapter name: ").strip()
        if not name:
            print("ERROR: Chapter name is required")
            sys.exit(1)
    slug = _slugify(name)
    chapter_dir = Path(slug)

    if (chapter_dir / "index.md").exists():
        print(f"ERROR: {chapter_dir / 'index.md'} already exists")
        sys.exit(1)

    chapter_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Verbs",
        "",
        f"# Items",
        "",
    ]

    (chapter_dir / "index.md").write_text("\n".join(lines) + "\n")
    print(f"\nCreated chapter \"{name}\": {chapter_dir / 'index.md'}")


COMMANDS = {
    "build": cmd_build,
    "new": cmd_new,
}

USAGE = """\
Usage: adv <command> [args]

Commands:
  build [dir] [--md] [-o FILE] [--theme NAME] [--paper SIZE] [--blind]
                     Compile game to PDF (default) or markdown
  new [name]         Scaffold a new game or chapter (interactive if no name given)\
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
        # Backwards compat: bare directory arg = build
        cmd_build(args)
