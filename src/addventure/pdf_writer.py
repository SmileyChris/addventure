import json
import subprocess
import tempfile
from pathlib import Path
from shutil import which

from .models import GameData
from .writer import GameWriter
from .compiler import get_entity_id, check_authored_collisions, check_potential_collisions


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"


def serialize_game_data(game: GameData, writer: GameWriter) -> dict:
    """Transform GameData into a JSON-serializable dict for Typst templates."""
    verbs = [
        {"name": v.name, "id": v.id}
        for v in game.verbs.values()
        if "__" not in v.name
    ]

    rooms = []
    for room_name, rm in game.rooms.items():
        if rm.state is not None:
            continue

        # Initial visible objects (not discovered via arrows)
        discovered_names = set()
        for ix in game.interactions:
            for a in ix.arrows:
                if a.destination == "room" and ix.room == room_name:
                    discovered_names.add(a.subject)

        objects = [
            {"name": n.name, "id": n.id}
            for n in game.nouns.values()
            if n.room == room_name and n.state is None and n.name not in discovered_names
        ]

        disc_count = sum(
            1 for ix in game.interactions if ix.room == room_name
            for a in ix.arrows if a.destination == "room"
        )

        rooms.append({
            "name": room_name,
            "id": rm.id,
            "objects": objects,
            "discovery_slots": disc_count,
        })

    potentials = sorted(
        [{"sum": ri.sum_id, "entry": ri.entry_number} for ri in game.resolved],
        key=lambda p: p["sum"],
    )

    ledger = []
    for ri in game.resolved:
        instructions = writer._generate_instructions(ri)
        ledger.append({
            "entry": ri.entry_number,
            "narrative": ri.narrative,
            "instructions": instructions,
        })

    return {
        "metadata": game.metadata,
        "verbs": verbs,
        "rooms": rooms,
        "inventory_slots": 12,
        "potentials": potentials,
        "ledger": ledger,
    }
