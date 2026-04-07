import re
from .models import (
    GameData, Verb, RoomObject, InventoryObject, Room, Arrow, Interaction, Cue, Action, Signal, SignalCheck,
)


class ParseError(Exception):
    def __init__(self, line_num, msg):
        super().__init__(f"Line {line_num}: {msg}")


# ── Parsing Helpers ─────────────────────────────────────────────────────────

_NAME_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*$")
_STATED_NAME_RE = re.compile(r"^[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*(?:__[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)?$")
_OBJECT_REF_RE = re.compile(r"^(?:[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*(?:__[A-Z][A-Z0-9]*(?:_[A-Z0-9]+)*)?|\*)$")

def _indent(line: str, ln: int | None = None) -> int:
    prefix = line[:len(line) - len(line.lstrip(" \t"))]
    if "\t" in prefix:
        raise ParseError(ln or 0, "Tabs are not allowed for indentation; use spaces")
    return len(prefix)

def _split_name(name: str) -> tuple[str, str | None]:
    if "__" in name:
        b, s = name.split("__", 1)
        return b, s
    return name, None

def _is_comment(line: str) -> bool:
    return line.strip().startswith("//")

def _strip_trailing_comment(line: str) -> str:
    """Strip trailing // comments from structural lines."""
    idx = line.find("//")
    if idx == -1:
        return line
    return line[:idx].rstrip()

def _normalize_structural_line(line: str) -> str:
    """Normalize a structural line before parsing.

    For lines without a colon, trailing // comments are stripped.
    For lines with a colon, the text after the first colon is preserved so
    inline narrative can contain literal // text.
    """
    if ":" not in line:
        return _strip_trailing_comment(line).strip()
    header, _, tail = line.partition(":")
    return f"{_strip_trailing_comment(header).strip()}:{tail.strip()}"

def _is_header(line: str) -> bool:
    s = line.strip()
    return s.startswith("## ") or s.startswith("# ")

def _parse_header(line: str) -> tuple[str, str | None]:
    """Parse a # or ## header. Returns (section_type, name).
    Known sections (verbs, items, interactions) return (type, None).
    Everything else is a room name: ("room", name).
    """
    s = line.strip()
    name = s[3:].strip() if s.startswith("## ") else s[2:].strip()
    lower = name.lower()
    if lower in ("verbs", "inventory", "interactions", "signals"):
        return lower, None
    return "room", name

def _is_arrow(s: str) -> bool:
    return "->" in s

def _parse_arrow(text: str, ln: int) -> Arrow:
    parts = [p.strip() for p in text.split("->", 1)]
    if len(parts) != 2 or not parts[1]:
        raise ParseError(ln, f"Bad arrow: {text}")
    subject, destination = parts
    if subject:
        _validate_arrow_endpoint(subject, ln, "arrow subject")
    _validate_arrow_endpoint(destination, ln, "arrow destination")
    signal_name = None
    if destination.startswith("signal "):
        signal_name = destination[7:].strip()
    return Arrow(subject, destination, ln, signal_name=signal_name)

def _strip_marker(s: str) -> tuple[str, str]:
    """Strip leading + or - marker. Returns (marker, content)."""
    if s.startswith("+ "):
        return "+", s[2:]
    if s.startswith("- "):
        return "-", s[2:]
    return "", s

def _has_colon_header(s: str) -> bool:
    return ":" in s and not s.startswith("//")

def _is_action(s: str) -> bool:
    return s.startswith("> ")

def _is_sealed_fence(s: str) -> bool:
    """Check if a line is a fragment block fence (opening or closing)."""
    return s == ":::" or s == "::: fragment"

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

def _is_name(s: str) -> bool:
    return bool(_NAME_RE.match(s))

def _is_object_ref(s: str) -> bool:
    return bool(_OBJECT_REF_RE.match(s))

def _is_stated_name(s: str) -> bool:
    return bool(_STATED_NAME_RE.match(s))

def _require_name(value: str, ln: int, what: str) -> str:
    if not _is_name(value):
        raise ParseError(ln, f"Invalid {what}: {value}")
    return value

def _require_object_ref(value: str, ln: int, what: str) -> str:
    if not _is_object_ref(value):
        raise ParseError(ln, f"Invalid {what}: {value}")
    return value

def _require_stated_name(value: str, ln: int, what: str) -> str:
    if not _is_stated_name(value):
        raise ParseError(ln, f"Invalid {what}: {value}")
    return value

def _validate_arrow_endpoint(value: str, ln: int, what: str) -> None:
    if value in {"player", "room", "trash", "?"}:
        return
    if value.startswith('"') and value.endswith('"'):
        return
    if value.startswith("room__"):
        _require_name(value.split("__", 1)[1], ln, f"{what} room state")
        return
    if value.startswith("signal "):
        sig_name = value[7:].strip()
        if not _is_name(sig_name):
            raise ParseError(ln, f"Invalid signal name: {sig_name}")
        return
    _require_object_ref(value, ln, what)

def _validate_target_groups(target_groups: list[list[str]], ln: int) -> None:
    wildcard_groups = [group for group in target_groups if "*" in group]
    if not wildcard_groups:
        return
    if target_groups != [["*"]]:
        raise ParseError(ln, "Wildcard '*' is only allowed as the entire target list")


_KNOWN_FRONTMATTER_KEYS = {
    "title", "author", "start", "entry_prefix",
    "image", "image_height", "name_style",
}


# ── Frontmatter Parser ─────────────────────────────────────────────────────

def _parse_frontmatter(lines: list[str]) -> tuple[dict[str, str], int]:
    """Parse YAML-style frontmatter between --- fences. Returns (metadata, next_line_index)."""
    if not lines or lines[0].strip() != "---":
        return {}, 0
    meta = {}
    i = 1
    while i < len(lines):
        line = _strip_trailing_comment(lines[i]).strip()
        if line == "---":
            return meta, i + 1
        if ":" in line and line:
            key, _, val = line.partition(":")
            meta[key.strip()] = val.strip()
        elif line:
            raise ParseError(i + 1, f"Invalid frontmatter line: {line}")
        i += 1
    return meta, i


def _unexpected_child_line(lines, i, child_indent):
    """Return (line_index, stripped_line) for the first child line in a no-children block."""
    while i < len(lines):
        stripped = lines[i].strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _is_header(lines[i]) or _indent(lines[i], i + 1) < child_indent:
            return None
        return i, stripped
    return None


# ── Signal Check Parser ─────────────────────────────────────────────────────

def _parse_signal_check_group(lines, i):
    """Parse a group of NAME? / otherwise? blocks. Returns (next_i, list[SignalCheck])."""
    checks = []
    saw_otherwise = False

    while i < len(lines):
        stripped = _strip_trailing_comment(lines[i]).strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _is_header(lines[i]):
            break

        if stripped == "otherwise?":
            if saw_otherwise:
                raise ParseError(i + 1, "Duplicate otherwise? in signal check")
            saw_otherwise = True
            signal_name = None
            i += 1
        elif stripped.endswith("?") and len(stripped) > 1 and _is_name(stripped[:-1]):
            if saw_otherwise:
                raise ParseError(i + 1, "otherwise? must be the last branch in a signal check")
            signal_name = stripped[:-1]
            i += 1
        else:
            break

        # Parse indented body: narrative lines and arrows
        narrative_lines = []
        arrows = []
        block_indent = None
        while i < len(lines):
            line = lines[i]
            line_stripped = _strip_trailing_comment(line).strip()
            if not line_stripped or _is_comment(line_stripped):
                i += 1
                continue
            ind = _indent(line, i + 1)
            if block_indent is None:
                if ind == 0:
                    break  # No indented body
                block_indent = ind
            if ind < block_indent:
                break
            if line_stripped.startswith("- ") and _is_arrow(line_stripped[2:]):
                arrow = _parse_arrow(_strip_trailing_comment(line_stripped[2:]), i + 1)
                arrows.append(arrow)
            else:
                narrative_lines.append(line_stripped)
            i += 1

        narrative = "\n".join(narrative_lines)
        checks.append(SignalCheck(signal_name=signal_name, narrative=narrative, arrows=arrows))

    return i, checks


# ── Global Parser ───────────────────────────────────────────────────────────

def parse_global(source: str) -> GameData:
    game = GameData()
    lines = source.splitlines()

    # Parse frontmatter
    game.metadata, i = _parse_frontmatter(lines)
    for key in game.metadata:
        if key not in _KNOWN_FRONTMATTER_KEYS:
            game.warnings.append(f"Unknown frontmatter key: {key}")

    # Collect description and signal checks: text between frontmatter and first # header
    desc_lines = []
    while i < len(lines):
        line = lines[i]
        stripped = _strip_trailing_comment(line).strip()
        if _is_header(line):
            break
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        # Check for signal check block: NAME? or otherwise?
        if stripped == "otherwise?" or (stripped.endswith("?") and len(stripped) > 1 and _is_name(stripped[:-1])):
            i, checks = _parse_signal_check_group(lines, i)
            game.signal_checks = checks
            # Consume remaining blank/comment lines before header
            while i < len(lines) and not _is_header(lines[i]) and not _strip_trailing_comment(lines[i]).strip():
                i += 1
            break
        desc_lines.append(stripped)
        i += 1
    if desc_lines:
        game.metadata["description"] = "\n\n".join(desc_lines)

    while i < len(lines):
        line = _strip_trailing_comment(lines[i]).strip()
        if not line or _is_comment(line):
            i += 1
            continue
        if _is_header(line):
            sec, _ = _parse_header(line)
            i += 1
            if sec == "verbs":
                while i < len(lines) and not _is_header(lines[i]):
                    w = _strip_trailing_comment(lines[i]).strip()
                    if w and not _is_comment(w):
                        if _indent(lines[i], i + 1) != 0:
                            raise ParseError(i + 1, f"Unexpected indentation in # Verbs: {w}")
                        if w.startswith(("+ ", "- ", "> ")) or _is_arrow(w) or ":" in w:
                            raise ParseError(i + 1, f"Invalid verb declaration: {w}")
                        _require_name(w, i + 1, "verb name")
                        game.verbs[w] = Verb(w)
                    i += 1
            elif sec == "inventory":
                while i < len(lines) and not _is_header(lines[i]):
                    w = _strip_trailing_comment(lines[i]).strip()
                    if w and not _is_comment(w):
                        if _indent(lines[i], i + 1) != 0:
                            raise ParseError(i + 1, f"Unexpected indentation in # Inventory: {w}")
                        if w.startswith(("+ ", "- ", "> ")) or _is_arrow(w):
                            raise ParseError(i + 1, f"Invalid inventory object declaration: {w}")
                        _require_name(w, i + 1, "inventory object name")
                        item_indent = _indent(lines[i], i + 1)
                        game.inventory[w] = InventoryObject(w)
                        i += 1
                        i = _parse_entity_block(lines, i, game, room_name="", entity_name=w, entity_indent=item_indent)
                    else:
                        i += 1
            elif sec == "signals":
                while i < len(lines) and not _is_header(lines[i]):
                    w = _strip_trailing_comment(lines[i]).strip()
                    if w and not _is_comment(w):
                        if _indent(lines[i], i + 1) != 0:
                            raise ParseError(i + 1, f"Unexpected indentation in # Signals: {w}")
                        if not _is_name(w):
                            raise ParseError(i + 1, f"Invalid signal name: {w}")
                        from .compiler import signal_id as _signal_id
                        game.signals[w] = Signal(w, _signal_id(w))
                    i += 1
            else:
                raise ParseError(i, f"Unknown global section: {sec}")
        else:
            raise ParseError(i + 1, f"Unexpected line in global file: {line}")
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
        line = _strip_trailing_comment(lines[i]).strip()
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
            raise ParseError(i + 1, f"Unexpected line in room file: {line}")
    return room_name


def _parse_room_body(lines, i, game, room_name):
    while i < len(lines) and not _is_header(lines[i]):
        line = lines[i]
        stripped = _normalize_structural_line(line)
        if not stripped or _is_comment(stripped):
            i += 1
            continue

        ind = _indent(line, i + 1)
        marker, content = _strip_marker(stripped)

        if _is_action(stripped):
            i = _parse_action(lines, i, game, room_name, discovered=False, parent_indent=-1)
            continue

        if ind == 0 and not marker:
            # Bare name at indent 0 = entity or room-level interaction
            if _has_colon_header(stripped) and not _is_arrow(stripped):
                # Room-level interaction: LOOK: desc or USE + ITEM:
                i = _parse_inline_interaction(
                    lines, i, game, room_name,
                    context_entity=f"@{room_name}", parent_indent=-1,
                    content_override=stripped,
                )
            elif _is_arrow(stripped):
                arrow = _parse_arrow(stripped, i + 1)
                if arrow.subject == "room":
                    arrow.subject = f"@{room_name}"
                i += 1
                i = _parse_arrow_children(lines, i, game, room_name, arrow, 1)
            elif not _is_header(stripped):
                obj_name = stripped
                _require_stated_name(obj_name, i + 1, "room object name")
                base, state = _split_name(obj_name)
                key = f"{room_name}::{obj_name}"
                existing = game.objects.get(key)
                game.objects[key] = RoomObject(
                    obj_name, base, state, room_name,
                    discovered=existing.discovered if existing else False,
                )
                i += 1
                i = _parse_entity_block(lines, i, game, room_name, obj_name, 0)
            else:
                break
        else:
            raise ParseError(i + 1, f"Unexpected line in room body: {stripped}")
    return i


def _parse_entity_block(lines, i, game, room_name, entity_name, entity_indent, propagated_arrows=None):
    """Parse children of an entity. Children are + or - lines indented deeper than entity_indent."""
    while i < len(lines):
        line = lines[i]
        stripped = _normalize_structural_line(line)
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _is_header(line):
            break

        ind = _indent(line, i + 1)
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
                    lines, i, game, room_name, entity_name, entity_indent,
                    content_override=stripped,
                )
            else:
                raise ParseError(i + 1, f"Unexpected line in entity block: {stripped}")
        elif marker == "-":
            if _is_arrow(content):
                arrow = _parse_arrow(_strip_trailing_comment(content), i + 1)
                if arrow.subject == "room":
                    arrow.subject = f"@{room_name}"
                if propagated_arrows is not None:
                    propagated_arrows.append(arrow)
                arr_indent = _indent(line, i + 1)
                i += 1
                i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=propagated_arrows)
            else:
                raise ParseError(i + 1, f"Unexpected line in entity block: {stripped}")
        else:
            if _is_action(stripped):
                i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=entity_indent)
                continue
            # No marker — could be a bare entity name at deeper indent
            if _is_sealed_fence(stripped):
                raise ParseError(i + 1, "Fragment blocks must be inside an interaction (+ block)")
            elif not _is_narrative(stripped) and ind > entity_indent:
                obj_name = stripped
                _require_stated_name(obj_name, i + 1, "room object name")
                base, state = _split_name(obj_name)
                key = f"{room_name}::{obj_name}"
                if key not in game.objects:
                    game.objects[key] = RoomObject(obj_name, base, state, room_name)
                i += 1
                i = _parse_entity_block(lines, i, game, room_name, obj_name, ind)
            else:
                raise ParseError(i + 1, f"Unexpected line in entity block: {stripped}")
    return i


def _parse_inline_interaction(lines, i, game, room_name, context_entity, parent_indent, content_override=None):
    line = lines[i]
    stripped = line.strip()
    current_indent = _indent(line, i + 1)
    source_line = i + 1

    # Strip + marker if present
    _, content = _strip_marker(content_override if content_override is not None else stripped)

    header_part, _, after_colon = content.partition(":")
    header_part = header_part.strip()
    after_colon = after_colon.strip()

    if "+" in header_part:
        parts = [p.strip() for p in header_part.split("+")]
        verb = _require_stated_name(parts[0], source_line, "verb name")
        extra_targets = [[_require_object_ref(a.strip(), source_line, "target") for a in p.split("|")] for p in parts[1:]]
    else:
        verb = _require_stated_name(header_part, source_line, "verb name")
        extra_targets = []

    target_groups = [[context_entity]] + extra_targets
    _validate_target_groups(extra_targets, source_line)
    i += 1

    # Inline narrative (text after colon)
    narrative = after_colon if after_colon else ""

    arrows = []
    sealed_content = None
    blank_line_seen = False

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or _is_comment(bstripped):
            if narrative:
                blank_line_seen = True
            i += 1
            continue
        if _indent(bline, i + 1) <= current_indent or _is_header(bline):
            break

        bmarker, bcontent = _strip_marker(bstripped)

        if bmarker == "-" and _is_arrow(bcontent):
            arrow = _parse_arrow(_strip_trailing_comment(bcontent), i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline, i + 1)
            i += 1
            blank_line_seen = False
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=arrows)
        elif bmarker == "+":
            # A + line inside an interaction is a child of a prior arrow's state
            # This shouldn't happen at this level — break out
            raise ParseError(i + 1, f"Unexpected line in interaction body: {bstripped}")
        elif _is_sealed_fence(bstripped):
            if sealed_content is not None:
                raise ParseError(i + 1, "Multiple fragment blocks in one interaction")
            if bstripped != "::: fragment":
                raise ParseError(i + 1, "Expected '::: fragment' to open a fragment block")
            i += 1
            sealed_lines = []
            while i < len(lines):
                sline = lines[i]
                sstripped = sline.strip()
                if sstripped == ":::":
                    i += 1
                    break
                if _is_header(sline):
                    raise ParseError(i + 1, "Unclosed fragment block (hit header)")
                sealed_lines.append(sstripped)
                i += 1
            else:
                raise ParseError(i, "Unclosed fragment block (hit end of file)")
            # Each non-empty line is its own paragraph; blank lines are separators
            paragraphs = [sl for sl in sealed_lines if sl]
            sealed_content = "\n\n".join(paragraphs)
        elif _is_action(bstripped):
            action_name = bstripped[2:].strip()
            action_line = i + 1
            blank_line_seen = False
            i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=current_indent)
            arrows.append(Arrow(f">{action_name}", "room", action_line))
        elif _is_narrative(bstripped) and not narrative:
            narrative = bstripped
            blank_line_seen = False
            i += 1
        elif _is_narrative(bstripped) and narrative:
            # Blank line since last narrative = new paragraph; otherwise same paragraph
            if blank_line_seen:
                narrative += "\n\n" + bstripped
            else:
                narrative += " " + bstripped
            blank_line_seen = False
            i += 1
        else:
            raise ParseError(i + 1, f"Unexpected line in interaction body: {bstripped}")

    ix = Interaction(
        verb=verb, target_groups=target_groups,
        narrative=narrative, arrows=arrows,
        source_line=source_line, room=room_name,
        sealed_content=sealed_content,
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
            stripped = _strip_trailing_comment(line).strip()
            if not stripped or _is_comment(stripped):
                i += 1
                continue
            if _indent(line, i + 1) < child_indent or _is_header(line):
                break
            marker, content = _strip_marker(stripped)
            if marker == "-" and _is_arrow(content):
                a = _parse_arrow(_strip_trailing_comment(content), i + 1)
                cue_arrows.append(a)
                i += 1
            elif _is_narrative(stripped):
                if narrative:
                    narrative += "\n\n" + stripped
                else:
                    narrative = stripped
                i += 1
            else:
                raise ParseError(i + 1, f"Unexpected line in cue block: {stripped}")
        game.cues.append(Cue(
            target_room=target_room,
            narrative=narrative,
            arrows=cue_arrows,
            source_line=arrow.source_line,
            trigger_room=room_name,
        ))
        # Register any room objects that the cue arrows reveal in the target room
        # Strip trailing __ (base-state-only marker) for room object registration
        obj_room = target_room[:-2] if target_room.endswith("__") else target_room
        for ca in cue_arrows:
            if ca.destination == "room":
                subj = ca.subject
                base, state = _split_name(subj)
                key = f"{obj_room}::{subj}"
                if key not in game.objects:
                    game.objects[key] = RoomObject(subj, base, state, obj_room, discovered=True)
                else:
                    game.objects[key].discovered = True
        return i

    if dest == "trash":
        unexpected = _unexpected_child_line(lines, i, child_indent)
        if unexpected is not None:
            line_idx, stripped = unexpected
            raise ParseError(line_idx + 1, f"Arrow to trash cannot have children: {stripped}")
        return i

    if dest == "player":
        subject = arrow.subject
        return _parse_entity_block(lines, i, game, room_name="", entity_name=subject, entity_indent=child_indent - 1)

    if dest.startswith('"') and dest.endswith('"'):
        target_room = dest[1:-1]
        subject = arrow.subject
        if subject == "player":
            # player -> "Room" is movement, not a room object registration
            unexpected = _unexpected_child_line(lines, i, child_indent)
            if unexpected is not None:
                line_idx, stripped = unexpected
                raise ParseError(line_idx + 1, f"Movement arrow cannot have children: {stripped}")
            return i
        base, state = _split_name(subject)
        key = f"{target_room}::{subject}"
        if key not in game.objects:
            game.objects[key] = RoomObject(subject, base, state, target_room)
        return _parse_entity_block(lines, i, game, target_room, subject, child_indent - 1)

    if dest == "room":
        subject = arrow.subject
        base, state = _split_name(subject)
        key = f"{room_name}::{subject}"
        if key not in game.objects:
            game.objects[key] = RoomObject(subject, base, state, room_name, discovered=True)
        else:
            game.objects[key].discovered = True
        return _parse_entity_block(lines, i, game, room_name, subject, child_indent - 1)

    # -> VERBNAME (verb reveal): skip, no children
    if arrow.subject == "":
        unexpected = _unexpected_child_line(lines, i, child_indent)
        if unexpected is not None:
            line_idx, stripped = unexpected
            raise ParseError(line_idx + 1, f"Verb reveal arrow cannot have children: {stripped}")
        return i

    # Verb state transform (e.g. USE__RESTRAINED -> USE): skip, no children
    if arrow.subject in game.verbs or dest in game.verbs:
        unexpected = _unexpected_child_line(lines, i, child_indent)
        if unexpected is not None:
            line_idx, stripped = unexpected
            raise ParseError(line_idx + 1, f"Verb arrow cannot have children: {stripped}")
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
        if key not in game.objects:
            game.objects[key] = RoomObject(dest_name, base, state, room_name)
        return _parse_entity_block(lines, i, game, room_name, dest_name, child_indent - 1, propagated_arrows=propagated_arrows)


def _parse_room_state_children(lines, i, game, room_state_name, child_indent, propagated_arrows=None):
    """Parse children of a room state block.

    Any '-> room' arrows found here are collected into propagated_arrows
    so the parent interaction can generate player instructions for them.
    """
    room_entity = f"@{room_state_name}"
    while i < len(lines):
        line = lines[i]
        stripped = _strip_trailing_comment(line).strip()
        if not stripped or _is_comment(stripped):
            i += 1
            continue
        if _indent(line, i + 1) < child_indent or _is_header(line):
            break

        marker, content = _strip_marker(stripped)

        if marker == "+":
            if _has_colon_header(content) and not _is_arrow(content):
                i = _parse_inline_interaction(
                    lines, i, game, room_state_name, room_entity, child_indent - 1
                )
            else:
                obj_name = content
                _require_stated_name(obj_name, i + 1, "room object name")
                base, state = _split_name(obj_name)
                game.objects[f"{room_state_name}::{obj_name}"] = RoomObject(
                    obj_name, base, state, room_state_name
                )
                i += 1
                i = _parse_entity_block(lines, i, game, room_state_name, obj_name, _indent(line, i + 1))
        elif marker == "-":
            if _is_arrow(content):
                arrow = _parse_arrow(_strip_trailing_comment(content), i + 1)
                if propagated_arrows is not None and arrow.destination == "room":
                    propagated_arrows.append(arrow)
                i += 1
                i = _parse_arrow_children(lines, i, game, room_state_name, arrow, _indent(line, i + 1) + 1, propagated_arrows)
            else:
                raise ParseError(i + 1, f"Unexpected line in room-state block: {stripped}")
        else:
            # Bare name = room object in room state
            obj_name = stripped
            _require_stated_name(obj_name, i + 1, "room object name")
            base, state = _split_name(obj_name)
            game.objects[f"{room_state_name}::{obj_name}"] = RoomObject(
                obj_name, base, state, room_state_name
            )
            i += 1
            i = _parse_entity_block(lines, i, game, room_state_name, obj_name, _indent(line, i + 1))
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


def _parse_action(lines, i, game, room_name, discovered, parent_indent):
    """Parse a > ACTION_NAME block. Returns next line index."""
    line = lines[i]
    stripped = _strip_trailing_comment(line).strip()
    action_name = stripped[2:].strip()  # strip "> "
    source_line = i + 1
    _require_name(action_name, source_line, "action name")
    current_indent = _indent(line, i + 1)
    i += 1

    narrative = ""
    arrows = []

    while i < len(lines):
        bline = lines[i]
        bstripped = bline.strip()
        if not bstripped or _is_comment(bstripped):
            i += 1
            continue
        if _indent(bline, i + 1) <= current_indent or _is_header(bline):
            break

        bmarker, bcontent = _strip_marker(bstripped)

        if _is_action(bstripped):
            raise ParseError(i + 1, f"Actions cannot nest directly under actions: {bstripped}")

        if bmarker == "-" and _is_arrow(bcontent):
            arrow = _parse_arrow(_strip_trailing_comment(bcontent), i + 1)
            if arrow.subject == "room":
                arrow.subject = f"@{room_name}"
            arrows.append(arrow)
            arr_indent = _indent(bline, i + 1)
            i += 1
            i = _parse_arrow_children(lines, i, game, room_name, arrow, arr_indent + 1, propagated_arrows=arrows)
        elif _is_narrative(bstripped) and not narrative:
            narrative = bstripped
            i += 1
        elif _is_narrative(bstripped) and narrative:
            narrative += "\n\n" + bstripped
            i += 1
        else:
            raise ParseError(i + 1, f"Unexpected line in action body: {bstripped}")

    key = f"{room_name}::{action_name}"
    game.actions[key] = Action(
        name=action_name,
        room=room_name,
        narrative=narrative,
        arrows=arrows,
        discovered=discovered,
    )
    return i


def _parse_freeform_interactions(lines, i, game, room_name):
    while i < len(lines) and not _is_header(lines[i]):
        line = _strip_trailing_comment(lines[i]).strip()
        if not line or _is_comment(line):
            i += 1
            continue
        if "+" in line and line.endswith(":"):
            header = line[:-1].strip()
            parts = [p.strip() for p in header.split("+")]
            verb = _require_stated_name(parts[0], i + 1, "verb name")
            target_groups = [[_require_object_ref(a.strip(), i + 1, "target") for a in p.split("|")] for p in parts[1:]]
            _validate_target_groups(target_groups, i + 1)
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
                if _indent(bline, i + 1) == 0:
                    break
                bmarker, bcontent = _strip_marker(bs)
                if bmarker == "-" and _is_arrow(bcontent):
                    a = _parse_arrow(_strip_trailing_comment(bcontent), i + 1)
                    if a.subject == "room":
                        a.subject = f"@{room_name}"
                    arrows.append(a)
                    arr_indent = _indent(bline, i + 1)
                    i += 1
                    i = _parse_arrow_children(lines, i, game, room_name, a, arr_indent + 1, propagated_arrows=arrows)
                elif bmarker == "+":
                    break
                elif _is_action(bs):
                    action_name = bs[2:].strip()
                    action_line = i + 1
                    i = _parse_action(lines, i, game, room_name, discovered=True, parent_indent=0)
                    arrows.append(Arrow(f">{action_name}", "room", action_line))
                elif _is_narrative(bs) and not narrative:
                    narrative = bs
                    i += 1
                elif _is_narrative(bs):
                    narrative += "\n\n" + bs
                    i += 1
                else:
                    raise ParseError(i + 1, f"Unexpected line in interaction body: {bs}")
            _register_interaction(game, Interaction(
                verb=verb, target_groups=target_groups,
                narrative=narrative, arrows=arrows,
                source_line=source_line, room=room_name,
            ))
            continue
        raise ParseError(i + 1, f"Unexpected: {line}")
    return i
