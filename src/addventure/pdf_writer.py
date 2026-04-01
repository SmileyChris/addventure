import json
import subprocess
import tempfile
from pathlib import Path
from shutil import which

from .models import GameData
from .writer import GameWriter
from .compiler import get_entity_id, check_authored_collisions, check_potential_collisions


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

# Friendly aliases for common paper sizes
PAPER_ALIASES = {
    "letter": "us-letter",
    "legal": "us-legal",
    "tabloid": "us-tabloid",
}


def serialize_game_data(game: GameData, writer: GameWriter, blind: bool = False) -> dict:
    """Transform GameData into a JSON-serializable dict for Typst templates."""
    verbs = []
    for v in game.verbs.values():
        if "__" in v.name:
            continue
        # If a state variant exists (e.g. USE__RESTRAINED), show its ID
        # as the starting ID since the player begins in that state
        start_id = v.id
        for sv in game.verbs.values():
            if sv.name.startswith(v.name + "__"):
                start_id = sv.id
                break
        verbs.append({"name": v.name, "id": start_id})

    rooms = []
    for room_name, rm in game.rooms.items():
        if rm.state is not None:
            continue

        # Initial visible objects (not discovered via arrows or cues)
        discovered_names = set()
        for ix in game.interactions:
            for a in ix.arrows:
                if a.destination == "room" and ix.room == room_name:
                    discovered_names.add(a.subject)
        for cue in game.cues:
            if cue.target_room == room_name:
                for a in cue.arrows:
                    if a.destination == "room":
                        discovered_names.add(a.subject)

        objects = [
            {"name": n.name, "id": n.id}
            for n in game.nouns.values()
            if n.room == room_name and n.state is None and n.name not in discovered_names
        ]

        disc_count = sum(
            1 for ix in game.interactions if ix.room == room_name
            for a in ix.arrows if a.destination == "room"
        ) + sum(
            1 for cue in game.cues if cue.target_room == room_name
            for a in cue.arrows if a.destination == "room"
        )

        # Get room description from LOOK + @room interaction
        look_entry = writer._find_entry("LOOK", f"@{room_name}", room_name)
        description = look_entry.narrative if look_entry else ""
        # First line only for the start room sheet
        first_line = description.split("\n")[0].strip() if description else ""

        rooms.append({
            "name": room_name,
            "id": rm.id,
            "objects": objects,
            "discovery_slots": disc_count,
            "description": first_line,
        })

    potentials = sorted(
        [{"sum": ri.sum_id, "entry": ri.entry_number} for ri in game.resolved],
        key=lambda p: p["sum"],
    )

    ledger = []
    seen_entries = set()
    for ri in game.resolved:
        if ri.entry_number in seen_entries:
            continue
        seen_entries.add(ri.entry_number)
        instructions = writer._generate_instructions(ri)
        ledger.append({
            "entry": ri.entry_number,
            "narrative": ri.narrative,
            "instructions": instructions,
        })
    ledger.sort(key=lambda e: e["entry"])

    start_room = writer._start_room()
    entry_prefix = game.metadata.get("entry_prefix", "A")

    # Normalize discovery slots: all rooms get the max to avoid leaking info
    max_disc = max((r["discovery_slots"] for r in rooms), default=0)
    for room in rooms:
        room["discovery_slots"] = max_disc
        room["is_start"] = room["name"] == start_room

    return {
        "metadata": game.metadata,
        "start_room": start_room,
        "entry_prefix": entry_prefix,
        "blind": blind,
        "verbs": verbs,
        "rooms": rooms,
        "inventory_slots": max(len(game.items) + 2, 6),
        "cue_slots": len(game.cues),
        "potentials": potentials,
        "ledger": ledger,
    }


def find_typst() -> str | None:
    """Return path to typst binary, or None if not found."""
    return which("typst")


def generate_pdf(
    game: GameData,
    output_path: Path,
    theme: str = "default",
    game_dir: Path | None = None,
    paper: str | None = None,
    blind: bool = False,
    cover: bool = False,
) -> bool:
    """Generate a PDF from GameData. Returns True on success, False if typst not found."""
    typst_bin = find_typst()
    if typst_bin is None:
        return False

    theme_dir = TEMPLATES_DIR / theme
    if not theme_dir.exists():
        raise FileNotFoundError(f"Theme not found: {theme} (looked in {theme_dir})")

    writer = GameWriter(game, blind=blind)
    data = serialize_game_data(game, writer, blind=blind)

    # Resolve cover image path relative to game directory
    image_rel = game.metadata.get("image")
    if image_rel and game_dir is not None:
        image_path = (game_dir / image_rel).resolve()
        if image_path.is_file():
            data["metadata"]["image"] = str(image_path)
        else:
            print(f"WARNING: image not found: {image_path}", file=__import__('sys').stderr)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        json_path = f.name

    try:
        main_typ = theme_dir / "main.typ"
        output_path = Path(output_path)
        cmd = [
            typst_bin, "compile",
            str(main_typ),
            str(output_path),
            "--root", "/",
            "--font-path", str(theme_dir / "fonts"),
            "--input", f"data={json_path}",
        ]
        if paper:
            paper = PAPER_ALIASES.get(paper, paper)
            cmd.extend(["--input", f"paper={paper}"])
        if cover:
            logo_path = str(Path(__file__).resolve().parent.parent.parent / "addventure.jpg")
            cmd.extend(["--input", f"cover={logo_path}"])
        cmd.extend(["--input", "fillable=1"])
        subprocess.run(
            cmd,
            check=True,
            capture_output=True,
            text=True,
        )
        from .fillable import make_fillable
        make_fillable(output_path)
        return True
    except subprocess.CalledProcessError as e:
        print(f"Typst error:\n{e.stderr}", file=__import__('sys').stderr)
        raise
    finally:
        Path(json_path).unlink(missing_ok=True)
