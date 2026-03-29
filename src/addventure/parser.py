import re
from .models import (
    GameData, Verb, Noun, Item, Room, Arrow, Interaction,
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

def _is_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("---") and s.endswith("---")

def _parse_header(line: str) -> tuple[str, str | None]:
    inner = line.strip().strip("-").strip()
    m = re.match(r'"([^"]*)"', inner)
    if m:
        return "room", m.group(1)
    return inner, None

def _is_arrow(s: str) -> bool:
    return "->" in s and not s.startswith('"')

def _parse_arrow(text: str, ln: int) -> Arrow:
    parts = [p.strip() for p in text.split("->", 1)]
    if len(parts) != 2 or not parts[0] or not parts[1]:
        raise ParseError(ln, f"Bad arrow: {text}")
    return Arrow(parts[0], parts[1], ln)

def _has_colon_header(s: str) -> bool:
    return ":" in s and not s.startswith('"') and not s.startswith("#")


# ── Global Parser ───────────────────────────────────────────────────────────

def parse_global(source: str) -> GameData:
    game = GameData()
    lines = source.splitlines()
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
            i += 1
            continue
        if _is_header(line):
            sec, _ = _parse_header(line)
            i += 1
            if sec == "verbs":
                while i < len(lines) and not _is_header(lines[i]):
                    w = lines[i].strip()
                    if w and not w.startswith("#"):
                        game.verbs[w] = Verb(w)
                    i += 1
            elif sec == "items":
                while i < len(lines) and not _is_header(lines[i]):
                    w = lines[i].strip()
                    if w and not w.startswith("#"):
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

    while i < len(lines):
        line = lines[i].strip()
        if not line or line.startswith("#"):
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
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        ind = _indent(line)
        if ind == 0:
            if _has_colon_header(stripped) and not _is_arrow(stripped):
                # Room-level interaction: LOOK: "desc" or USE + ITEM:
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
            elif not stripped.startswith("---"):
                noun_name = stripped
                base, state = _split_name(noun_name)
                game.nouns[f"{room_name}::{noun_name}"] = Noun(
                    noun_name, base, state, room_name
                )
                i += 1
                i = _parse_entity_block(lines, i, game, room_name, noun_name, 1)
            else:
                break
        else:
            i += 1
    return i


def _parse_entity_block(lines, i, game, room_name, entity_name, base_indent):
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if _indent(line) < base_indent or _is_header(line):
            break
        if _has_colon_header(stripped) and not _is_arrow(stripped):
            i = _parse_inline_interaction(
                lines, i, game, room_name, entity_name, base_indent - 1
            )
        elif _is_arrow(stripped):
            arrow = _parse_arrow(stripped, i + 1)
            arr_indent = _indent(line)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1)
        else:
            i += 1
    return i


def _parse_inline_interaction(lines, i, game, room_name, context_entity, parent_indent):
    line = lines[i]
    stripped = line.strip()
    current_indent = _indent(line)

    header_part, _, after_colon = stripped.partition(":")
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

    narrative = ""
    if after_colon.startswith('"') and after_colon.endswith('"'):
        narrative = after_colon[1:-1]

    arrows = []

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or bstripped.startswith("#"):
            i += 1
            continue
        if _indent(bline) <= current_indent or _is_header(bline):
            break
        if bstripped.startswith('"') and bstripped.endswith('"') and not narrative:
            narrative = bstripped[1:-1]
            i += 1
        elif _is_arrow(bstripped):
            arrow = _parse_arrow(bstripped, i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1)
        else:
            i += 1

    ix = Interaction(
        verb=verb, target_groups=target_groups,
        narrative=narrative, arrows=arrows,
        source_line=source_line, room=room_name,
    )
    _register_interaction(game, ix)
    return i


def _parse_arrow_children(lines, i, game, room_name, arrow, child_indent):
    dest = arrow.destination

    if dest in ("trash", "player"):
        while i < len(lines):
            if not lines[i].strip() or lines[i].strip().startswith("#"):
                i += 1
                continue
            if _indent(lines[i]) < child_indent or _is_header(lines[i]):
                break
            i += 1
        return i

    if dest.startswith('"') and dest.endswith('"'):
        target_room = dest[1:-1]
        subject = arrow.subject
        base, state = _split_name(subject)
        key = f"{target_room}::{subject}"
        if key not in game.nouns:
            game.nouns[key] = Noun(subject, base, state, target_room)
        return _parse_entity_block(lines, i, game, target_room, subject, child_indent)

    if dest == "room":
        subject = arrow.subject
        base, state = _split_name(subject)
        key = f"{room_name}::{subject}"
        if key not in game.nouns:
            game.nouns[key] = Noun(subject, base, state, room_name)
        return _parse_entity_block(lines, i, game, room_name, subject, child_indent)

    # Transform
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
        return _parse_room_state_children(lines, i, game, clean, child_indent)
    else:
        base, state = _split_name(dest_name)
        key = f"{room_name}::{dest_name}"
        if key not in game.nouns:
            game.nouns[key] = Noun(dest_name, base, state, room_name)
        return _parse_entity_block(lines, i, game, room_name, dest_name, child_indent)


def _parse_room_state_children(lines, i, game, room_state_name, child_indent):
    room_entity = f"@{room_state_name}"
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue
        if _indent(line) < child_indent or _is_header(line):
            break

        if _has_colon_header(stripped) and not _is_arrow(stripped):
            i = _parse_inline_interaction(
                lines, i, game, room_state_name, room_entity, child_indent - 1
            )
        elif _is_arrow(stripped):
            arrow = _parse_arrow(stripped, i + 1)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_state_name, arrow, _indent(line) + 1)
        else:
            noun_name = stripped
            base, state = _split_name(noun_name)
            game.nouns[f"{room_state_name}::{noun_name}"] = Noun(
                noun_name, base, state, room_state_name
            )
            i += 1
            i = _parse_entity_block(lines, i, game, room_state_name, noun_name, _indent(line) + 1)
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
        if not line or line.startswith("#"):
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
                if not bs or bs.startswith("#"):
                    i += 1
                    continue
                if not bline.startswith("  "):
                    break
                if bs.startswith('"') and bs.endswith('"'):
                    narrative = bs[1:-1]
                elif _is_arrow(bs):
                    a = _parse_arrow(bs, i + 1)
                    if a.subject == "room":
                        a.subject = f"@{room_name}"
                    arrows.append(a)
                i += 1
            _register_interaction(game, Interaction(
                verb=verb, target_groups=target_groups,
                narrative=narrative, arrows=arrows,
                source_line=source_line, room=room_name,
            ))
            continue
        raise ParseError(i + 1, f"Unexpected: {line}")
    return i
