import re
from .models import (
    GameData, Verb, Noun, Item, Room, Arrow, Interaction, Cue,
)


class ParseError(Exception):
    def __init__(self, line_num, msg):
        super().__init__(f"Line {line_num}: {msg}")


# ── Parsing Helpers ─────────────────────────────────────────────────────────

def _indent(line: str) -> int:
    return (len(line) - len(line.lstrip(" "))) // 2

def _split_name(name: str) -> tuple[str, str | None]:
    if "__" in name:
        b, s = name.split("__", 1)
        return b, s
    return name, None

def _is_comment(line: str) -> bool:
    return line.strip().startswith("//")

def _is_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("# ")

def _parse_header(line: str) -> tuple[str, str | None]:
    """Parse a # header. Returns (section_type, name).
    Known sections (verbs, items, interactions) return (type, None).
    Everything else is a room name: ("room", name).
    """
    name = line.strip()[2:].strip()
    lower = name.lower()
    if lower in ("verbs", "items", "interactions"):
        return lower, None
    return "room", name

def _is_arrow(s: str) -> bool:
    return "->" in s

def _parse_arrow(text: str, ln: int) -> Arrow:
    parts = [p.strip() for p in text.split("->", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ParseError(ln, f"Bad arrow: {text}")
    return Arrow(parts[0], parts[1], ln)

def _strip_marker(s: str) -> tuple[str, str]:
    """Strip leading + or - marker. Returns (marker, content)."""
    if s.startswith("+ "):
        return "+", s[2:]
    if s.startswith("- "):
        return "-", s[2:]
    return "", s

def _has_colon_header(s: str) -> bool:
    return ":" in s and not s.startswith("//")

def _is_narrative(s: str) -> bool:
    """A line is narrative if it has no marker and no structural syntax."""
    if s.startswith("+ ") or s.startswith("- "):
        return False
    if "->" in s:
        return False
    if _is_header(s) or _is_comment(s):
        return False
    # ALL_CAPS with optional underscores = entity name, not narrative
    if re.match(r'^[A-Z][A-Z0-9_]*$', s):
        return False
    return True


# ── Frontmatter Parser ─────────────────────────────────────────────────────

def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse YAML-style frontmatter between --- fences. Returns (metadata, next_line_index)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta = {}
    i = 1
    while i < len(lines):
        line = lines[i].strip()
        if line == "---":
            return meta, i + 1
        if ":" in line and not line.startswith("//"):
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
        i += 1
    return meta, i


# ── Global Parser ───────────────────────────────────────────────────────────

def parse_global(source: str) -> GameData:
    game = GameData()
    lines = source.splitlines()

    # Parse frontmatter
    game.metadata, i = _parse_frontmatter(lines)

    # Collect description: text between frontmatter and first # header
    desc_lines = []
    while i < len(lines):
        line = lines[i].strip()
        if _is_header(lines[i]):
            break
        if line and not _is_comment(line):
            desc_lines.append(line)
        i += 1
    if desc_lines:
        game.metadata["description"] = "\n\n".join(desc_lines)

    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_comment(line):
            i += 1
            continue
        if _is_header(line):
            sec, _ = _parse_header(line)
            i += 1
            if sec == "verbs":
                while i < len(lines) and not _is_header(lines[i]):
                    w = lines[i].strip()
                    if w and not _is_comment(lines[i]):
                        game.verbs[w] = Verb(w)
                    i += 1
            elif sec == "items":
                while i < len(lines) and not _is_header(lines[i]):
                    w = lines[i].strip()
                    if w and not _is_comment(lines[i]):
                        game.items[w] = Item(w)
                    i += 1
            else:
                raise ParseError(i, f"Unknown global section: {sec}")
        else:
            i += 1
    return game


# ── Room Parser ─────────────────────────────────────────────────────────────

def parse_room_file(source: str, game: GameData) -> str:
    lines = source.splitlines()
    i = 0
    room_name = None

    # Skip any frontmatter in room files
    if lines and lines[0].strip() == "---":
        _, i = _parse_frontmatter(lines)

    while i < len(lines):
        line = lines[i].strip()
        if not line or _is_comment(line):
            i += 1
            continue
        if _is_header(line):
            sec, name = _parse_header(line)
            i += 1
            if sec == "room" and name:
                room_name = name
                base, state = _split_name(name)
                game.rooms[name] = Room(name, base, state)
                i = _parse_room_body(lines, i, game, room_name)
            elif sec == "interactions":
                if not room_name:
                    raise ParseError(i, "Interactions before room header")
                i = _parse_freeform_interactions(lines, i, game, room_name)
            else:
                raise ParseError(i, f"Unknown section: {sec}")
        else:
            i += 1
    return room_name


def _parse_room_body(lines, i, game, room_name):
    while i < len(lines) and not _is_header(lines[i]):
        line = lines[i]
        stripped = line.strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue

        ind = _indent(line)
        marker, content = _strip_marker(stripped)

        if ind == 0 and not marker:
            # Bare name at indent 0 = entity or room-level interaction
            if _has_colon_header(stripped) and not _is_arrow(stripped):
                # Room-level interaction: LOOK: desc or USE + ITEM:
                i = _parse_inline_interaction(
                    lines, i, game, room_name,
                    context_entity=f"@{room_name}", parent_indent=-1,
                )
            elif _is_arrow(stripped):
                arrow = _parse_arrow(stripped, i + 1)
                if arrow.subject == "room":
                    arrow.subject = f"@{room_name}"
                i += 1
                i = _parse_arrow_children(lines, i, game, room_name, arrow, 1)
            elif not _is_header(stripped):
                noun_name = stripped
                base, state = _split_name(noun_name)
                game.nouns[f"{room_name}::{noun_name}"] = Noun(
                    noun_name, base, state, room_name
                )
                i += 1
                i = _parse_entity_block(lines, i, game, room_name, noun_name, 0)
            else:
                break
        elif marker == "+":
            # + at indent 0 would be under a room-level entity — shouldn't happen
            # at root level without a prior entity, skip
            i += 1
        else:
            i += 1
    return i


def _parse_entity_block(lines, i, game, room_name, entity_name, entity_indent):
    """Parse children of an entity. Children are + or - lines indented deeper than entity_indent."""
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _is_header(line):
            break

        ind = _indent(line)
        marker, content = _strip_marker(stripped)

        # Must be indented deeper than entity, or + at same level (interactions on entity).
        # - arrows at entity_indent are siblings, not children.
        if ind < entity_indent:
            break
        if ind == entity_indent:
            if marker != "+":
                break

        if marker == "+":
            if _has_colon_header(content) and not _is_arrow(content):
                # Reconstruct the line without marker for interaction parsing
                i = _parse_inline_interaction(
                    lines, i, game, room_name, entity_name, entity_indent
                )
            else:
                i += 1
        elif marker == "-":
            if _is_arrow(content):
                arrow = _parse_arrow(content, i + 1)
                if arrow.subject == "room":
                    arrow.subject = f"@{room_name}"
                arr_indent = _indent(line)
                i += 1
                i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1)
            else:
                i += 1
        else:
            # No marker — could be a bare entity name at deeper indent
            if not _is_narrative(stripped) and ind > entity_indent:
                noun_name = stripped
                base, state = _split_name(noun_name)
                key = f"{room_name}::{noun_name}"
                if key not in game.nouns:
                    game.nouns[key] = Noun(noun_name, base, state, room_name)
                i += 1
                i = _parse_entity_block(lines, i, game, room_name, noun_name, ind)
            else:
                break
    return i


def _parse_inline_interaction(lines, i, game, room_name, context_entity, parent_indent):
    line = lines[i]
    stripped = line.strip()
    current_indent = _indent(line)

    # Strip + marker if present
    _, content = _strip_marker(stripped)

    header_part, _, after_colon = content.partition(":")
    header_part = header_part.strip()
    after_colon = after_colon.strip()

    if "+" in header_part:
        parts = [p.strip() for p in header_part.split("+")]
        verb = parts[0]
        extra_targets = [[a.strip() for a in p.split("|")] for p in parts[1:]]
    else:
        verb = header_part
        extra_targets = []

    target_groups = [[context_entity]] + extra_targets
    source_line = i + 1
    i += 1

    # Inline narrative (text after colon)
    narrative = after_colon if after_colon else ""

    arrows = []

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or _is_comment(bstripped):
            i += 1
            continue
        if _indent(bline) <= current_indent or _is_header(bline):
            break

        bmarker, bcontent = _strip_marker(bstripped)

        if bmarker == "-" and _is_arrow(bcontent):
            arrow = _parse_arrow(bcontent, i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=arrows)
        elif bmarker == "+":
            # A + line inside an interaction is a child of a prior arrow's state
            # This shouldn't happen at this level — break out
            break
        elif _is_narrative(bstripped) and not narrative:
            narrative = bstripped
            i += 1
        elif _is_narrative(bstripped) and narrative:
            # Additional narrative lines — append
            narrative += " " + bstripped
            i += 1
        else:
            i += 1

    ix = Interaction(
        verb=verb, target_groups=target_groups,
        narrative=narrative, arrows=arrows,
        source_line=source_line, room=room_name,
    )
    _register_interaction(game, ix)
    return i


def _parse_arrow_children(lines, i, game, room_name, arrow, child_indent, propagated_arrows=None):
    dest = arrow.destination

    # ? -> "Room" is a cue (cross-room deferred effect)
    if arrow.subject == "?":
        if not (dest.startswith('"') and dest.endswith('"')):
            raise ParseError(arrow.source_line, "Cue arrow (?) must target a quoted room name")
        target_room = dest[1:-1]
        narrative = ""
        cue_arrows = []
        while i < len(lines):
            line = lines[i]
            stripped = line.strip()
            if not stripped or _is_comment(stripped):
                i += 1
                continue
            if _indent(line) < child_indent or _is_header(line):
                break
            marker, content = _strip_marker(stripped)
            if marker == "-" and _is_arrow(content):
                a = _parse_arrow(content, i + 1)
                cue_arrows.append(a)
                i += 1
            elif _is_narrative(stripped):
                if narrative:
                    narrative += " " + stripped
                else:
                    narrative = stripped
                i += 1
            else:
                i += 1
        game.cues.append(Cue(
            target_room=target_room,
            narrative=narrative,
            arrows=cue_arrows,
            source_line=arrow.source_line,
            trigger_room=room_name,
        ))
        # Register any nouns that the cue arrows reveal in the target room
        # Strip trailing __ (base-state-only marker) for noun registration
        noun_room = target_room[:-2] if target_room.endswith("__") else target_room
        for ca in cue_arrows:
            if ca.destination == "room":
                subj = ca.subject
                base, state = _split_name(subj)
                key = f"{noun_room}::{subj}"
                if key not in game.nouns:
                    game.nouns[key] = Noun(subj, base, state, noun_room)
        return i

    if dest in ("trash", "player"):
        while i < len(lines):
            stripped = lines[i].strip()
            if not stripped or _is_comment(stripped):
                i += 1
                continue
            if _indent(lines[i]) < child_indent or _is_header(lines[i]):
                break
            i += 1
        return i

    if dest.startswith('"') and dest.endswith('"'):
        target_room = dest[1:-1]
        subject = arrow.subject
        if subject == "player":
            # player -> "Room" is movement, not a noun registration
            return i
        base, state = _split_name(subject)
        key = f"{target_room}::{subject}"
        if key not in game.nouns:
            game.nouns[key] = Noun(subject, base, state, target_room)
        return _parse_entity_block(lines, i, game, target_room, subject, child_indent - 1)

    if dest == "room":
        subject = arrow.subject
        base, state = _split_name(subject)
        key = f"{room_name}::{subject}"
        if key not in game.nouns:
            game.nouns[key] = Noun(subject, base, state, room_name)
        return _parse_entity_block(lines, i, game, room_name, subject, child_indent - 1)

    # Verb state transform (e.g. USE__RESTRAINED -> USE): skip, no children
    if arrow.subject in game.verbs or dest in game.verbs:
        return i

    # Entity state transform
    dest_name = dest
    if dest_name.startswith("@") or dest_name.startswith("room__"):
        # Room state transform
        if dest_name.startswith("room__"):
            dest_name = f"@{room_name}__{dest_name.split('__', 1)[1]}"
            arrow.destination = dest_name
        clean = dest_name.lstrip("@")
        base, state = _split_name(clean)
        if clean not in game.rooms:
            game.rooms[clean] = Room(clean, base, state)
        return _parse_room_state_children(lines, i, game, clean, child_indent, propagated_arrows)
    else:
        base, state = _split_name(dest_name)
        key = f"{room_name}::{dest_name}"
        if key not in game.nouns:
            game.nouns[key] = Noun(dest_name, base, state, room_name)
        return _parse_entity_block(lines, i, game, room_name, dest_name, child_indent - 1)


def _parse_room_state_children(lines, i, game, room_state_name, child_indent, propagated_arrows=None):
    """Parse children of a room state block.

    Any '-> room' arrows found here are collected into propagated_arrows
    so the parent interaction can generate player instructions for them.
    """
    room_entity = f"@{room_state_name}"
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _indent(line) < child_indent or _is_header(line):
            break

        marker, content = _strip_marker(stripped)

        if marker == "+":
            if _has_colon_header(content) and not _is_arrow(content):
                i = _parse_inline_interaction(
                    lines, i, game, room_state_name, room_entity, child_indent - 1
                )
            else:
                noun_name = content
                base, state = _split_name(noun_name)
                game.nouns[f"{room_state_name}::{noun_name}"] = Noun(
                    noun_name, base, state, room_state_name
                )
                i += 1
                i = _parse_entity_block(lines, i, game, room_state_name, noun_name, _indent(line))
        elif marker == "-":
            if _is_arrow(content):
                arrow = _parse_arrow(content, i + 1)
                if propagated_arrows is not None and arrow.destination == "room":
                    propagated_arrows.append(arrow)
                i += 1
                i = _parse_arrow_children(lines, i, game, room_state_name, arrow, _indent(line) + 1, propagated_arrows)
            else:
                i += 1
        else:
            # Bare name = noun in room state
            noun_name = stripped
            base, state = _split_name(noun_name)
            game.nouns[f"{room_state_name}::{noun_name}"] = Noun(
                noun_name, base, state, room_state_name
            )
            i += 1
            i = _parse_entity_block(lines, i, game, room_state_name, noun_name, _indent(line))
    return i


def _register_interaction(game, interaction):
    for existing in game.interactions:
        if (existing.verb == interaction.verb and
                existing.target_groups == interaction.target_groups and
                existing.room == interaction.room):
            raise ParseError(
                interaction.source_line,
                f"Duplicate: {interaction.label} (first at line {existing.source_line})"
            )
    game.interactions.append(interaction)


def _parse_freeform_interactions(lines, i, game, room_name):
    while i < len(lines) and not _is_header(lines[i]):
        line = lines[i].strip()
        if not line or _is_comment(line):
            i += 1
            continue
        if "+" in line and line.endswith(":"):
            header = line[:-1].strip()
            parts = [p.strip() for p in header.split("+")]
            verb = parts[0]
            target_groups = [[a.strip() for a in p.split("|")] for p in parts[1:]]
            source_line = i + 1
            i += 1
            narrative = ""
            arrows = []
            while i < len(lines) and not _is_header(lines[i]):
                bline = lines[i]
                bs = bline.strip()
                if not bs or _is_comment(bs):
                    i += 1
                    continue
                if not bline.startswith("  "):
                    break
                bmarker, bcontent = _strip_marker(bs)
                if bmarker == "-" and _is_arrow(bcontent):
                    a = _parse_arrow(bcontent, i + 1)
                    if a.subject == "room":
                        a.subject = f"@{room_name}"
                    arrows.append(a)
                    arr_indent = _indent(bline)
                    i += 1
                    i = _parse_arrow_children(lines, i, game, room_name, a, arr_indent + 1, propagated_arrows=arrows)
                elif bmarker == "+":
                    break
                elif _is_narrative(bs) and not narrative:
                    narrative = bs
                    i += 1
                elif _is_narrative(bs):
                    narrative += " " + bs
                    i += 1
                else:
                    i += 1
            _register_interaction(game, Interaction(
                verb=verb, target_groups=target_groups,
                narrative=narrative, arrows=arrows,
                source_line=source_line, room=room_name,
            ))
            continue
        raise ParseError(i + 1, f"Unexpected: {line}")
    return i
