import json
import math
import subprocess
import tempfile
from pathlib import Path
from shutil import which

from .jigsaw import checkerboard_flips, compute_grid, detect_empty_cells, interleave_pieces
from .models import GameData, ResolvedInteraction
from .writer import GameWriter


TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"

MEASURE_MARGIN_MM = 2

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
        if "__" in v.name or v.name in game.auto_verbs:
            continue
        # If a state variant exists (e.g. USE__RESTRAINED), show its ID
        # as the starting ID since the player begins in that state
        start_id = v.id
        for sv in game.verbs.values():
            if sv.name.startswith(v.name + "__"):
                start_id = sv.id
                break
        verbs.append({"name": writer.display_name(v.name), "id": start_id})

    entry_prefix = game.metadata.get("entry_prefix", "A")

    rooms = []
    for room_name, rm in game.rooms.items():
        if rm.state is not None:
            continue

        # Initial visible objects (not discovered via arrows or cues)
        objects = [
            {"name": writer.display_name(n.name), "id": n.id}
            for n in writer._initial_objects(room_name)
        ]

        disc_count = sum(
            1 for obj in game.objects.values()
            if obj.room == room_name and obj.state is None and obj.discovered
        ) + sum(
            1 for a in game.actions.values()
            if a.room == room_name and a.discovered
        )

        # Actions for this room (pre-printed only)
        room_actions = [
            {"name": writer.display_name(a.name), "entry": a.ledger_id}
            for a in game.actions.values()
            if a.room == room_name and not a.discovered
        ]

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
            "actions": room_actions,
            "entry_prefix": entry_prefix,
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
    seen_action_entries = set()
    for action in game.actions.values():
        if action.ledger_id in seen_entries or action.ledger_id in seen_action_entries:
            continue
        seen_action_entries.add(action.ledger_id)
        instructions = writer._action_instructions(action)
        ledger.append({
            "entry": action.ledger_id,
            "narrative": action.narrative,
            "instructions": instructions,
        })

    # Signal check entries (index-level)
    from .compiler import signal_id as _signal_id
    for sc in game.signal_checks:
        if sc.entry_number not in seen_entries:
            seen_entries.add(sc.entry_number)
            sc_instructions = writer._signal_check_instructions(sc.arrows, room=writer._start_room() or "")
            ledger.append({
                "entry": sc.entry_number,
                "narrative": sc.narrative,
                "instructions": sc_instructions,
            })

    # Signal check entries (interaction-level)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            if sc.entry_number not in seen_entries:
                seen_entries.add(sc.entry_number)
                sc_instructions = writer._signal_check_instructions(sc.arrows, room=ix.room)
                ledger.append({
                    "entry": sc.entry_number,
                    "narrative": sc.narrative,
                    "instructions": sc_instructions,
                })

    # Build signal check references for ledger entries
    from .md_writer import _format_signal_check_instruction
    entry_signal_refs = {}
    for ix in game.interactions:
        if ix.signal_checks:
            for ri in game.resolved:
                if ri.source_line == ix.source_line and ri.room == ix.room:
                    # Strip markdown bold markers for plain-text PDF instructions
                    ref = _format_signal_check_instruction(
                        ix.signal_checks, entry_prefix, _signal_id, also=True
                    )
                    entry_signal_refs[ri.entry_number] = ref.replace("**", "")

    ledger.sort(key=lambda e: e["entry"])

    # Add signal check refs to existing ledger entries
    for entry in ledger:
        ref = entry_signal_refs.get(entry["entry"])
        if ref:
            entry["instructions"] = list(entry["instructions"]) + [ref]

    start_room = writer._start_room()

    # Normalize discovery slots: all rooms get the max to avoid leaking info
    # In blind mode, pre-printed actions are merged into the blank slot pool
    if blind:
        for room in rooms:
            room["discovery_slots"] += len(room["actions"])
            if room["name"] != start_room:
                room["actions"] = []
    max_disc = max((r["discovery_slots"] for r in rooms), default=0)
    for room in rooms:
        room["discovery_slots"] = max_disc
        room["is_start"] = room["name"] == start_room

    sealed_texts = [
        {
            "ref": st.ref,
            "content": st.content,
            "entry_number": st.entry_number,
        }
        for st in sorted(game.sealed_texts, key=lambda s: s.ref)
    ]

    # Signal checks (index-level) for verb sheet
    index_signal_checks = []
    for sc in game.signal_checks:
        if sc.signal_names:
            sid = " and ".join(_signal_id(n) for n in sc.signal_names)
        else:
            sid = None
        index_signal_checks.append({
            "signal_id": sid,
            "entry": sc.entry_number,
            "is_otherwise": not sc.signal_names,
        })

    # Signal slot count for inventory sheet
    # Count unique signal names from checks
    check_names = set()
    for sc in game.signal_checks:
        check_names.update(sc.signal_names)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            check_names.update(sc.signal_names)
    signal_slots = max(len(check_names), len(game.signal_emissions))
    signal_has_incoming = bool(check_names - game.signal_emissions)

    return {
        "metadata": dict(game.metadata),
        "start_room": start_room,
        "entry_prefix": entry_prefix,
        "blind": blind,
        "jigsaw": False,
        "verbs": verbs,
        "rooms": rooms,
        "inventory_slots": max(len(game.inventory) + 2, 6),
        "cue_slots": len(game.cues),
        "signal_checks": index_signal_checks,
        "signal_slots": signal_slots,
        "signal_has_incoming": signal_has_incoming,
        "potentials": potentials,
        "ledger": ledger,
        "sealed_texts": sealed_texts,
    }


def find_typst() -> str | None:
    """Return path to typst binary, or None if not found."""
    return which("typst")


def _jigsaw_pipeline(
    game: GameData, writer: GameWriter, theme_dir: Path
) -> dict:
    """Two-pass pipeline: measure sealed texts, compute grid, return jigsaw data."""
    if not game.sealed_texts:
        return {}

    typst_bin = find_typst()
    measure_typ = theme_dir / "sealed-measure.typ"
    content_w_mm = 160.0

    # Pass 1: measure each sealed text AND detect empty cells
    measurements = {}
    all_grids = {}
    non_empty_cells = {}

    for st in game.sealed_texts:
        measure_data = json.dumps({
            "content_w": f"{content_w_mm}mm",
            "content": st.content,
        })
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write(measure_data)
            measure_json = f.name

        measure_pdf = tempfile.mktemp(suffix=".pdf")
        measure_png = tempfile.mktemp(suffix=".png")
        try:
            # Compile to PDF for height measurement
            subprocess.run(
                [typst_bin, "compile", str(measure_typ), measure_pdf,
                 "--root", "/",
                 "--input", f"data={measure_json}"],
                check=True, capture_output=True, text=True,
            )
            from pypdf import PdfReader
            reader = PdfReader(measure_pdf)
            page = reader.pages[0]
            pt_to_mm = 25.4 / 72
            page_h_mm = float(page.mediabox.height) * pt_to_mm
            content_h_mm = page_h_mm - 2 * MEASURE_MARGIN_MM + 1
            measurements[st.ref] = content_h_mm

            # Compute grid for this text
            grid = compute_grid(
                content_w_mm + 2 * MEASURE_MARGIN_MM,
                content_h_mm + 2 * MEASURE_MARGIN_MM,
                cols=4, target_cell_h_mm=25.0,
            )
            all_grids[st.ref] = grid

            # Compile to PNG for empty cell detection
            subprocess.run(
                [typst_bin, "compile", str(measure_typ), measure_png,
                 "--root", "/",
                 "--input", f"data={measure_json}",
                 "--ppi", "72"],
                check=True, capture_output=True, text=True,
            )
            non_empty = detect_empty_cells(
                measure_png, grid["cols"], grid["rows"],
            )
            non_empty_cells[st.ref] = non_empty
        finally:
            Path(measure_json).unlink(missing_ok=True)
            Path(measure_pdf).unlink(missing_ok=True)
            Path(measure_png).unlink(missing_ok=True)

    # Uniform cell height across all sealed texts
    cell_h = max(g["cell_h_mm"] for g in all_grids.values())
    cell_w = (content_w_mm + 2 * MEASURE_MARGIN_MM) / 4
    for ref, h in measurements.items():
        full_h = h + 2 * MEASURE_MARGIN_MM
        all_grids[ref]["rows"] = max(2, math.ceil(full_h / cell_h))
        all_grids[ref]["cell_h_mm"] = cell_h

    # Build piece list from non-empty cells only
    all_pieces = []
    for st in game.sealed_texts:
        cells = non_empty_cells.get(st.ref, [])
        for r, c in cells:
            all_pieces.append({
                "ref": st.ref,
                "row": r,
                "col": c,
            })

    # Interleave and assign checkerboard flips
    interleaved = interleave_pieces(all_pieces, 4)
    cut_cols = 4
    flips = checkerboard_flips(
        math.ceil(len(interleaved) / cut_cols), cut_cols
    )
    for idx, piece in enumerate(interleaved):
        fr = idx // cut_cols
        fc = idx % cut_cols
        piece["flip"] = flips[fr][fc] if fr < len(flips) else False

    # Build per-sealed-text data for the template
    sealed_data = []
    for st in game.sealed_texts:
        sealed_data.append({
            "ref": st.ref,
            "content": st.content,
            "rows": all_grids[st.ref]["rows"],
        })

    return {
        "jigsaw_data": {
            "cols": 4,
            "cell_w": f"{cell_w:.2f}mm",
            "cell_h": f"{cell_h:.2f}mm",
            "pad": f"{MEASURE_MARGIN_MM}mm",
            "cut_cols": cut_cols,
            "pieces": interleaved,
        },
        "sealed_texts_override": sealed_data,
    }


def _run_typst(
    typst_bin: str,
    main_typ: Path,
    output_path: Path,
    theme_dir: Path,
    json_path: str,
    paper: str | None = None,
    cover: bool = False,
    extra_inputs: list[str] | None = None,
) -> None:
    """Compile a Typst template to PDF."""
    cmd = [
        typst_bin, "compile",
        str(main_typ),
        str(output_path),
        "--root", "/",
        "--font-path", str(theme_dir / "fonts"),
        "--input", f"data={json_path}",
    ]
    if paper:
        cmd.extend(["--input", f"paper={paper}"])
    if cover:
        logo_path = str(Path(__file__).resolve().parent.parent.parent / "addventure.jpg")
        cmd.extend(["--input", f"cover={logo_path}"])
    cmd.extend(["--input", "fillable=1"])
    if extra_inputs:
        for inp in extra_inputs:
            cmd.extend(["--input", inp])
    subprocess.run(cmd, check=True, capture_output=True, text=True)


def generate_pdf(
    game: GameData,
    output_path: Path,
    theme: str = "default",
    game_dir: Path | None = None,
    paper: str | None = None,
    blind: bool = False,
    cover: bool = False,
    fragment: str = "included",
) -> tuple[bool, list[str]]:
    """Generate a PDF from GameData. Returns (success, warnings).

    fragment: "included" (default), "separate" (emit <name>-fragments.pdf alongside),
              or "jigsaw" (cut pages).
    """
    typst_bin = find_typst()
    if typst_bin is None:
        return False, []

    theme_dir = TEMPLATES_DIR / theme
    if not theme_dir.exists():
        raise FileNotFoundError(f"Theme not found: {theme} (looked in {theme_dir})")

    jigsaw = fragment == "jigsaw"
    writer = GameWriter(game, blind=blind, jigsaw=jigsaw)
    data = serialize_game_data(game, writer, blind=blind)

    if jigsaw and game.sealed_texts:
        jigsaw_result = _jigsaw_pipeline(game, writer, theme_dir)
        data["jigsaw"] = True
        if "jigsaw_data" in jigsaw_result:
            data["jigsaw_data"] = jigsaw_result["jigsaw_data"]
        if "sealed_texts_override" in jigsaw_result:
            data["sealed_texts"] = jigsaw_result["sealed_texts_override"]

    if fragment == "separate" and game.sealed_texts:
        # For separate mode, strip fragments from the main PDF data
        data["sealed_texts"] = []

    # Resolve cover image path relative to game directory
    image_rel = game.metadata.get("image")
    if image_rel and game_dir is not None:
        image_path = (game_dir / image_rel).resolve()
        if image_path.is_file():
            data["metadata"]["image"] = str(image_path)
        else:
            print(f"⚠ Image not found: {image_path}", file=__import__('sys').stderr)

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".json", delete=False
    ) as f:
        json.dump(data, f)
        json_path = f.name

    try:
        import sys as _sys
        main_typ = theme_dir / "main.typ"
        output_path = Path(output_path)
        normalized_paper = PAPER_ALIASES.get(paper, paper) if paper else None
        _run_typst(typst_bin, main_typ, output_path, theme_dir, json_path,
                   paper=normalized_paper, cover=cover)
        from .fillable import make_fillable
        make_fillable(output_path)

        if fragment == "separate" and game.sealed_texts:
            # Emit a separate PDF containing only the fragments section
            sealed_path = output_path.with_stem(output_path.stem + "-fragments")
            # Restore sealed texts in data for the second render
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            ) as sf:
                data["sealed_texts"] = [
                    {"ref": st.ref, "content": st.content, "entry_number": st.entry_number}
                    for st in sorted(game.sealed_texts, key=lambda s: s.ref)
                ]
                json.dump(data, sf)
                sealed_json_path = sf.name
            try:
                _run_typst(typst_bin, main_typ, sealed_path, theme_dir, sealed_json_path,
                           paper=normalized_paper, cover=False,
                           extra_inputs=["sealed_only=1"])
                make_fillable(sealed_path)
                print(f"Fragments PDF written to {sealed_path}", file=_sys.stderr)
            finally:
                Path(sealed_json_path).unlink(missing_ok=True)

        return True, writer.warnings
    except subprocess.CalledProcessError as e:
        print(f"Typst error:\n{e.stderr}", file=__import__('sys').stderr)
        raise
    finally:
        Path(json_path).unlink(missing_ok=True)
