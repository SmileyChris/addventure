"""Markdown writer — generates a player-facing markdown document from GameData."""

from textwrap import indent

from .models import GameData, ResolvedInteraction
from .writer import GameWriter, _display_name


def _render_placeholder_rows(count: int, width: int = 6) -> list[str]:
    """Render placeholder table rows padded to a fixed column width."""
    total = max(count, width)
    rows = []
    for offset in range(0, total, width):
        cells = ["`____`"] * min(width, total - offset)
        cells.extend([""] * (width - len(cells)))
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def generate_markdown(game: GameData, blind: bool = False) -> tuple[str, list[str]]:
    """Generate a complete markdown document from compiled GameData.

    Returns (markdown_text, warnings).
    """
    writer = GameWriter(game, blind=blind)
    entry_prefix = game.metadata.get("entry_prefix", "A")
    sections = []

    sections.append(_verb_section(game, writer, entry_prefix))

    start_room = writer._start_room()
    room_names = [
        name for name, rm in game.rooms.items() if rm.state is None
    ]
    if start_room and start_room in room_names:
        sections.append(_room_section(game, writer, start_room, is_start=True, blind=blind))
    sections.append(_inventory_section(game, writer, entry_prefix))
    for name in room_names:
        if name != start_room:
            sections.append(_room_section(game, writer, name, is_start=False, blind=blind))

    sections.append(_ledger_section(game, writer, entry_prefix))

    return "\n\n---\n\n".join(sections) + "\n", writer.warnings


def _verb_section(game: GameData, writer: GameWriter, entry_prefix: str) -> str:
    title = game.metadata.get("title", "Addventure")
    lines = [f"# {title}"]

    description = game.metadata.get("description")
    if description:
        lines.append(f"\n{description}")

    lines.append(
        "\n*To take an action, calculate verb number + object number(s)."
        " Look up the resulting sum in the Potentials List."
        " If listed, read the matching Ledger entry. If not listed, nothing happens.*"
    )

    lines.append("\n## Verbs\n")
    lines.append("| Verb | ID |")
    lines.append("|------|---:|")
    for v in game.verbs.values():
        if "__" not in v.name and v.name not in game.auto_verbs:
            lines.append(f"| {v.name} | {v.id} |")

    lines.append("\n*If instructed, record new verbs here.*\n")
    for _ in range(3):
        lines.append("- ______________ `[____]`")

    return "\n".join(lines)


def _room_section(
    game: GameData, writer: GameWriter, room_name: str,
    is_start: bool, blind: bool,
) -> str:
    rm = game.rooms[room_name]
    max_disc = writer._max_discovery_slots()

    if blind and not is_start:
        lines = [f"## Room ____"]
    else:
        label = f" (Start)" if is_start else ""
        lines = [f"## {room_name}{label}"]

    lines.append(f"\n**Room ID:** `{rm.id}`")

    # Description
    if is_start:
        look_entry = writer._find_entry("LOOK", f"@{room_name}", room_name)
        if look_entry and look_entry.narrative:
            lines.append(f"\n{look_entry.narrative}")

    # Objects
    initial = writer._initial_objects(room_name)

    preprinted_actions = writer._preprinted_actions(room_name)

    if blind:
        total_slots = len(initial) + len(preprinted_actions) + max_disc
        if is_start:
            lines.append("\n### Objects\n")
            lines.append("| Object | ID |")
            lines.append("|--------|---:|")
            for n in initial:
                lines.append(f"| {n.name} | `____` |")
            for a in preprinted_actions:
                lines.append(f"| {_display_name(a.name)} | `____` |")
        elif total_slots > 0:
            lines.append("\n### Objects\n")
            for _ in range(total_slots):
                lines.append("- ______________ `[____]`")
    else:
        if initial:
            lines.append("\n### Objects\n")
            lines.append("| Object | ID |")
            lines.append("|--------|---:|")
            for n in initial:
                lines.append(f"| {n.name} | {n.id} |")

        if max_disc > 0:
            lines.append(
                f"\n### Discoveries\n"
                f"*If objects are discovered in this room, record them here.*\n"
            )
            for _ in range(max_disc):
                lines.append("- ______________ `[____]`")

        # Actions (pre-printed) — only in non-blind mode
        if preprinted_actions:
            lines.append("\n### Actions\n")
            lines.append("| Action | Entry |")
            lines.append("|--------|------:|")
            entry_prefix_local = game.metadata.get("entry_prefix", "A")
            for a in preprinted_actions:
                lines.append(f"| {_display_name(a.name)} | {entry_prefix_local}-{a.ledger_id} |")

    return "\n".join(lines)


def _inventory_section(
    game: GameData, writer: GameWriter, entry_prefix: str,
) -> str:
    lines = ["## Inventory & Potentials"]

    # Inventory
    slot_count = max(len(game.items) + 2, 6)
    lines.append(
        "\n### Inventory\n"
        "\n*Record items you are carrying. Write the item name and its ID.*\n"
    )
    for _ in range(slot_count):
        lines.append("- ______________ `[____]`")

    # Cue Checks
    if game.cues:
        lines.append(
            "\n### Cue Checks\n"
            "\n*On room entry, add each cue + Room ID and check the Potentials List.*\n"
        )
        rows = _render_placeholder_rows(len(game.cues))
        lines.append(rows[0])
        lines.append("| " + " | ".join("---:" for _ in range(6)) + " |")
        lines.extend(rows[1:])

    # Master Potentials List
    lines.append(
        "\n### Master Potentials List\n"
        "\n*Calculate verb number + object number(s) and look up the sum below."
        " If listed, go to that Ledger entry.*\n"
    )
    potentials = sorted(game.resolved, key=lambda r: r.sum_id)
    cols = min(4, len(potentials)) or 1
    rows = -(-len(potentials) // cols)  # ceil division

    header = " | ".join(f"Sum | Entry" for _ in range(cols))
    sep = " | ".join(f"---:|------" for _ in range(cols))
    lines.append(f"| {header} |")
    lines.append(f"| {sep} |")
    for row_idx in range(rows):
        cells = []
        for col_idx in range(cols):
            idx = col_idx * rows + row_idx
            if idx < len(potentials):
                ri = potentials[idx]
                cells.append(f"{ri.sum_id} | {entry_prefix}-{ri.entry_number}")
            else:
                cells.append(" | ")
        lines.append(f"| {' | '.join(cells)} |")

    return "\n".join(lines)


def _ledger_section(
    game: GameData, writer: GameWriter, entry_prefix: str,
) -> str:
    lines = [
        "## Story Ledger",
        "\n*Only read an entry when directed to by the Potentials List or a room sheet."
        " Read the narrative aloud, then follow any instructions.*",
    ]

    # Collect all entries: resolved interactions + actions
    all_entries = []

    seen_entries = set()
    for ri in game.resolved:
        if ri.entry_number in seen_entries:
            continue
        seen_entries.add(ri.entry_number)
        instructions = writer._generate_instructions(ri)
        all_entries.append((ri.entry_number, ri.narrative, instructions))

    seen_action_entries = set()
    for action in game.actions.values():
        if action.ledger_id in seen_entries or action.ledger_id in seen_action_entries:
            continue
        seen_action_entries.add(action.ledger_id)
        instructions = writer._action_instructions(action)
        all_entries.append((action.ledger_id, action.narrative, instructions))

    all_entries.sort(key=lambda e: e[0])

    for entry_num, narrative, instructions in all_entries:
        lines.append(f"\n{entry_prefix}-{entry_num}")
        body = narrative
        if instructions:
            body += "\n\n" + "\n".join(f"- *{inst}*" for inst in instructions)
        lines.append(indent(body, ": ", lambda line: True))

    return "\n".join(lines)
