"""
Addventure CLI — `addventure build [dir]` and `addventure new [name]`.
"""

import re
import sys
from pathlib import Path

from . import compile_game, print_build_summary, generate_pdf, find_typst, generate_markdown
from .models import GameData
from .parser import ParseError, _parse_frontmatter


def _warn_stale_blind_room_refs(game: GameData) -> None:
    """Warn about movement arrows that target base rooms with state variants.

    In blind mode, movement instructions reference rooms by numeric ID.
    If a room has state transforms (e.g. Tower -> Tower__COLLAPSED), the
    transformed room gets a different ID. A later `player -> "Tower"` arrow
    would reference the base room's ID, which may be stale.
    """
    # Base rooms that have state variants
    stateful_bases: set[str] = {
        rm.base for rm in game.rooms.values() if rm.state is not None
    }
    if not stateful_bases:
        return

    # Collect room names targeted by player-movement arrows.
    # Skip targets ending in __ — the author is explicitly saying
    # "I mean the base state, I know what I'm doing."
    def _targeted(stateful: set[str]) -> set[str]:
        targeted: set[str] = set()
        for ri in game.resolved:
            for a in ri.arrows:
                if a.subject == "player" and a.destination.startswith('"'):
                    name = a.destination[1:-1]
                    if name.endswith("__"):
                        continue  # explicit base-state reference
                    if name in stateful:
                        targeted.add(name)
        for cue in game.cues:
            for a in cue.arrows:
                if a.subject == "player" and a.destination.startswith('"'):
                    name = a.destination[1:-1]
                    if name.endswith("__"):
                        continue  # explicit base-state reference
                    if name in stateful:
                        targeted.add(name)
        return targeted

    stale_targets = _targeted(stateful_bases)
    if stale_targets:
        names = ", ".join(sorted(stale_targets))
        print(
            f"⚠ Stale blind-mode room refs ({names}): movement arrows "
            f"target these rooms by base name, but each has state variants "
            f"with different room-sheet IDs",
            file=sys.stderr,
        )


def load_game(game_dir: Path) -> tuple[str, list[str]]:
    """Load index.md and all room .md files from a game directory."""
    if not game_dir.is_dir():
        print(f"ERROR: Directory not found: {game_dir}")
        sys.exit(1)
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
    parser = argparse.ArgumentParser(prog="addventure build", description="Compile and output a game")
    parser.add_argument("game_dir", nargs="?", default=None,
                        help="Path to game directory (default: current directory if index.md exists)")
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
    parser.add_argument("--hidden-ledger", action="store_true",
                        help="Obfuscate story ledger entries behind reveal-to-see checkboxes (fillable PDF only)")
    parser.add_argument("--no-cover", action="store_true",
                        help="Omit the How to Play cover page")
    parser.add_argument("--fragment", choices=["included", "separate", "jigsaw"],
                        default="included",
                        help="Fragment output mode: included (default), separate PDF, or jigsaw cut pages")
    parser.add_argument("--all", action="store_true",
                        help="Build all chapters into a single combined output")
    parsed = parser.parse_args(args)

    if parsed.game_dir:
        game_dir = Path(parsed.game_dir)
        if not game_dir.is_dir() and not parsed.game_dir.startswith(("games/", "games\\", "/", "~")):
            fallback = Path("games") / parsed.game_dir
            if fallback.is_dir():
                game_dir = fallback
    elif _in_game_dir():
        game_dir = Path(".")
    elif Path("games/example").is_dir():
        game_dir = Path("games/example")
    else:
        print("ERROR: No game directory specified and not in a game directory")
        print("Usage: addventure build [dir]")
        sys.exit(1)

    if parsed.all:
        _cmd_build_all(game_dir, parsed)
    else:
        _build_single(game_dir, parsed)


def _detect_parent_title(game_dir: Path) -> str | None:
    """If game_dir is a chapter subdirectory, return the parent game's title."""
    parent = game_dir.resolve().parent
    parent_index = parent / "index.md"
    if not parent_index.is_file():
        return None
    try:
        content = parent_index.read_text()
        if "# Verbs" not in content and "# verbs" not in content:
            return None
        # Parse frontmatter for title
        lines = content.splitlines()
        if lines and lines[0].strip() == "---":
            meta, _ = _parse_frontmatter(lines)
            if meta.get("title"):
                return meta["title"]
        return parent.name
    except (OSError, ParseError):
        return None


def _build_single(game_dir: Path, parsed) -> None:
    """Build a single game directory."""
    global_source, room_sources = load_game(game_dir)
    game = compile_game(global_source, room_sources)

    # Detect parent game for chapter nesting
    parent_title = _detect_parent_title(game_dir)
    if parent_title:
        game.metadata["parent_title"] = parent_title

    for warning in game.warnings:
        print(f"⚠ {warning}", file=sys.stderr)

    # Reachability check
    from .validator import validate_reachability
    for warning in validate_reachability(game):
        print(f"⚠ {warning}", file=sys.stderr)

    # Blind mode: warn if movement arrows target base rooms that have state
    # variants — the numeric room ID in the blind-mode instruction may be stale
    # if the room has already transformed to a different state.
    if parsed.blind:
        _warn_stale_blind_room_refs(game)

    writer_warnings = []
    if parsed.markdown:
        md, writer_warnings = generate_markdown(game, blind=parsed.blind, fragment=parsed.fragment)
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
            print("  Or use: addventure build --md", file=sys.stderr)
            sys.exit(1)

        if parsed.output:
            output_path = Path(parsed.output)
        else:
            name = game.metadata.get("title") or game_dir.resolve().name
            parent = game.metadata.get("parent_title")
            if parent:
                output_path = Path(f"{_slugify(parent)}_{_slugify(name)}.pdf")
            else:
                output_path = Path(f"{_slugify(name)}.pdf")
        success, writer_warnings = generate_pdf(game, output_path, theme=parsed.theme, game_dir=game_dir.resolve(), paper=parsed.paper, blind=parsed.blind, cover=not parsed.no_cover, fragment=parsed.fragment, hidden_ledger=parsed.hidden_ledger)
        if success:
            print(f"PDF written to {output_path}", file=sys.stderr)

    for warning in writer_warnings:
        print(f"⚠ {warning}", file=sys.stderr)

    print_build_summary(game)


def _cmd_build_all(game_dir: Path, parsed) -> None:
    """Build the parent game and all chapter subdirectories into one output."""
    import tempfile

    chapters = _find_chapters(game_dir)
    all_dirs = [game_dir] + chapters

    # Check for prefix conflicts
    prefix_map: dict[str, list[str]] = {}
    for d in all_dirs:
        prefix = _read_ledger_prefix(d / "index.md") or "A"
        label = d.name if d != game_dir else str(game_dir)
        prefix_map.setdefault(prefix, []).append(label)
    for prefix, dirs in prefix_map.items():
        if len(dirs) > 1:
            names = ", ".join(dirs)
            print(f"⚠ Prefix conflict: {names} share ledger_prefix \"{prefix}\"",
                  file=sys.stderr)

    if not chapters:
        print("No chapter subdirectories found, building single game",
              file=sys.stderr)
        _build_single(game_dir, parsed)
        return

    # Compile all chapters first so we can do cross-chapter validation
    compiled_chapters: list[tuple[str, object]] = []
    parent_title = None
    for d in all_dirs:
        global_source, room_sources = load_game(d)
        game = compile_game(global_source, room_sources)
        for warning in game.warnings:
            print(f"⚠ {warning}", file=sys.stderr)
        game.metadata["combined_build"] = "true"
        if d == game_dir:
            parent_title = game.metadata.get("title", str(game_dir))
        elif parent_title:
            game.metadata["parent_title"] = parent_title
        label = game.metadata.get("title", d.name)
        compiled_chapters.append((label, game))

    # Cross-chapter signal validation
    all_checked = {}   # signal_name -> chapter_label (from signal checks)
    all_emitted = {}   # signal_name -> chapter_label

    for label, game_data in compiled_chapters:
        # Collect signal names from signal checks (index-level and interaction-level)
        for sc in game_data.signal_checks:
            for sn in sc.signal_names:
                all_checked.setdefault(sn, label)
        for ix in game_data.interactions:
            for sc in ix.signal_checks:
                for sn in sc.signal_names:
                    all_checked.setdefault(sn, label)
        for name in game_data.signal_emissions:
            all_emitted[name] = label

    for name in all_emitted:
        if name not in all_checked:
            print(
                f"⚠ Signal {name} is emitted but not checked in any chapter",
                file=sys.stderr,
            )
    for name in all_checked:
        if name not in all_emitted:
            print(
                f"⚠ Signal {name} is checked but not emitted by any chapter",
                file=sys.stderr,
            )

    if parsed.markdown:
        from .md_writer import (
            _title_section, _room_section, _ledger_section, _sealed_section,
            _shared_actions_inventory_section,
        )
        from .writer import GameWriter

        all_games = [game for _, game in compiled_chapters]
        sections = []

        # Shared Actions & Inventory (verbs + inventory + signals)
        first_game = compiled_chapters[0][1]
        first_writer = GameWriter(first_game, blind=parsed.blind)
        sections.append(_shared_actions_inventory_section(first_writer, all_games))

        # Per-chapter: title page (intro + cues + potentials), rooms, ledger
        for label, game in compiled_chapters:
            writer = GameWriter(game, blind=parsed.blind, jigsaw=(parsed.fragment == "jigsaw"))
            entry_prefix = game.metadata.get("ledger_prefix", "A")
            for warning in writer.warnings:
                print(f"⚠ {warning}", file=sys.stderr)

            sections.append(_title_section(game, writer, entry_prefix))

            start_room = writer._start_room()
            room_names = [name for name, rm in game.rooms.items() if rm.state is None]
            if start_room and start_room in room_names:
                sections.append(_room_section(game, writer, start_room, is_start=True, blind=parsed.blind))
            for name in room_names:
                if name != start_room:
                    sections.append(_room_section(game, writer, name, is_start=False, blind=parsed.blind))

            sections.append(_ledger_section(game, writer, entry_prefix))

            fragments = _sealed_section(game, writer)
            if fragments:
                sections.append(fragments)

            print(f"Built chapter: {label}", file=sys.stderr)

        combined = "\n\n---\n\n".join(sections) + "\n"
        if parsed.output:
            Path(parsed.output).write_text(combined)
            print(f"Markdown written to {parsed.output}", file=sys.stderr)
        else:
            print(combined, end="")
    else:
        if find_typst() is None:
            print("ERROR: typst not found on PATH (needed for PDF output)",
                  file=sys.stderr)
            print("  Install typst: https://github.com/typst/typst",
                  file=sys.stderr)
            print("  Or use: addventure build --all --md", file=sys.stderr)
            sys.exit(1)

        from .pdf_writer import generate_combined_pdf

        # Build combined PDF with shared verbs/inventory and per-chapter sections
        chapter_tuples = [
            (label, game, all_dirs[i].resolve())
            for i, (label, game) in enumerate(compiled_chapters)
        ]

        if parsed.output:
            output_path = Path(parsed.output)
        else:
            _, parent_game = compiled_chapters[0]
            name = parent_game.metadata.get("title") or game_dir.resolve().name
            output_path = Path(f"{_slugify(name)}.pdf")

        success, writer_warnings = generate_combined_pdf(
            chapter_tuples, output_path,
            theme=parsed.theme, paper=parsed.paper,
            blind=parsed.blind, cover=not parsed.no_cover,
            fragment=parsed.fragment, hidden_ledger=parsed.hidden_ledger,
        )
        for warning in writer_warnings:
            print(f"⚠ {warning}", file=sys.stderr)
        if success:
            print(f"Combined PDF written to {output_path}", file=sys.stderr)
        for label, _ in compiled_chapters:
            print(f"Built chapter: {label}", file=sys.stderr)


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
    lines.append("# Inventory")
    lines.append("")

    (game_dir / "index.md").write_text("\n".join(lines) + "\n")
    print(f"\nCreated game: {game_dir / 'index.md'}")


def _read_ledger_prefix(index_path: Path) -> str | None:
    """Read ledger_prefix from a chapter's index.md frontmatter."""
    try:
        content = index_path.read_text()
    except OSError:
        return None
    lines = content.splitlines()
    if not lines or lines[0].strip() != "---":
        return None
    try:
        meta, _ = _parse_frontmatter(lines)
    except ParseError:
        return None
    return meta.get("ledger_prefix")


def _find_chapters(game_dir: Path) -> list[Path]:
    """Find chapter subdirectories (those with index.md containing # Verbs)."""
    chapters = []
    for child in sorted(game_dir.iterdir()):
        if child.is_dir() and (child / "index.md").is_file():
            try:
                content = (child / "index.md").read_text()
                if "# Verbs" in content or "# verbs" in content:
                    chapters.append(child)
            except OSError:
                pass
    return chapters


def _next_chapter_prefix(game_dir: Path) -> str:
    """Determine the next available chapter prefix letter."""
    used = {"A"}  # Parent game is always A
    for chapter_dir in _find_chapters(game_dir):
        prefix = _read_ledger_prefix(chapter_dir / "index.md")
        if prefix:
            used.add(prefix.upper())
    for letter in "BCDEFGHIJKLMNOPQRSTUVWXYZ":
        if letter not in used:
            return letter
    raise RuntimeError("No available chapter prefix letters (A-Z exhausted)")


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

    prefix = _next_chapter_prefix(Path("."))

    chapter_dir.mkdir(parents=True, exist_ok=True)

    lines = [
        "---",
        f"ledger_prefix: {prefix}",
        "---",
        "",
        "# Verbs",
        "",
        "# Inventory",
        "",
    ]

    (chapter_dir / "index.md").write_text("\n".join(lines) + "\n")
    print(f"\nCreated chapter \"{name}\" (prefix {prefix}): {chapter_dir / 'index.md'}")


def _merge_pdfs(pdf_paths: list[Path], output_path: Path) -> None:
    """Merge multiple PDFs into one using pypdf."""
    from pypdf import PdfWriter
    writer = PdfWriter()
    for p in pdf_paths:
        writer.append(str(p))
    writer.write(str(output_path))
    writer.close()


COMMANDS = {
    "build": cmd_build,
    "new": cmd_new,
}

USAGE = """\
Usage: addventure <command> [args]

Commands:
  build [dir] [--md] [-o FILE] [--all] [--theme NAME] [--paper SIZE] [--blind] [--no-cover] [--fragment MODE]
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
