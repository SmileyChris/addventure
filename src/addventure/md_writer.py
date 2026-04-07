"""Markdown writer — generates a player-facing markdown document from GameData."""

from textwrap import indent

from .models import GameData, ResolvedInteraction
from .writer import GameWriter


def _format_signal_check_instruction(checks, entry_prefix, _signal_id, also=False):
    """Format signal checks as an if/otherwise instruction string.

    Returns e.g.: "Check your signals: if you have LLLT and HWZT, read A-2.
    Otherwise, if you have LLLT, read A-5. Otherwise, read A-3."
    """
    read_word = "also read" if also else "read"
    parts = []
    for i, sc in enumerate(checks):
        if sc.signal_names:
            sids = " and ".join(f"**{_signal_id(n)}**" for n in sc.signal_names)
            if i == 0:
                parts.append(f"if you have {sids}, {read_word} {entry_prefix}-{sc.entry_number}")
            else:
                parts.append(f"Otherwise, if you have {sids}, {read_word} {entry_prefix}-{sc.entry_number}")
        else:
            parts.append(f"Otherwise, {read_word} {entry_prefix}-{sc.entry_number}")
    return f"Check your signals: {'. '.join(parts)}."


def _render_placeholder_rows(count: int, width: int = 6) -> list[str]:
    """Render placeholder table rows padded to a fixed column width."""
    total = max(count, width)
    rows = []
    for offset in range(0, total, width):
        cells = ["`____`"] * min(width, total - offset)
        cells.extend([""] * (width - len(cells)))
        rows.append("| " + " | ".join(cells) + " |")
    return rows


def generate_markdown(game: GameData, blind: bool = False, fragment: str = "included") -> tuple[str, list[str]]:
    """Generate a complete markdown document from compiled GameData.

    Returns (markdown_text, warnings).
    fragment: "included" (default), "separate", or "jigsaw"
    """
    writer = GameWriter(game, blind=blind, jigsaw=(fragment == "jigsaw"))
    entry_prefix = game.metadata.get("ledger_prefix", "A")
    sections = []

    # 1. Title page: intro, signal checks, cues, potentials
    sections.append(_title_section(game, writer, entry_prefix))

    # 2. Actions & Inventory: verbs, inventory slots, signals
    sections.append(_actions_inventory_section(game, writer))

    # 3. Rooms
    start_room = writer._start_room()
    room_names = [
        name for name, rm in game.rooms.items() if rm.state is None
    ]
    if start_room and start_room in room_names:
        sections.append(_room_section(game, writer, start_room, is_start=True, blind=blind))
    for name in room_names:
        if name != start_room:
            sections.append(_room_section(game, writer, name, is_start=False, blind=blind))

    # 4. Ledger
    sections.append(_ledger_section(game, writer, entry_prefix))

    # 5. Fragments
    fragments = _sealed_section(game, writer)
    if fragments:
        sections.append(fragments)

    return "\n\n---\n\n".join(sections) + "\n", writer.warnings


def _game_title(game: GameData) -> str:
    title = game.metadata.get("title", "Addventure")
    parent_title = game.metadata.get("parent_title")
    if parent_title:
        return f"{parent_title} — {title}"
    return title


def _title_section(game: GameData, writer: GameWriter, entry_prefix: str) -> str:
    """Title page: intro, signal checks, cues, potentials."""
    lines = [f"# {_game_title(game)}"]

    description = game.metadata.get("description")
    if description:
        lines.append(f"\n{description}")

    if game.signal_checks:
        from .compiler import signal_id as _signal_id
        lines.append(f"\n*{_format_signal_check_instruction(game.signal_checks, entry_prefix, _signal_id)}*")

    lines.extend(_cue_section(game))
    lines.extend(_potentials_table(game, entry_prefix))

    return "\n".join(lines)


def _actions_inventory_section(game: GameData, writer: GameWriter) -> str:
    """Actions & Inventory: how-to-play, verbs, inventory slots, signals."""
    lines = ["## Actions & Inventory"]

    lines.append(
        "\n*To take an action, calculate verb number + object number(s)."
        " Look up the resulting sum in the Potentials List."
        " If listed, read the matching Ledger entry. If not listed, nothing happens.*"
    )

    lines.append("\n### Verbs\n")
    lines.append("| Verb | ID |")
    lines.append("|------|---:|")
    for v in game.verbs.values():
        if "__" not in v.name and v.name not in game.auto_verbs:
            lines.append(f"| {writer.display_name(v.name)} | {v.id} |")

    lines.append("\n*If instructed, record new verbs here.*\n")
    for _ in range(3):
        lines.append("- ______________ `[____]`")

    lines.extend(_inventory_slots(game, writer))
    lines.extend(_signal_slots(game))

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
            for a in preprinted_actions:
                lines.append(f"| {writer.display_name(a.name)} | `____` |")
            for n in initial:
                lines.append(f"| {writer.display_name(n.name)} | `____` |")
        elif total_slots > 0:
            lines.append("\n### Objects\n")
            for _ in range(total_slots):
                lines.append("- ______________ `[____]`")
    else:
        # Actions (pre-printed) — only in non-blind mode
        if preprinted_actions:
            lines.append("\n### Actions\n")
            lines.append("| Action | Entry |")
            lines.append("|--------|------:|")
            entry_prefix_local = game.metadata.get("ledger_prefix", "A")
            for a in preprinted_actions:
                lines.append(f"| {writer.display_name(a.name)} | {entry_prefix_local}-{a.ledger_id} |")

        if initial:
            lines.append("\n### Objects\n")
            lines.append("| Object | ID |")
            lines.append("|--------|---:|")
            for n in initial:
                lines.append(f"| {writer.display_name(n.name)} | {n.id} |")

        if max_disc > 0:
            lines.append(
                f"\n### Discoveries\n"
                f"*If objects are discovered in this room, record them here.*\n"
            )
            for _ in range(max_disc):
                lines.append("- ______________ `[____]`")

    return "\n".join(lines)



def _shared_actions_inventory_section(writer: 'GameWriter', games: list[GameData]) -> str:
    """Shared Actions & Inventory for --all builds: verbs, inventory, signals."""
    lines = ["## Actions & Inventory"]

    lines.append(
        "\n*To take an action, calculate verb number + object number(s)."
        " Look up the resulting sum in the Potentials List."
        " If listed, read the matching Ledger entry. If not listed, nothing happens.*"
    )

    # Verbs from first chapter
    game = games[0]
    lines.append("\n### Verbs\n")
    lines.append("| Verb | ID |")
    lines.append("|------|---:|")
    for v in game.verbs.values():
        if "__" not in v.name and v.name not in game.auto_verbs:
            lines.append(f"| {writer.display_name(v.name)} | {v.id} |")
    lines.append("\n*If instructed, record new verbs here.*\n")
    for _ in range(3):
        lines.append("- ______________ `[____]`")

    # Inventory slots: max across all chapters
    max_inv = max(max(len(g.inventory) + 2, 6) for g in games)
    lines.append(
        "\n### Inventory\n"
        "\n*Record items you are carrying. Write the item name and its ID.*\n"
    )
    for _ in range(max_inv):
        lines.append("- ______________ `[____]`")

    # Signal slots: collect across all chapters
    all_check_names = set()
    all_emissions = set()
    for g in games:
        for sc in g.signal_checks:
            all_check_names.update(sc.signal_names)
        for ix in g.interactions:
            for sc in ix.signal_checks:
                all_check_names.update(sc.signal_names)
        all_emissions.update(g.signal_emissions)
    signal_count = max(len(all_check_names), len(all_emissions))
    if signal_count > 0:
        lines.append(
            "\n### Signals\n"
            "\n*Write signal codes here when instructed.*\n"
        )
        rows = _render_placeholder_rows(signal_count)
        lines.extend(rows)

    return "\n".join(lines)


def _inventory_slots(game: GameData, writer: GameWriter) -> list[str]:
    lines = []
    slot_count = max(len(game.inventory) + 2, 6)
    lines.append(
        "\n### Inventory\n"
        "\n*Record items you are carrying. Write the item name and its ID.*\n"
    )
    for _ in range(slot_count):
        lines.append("- ______________ `[____]`")
    return lines


def _cue_section(game: GameData) -> list[str]:
    lines = []
    if game.cues:
        lines.append(
            "\n### Cue Checks\n"
            "\n*On room entry, add each cue + Room ID and check the Potentials List.*\n"
        )
        rows = _render_placeholder_rows(len(game.cues))
        lines.append(rows[0])
        lines.append("| " + " | ".join("---:" for _ in range(6)) + " |")
        lines.extend(rows[1:])
    return lines


def _signal_slots(game: GameData) -> list[str]:
    lines = []
    check_names = set()
    for sc in game.signal_checks:
        check_names.update(sc.signal_names)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            check_names.update(sc.signal_names)
    signal_count = max(len(check_names), len(game.signal_emissions))
    if signal_count > 0:
        incoming = check_names - game.signal_emissions
        if incoming:
            hint = "Copy any signals from the previous chapter, then write new ones when instructed."
        else:
            hint = "Write signal codes here when instructed."
        lines.append(
            "\n### Signals\n"
            f"\n*{hint}*\n"
        )
        rows = _render_placeholder_rows(signal_count)
        lines.extend(rows)
    return lines


def _potentials_table(game: GameData, entry_prefix: str) -> list[str]:
    lines = []
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
    return lines


def _sealed_section(game: GameData, writer: GameWriter = None) -> str:
    """Render sealed texts as a section at the end."""
    if not game.sealed_texts:
        return ""
    lines = [
        "## Fragments",
        "\n*Do not read ahead — turn to a fragment only when directed by a ledger entry.*",
    ]
    for st in sorted(game.sealed_texts, key=lambda s: s.ref):
        lines.append(f"\n### Fragment {st.ref}")
        lines.append(f"> ⚠ Do not read until directed.\n")
        lines.append(st.content)
        if st.arrows and writer:
            instructions = writer._signal_check_instructions(st.arrows, room=st.room)
            if instructions:
                lines.append("")
                lines.extend(f"- *{inst}*" for inst in instructions)
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

    # Index-level signal check entries
    for sc in game.signal_checks:
        if sc.entry_number not in seen_entries and sc.entry_number not in seen_action_entries:
            seen_entries.add(sc.entry_number)
            sc_instructions = writer._signal_check_instructions(sc.arrows, room=writer._start_room() or "")
            all_entries.append((sc.entry_number, sc.narrative, sc_instructions))

    # Interaction-level signal check entries
    for ix in game.interactions:
        for sc in ix.signal_checks:
            if sc.entry_number not in seen_entries and sc.entry_number not in seen_action_entries:
                seen_entries.add(sc.entry_number)
                sc_instructions = writer._signal_check_instructions(sc.arrows, room=ix.room)
                all_entries.append((sc.entry_number, sc.narrative, sc_instructions))

    all_entries.sort(key=lambda e: e[0])

    # Build signal check references for ledger entries
    # Map: entry_number -> signal check reference instruction
    from .compiler import signal_id as _signal_id
    entry_signal_refs = {}
    for ix in game.interactions:
        if ix.signal_checks:
            # Find the entry numbers for resolved interactions from this interaction
            for ri in game.resolved:
                if ri.source_line == ix.source_line and ri.room == ix.room:
                    entry_signal_refs[ri.entry_number] = _format_signal_check_instruction(
                        ix.signal_checks, entry_prefix, _signal_id, also=True
                    )

    for entry_num, narrative, instructions in all_entries:
        lines.append(f"\n{entry_prefix}-{entry_num}")
        body = narrative
        all_instructions = list(instructions)
        if entry_num in entry_signal_refs:
            all_instructions.append(entry_signal_refs[entry_num])
        if all_instructions:
            body += "\n\n" + "\n".join(f"- *{inst}*" for inst in all_instructions)
        lines.append(indent(body, ": ", lambda line: True))

    return "\n".join(lines)
