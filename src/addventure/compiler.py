import hashlib
import random
from itertools import combinations, product as cart_product

from .models import (
    GameData, Verb, RoomObject, InventoryObject, Interaction, ResolvedInteraction, Cue, Action, SealedText,
)
from .parser import parse_global, parse_room_file, _split_name, ParseError


_SIGNAL_CHARS = "BCDFGHJKLMNPQRSTVWXZ"  # consonants minus Y — can't form words


def signal_id(name: str) -> str:
    """Derive a deterministic 4-character code from a signal name.

    Uses 20 consonants (no vowels, no Y), giving 160,000 possible codes.
    Codes are visually distinct from numeric entity IDs.
    """
    h = hashlib.sha256(name.encode()).hexdigest()
    n = int(h[:8], 16)
    chars = []
    for _ in range(4):
        chars.append(_SIGNAL_CHARS[n % 20])
        n //= 20
    return "".join(chars)


# ── ID Allocation ───────────────────────────────────────────────────────────

def _valid_verb_id(n):
    return 11 <= n <= 99 and n % 10 != 0 and n % 5 != 0

def _valid_entity_id(n, four_digit=False):
    hi = 9999 if four_digit else 999
    lo = 1000 if four_digit else 100
    return lo <= n <= hi and n % 10 != 0 and n % 5 != 0


def _try_allocate(game: GameData, four_digit=False):
    if four_digit:
        verb_pool = [n for n in range(101, 1000) if _valid_entity_id(n)]
    else:
        verb_pool = [n for n in range(11, 100) if _valid_verb_id(n)]
    random.shuffle(verb_pool)
    for v in game.verbs.values():
        v.id = verb_pool.pop()

    lo, hi = (1000, 10000) if four_digit else (100, 1000)
    entity_pool = [n for n in range(lo, hi) if _valid_entity_id(n, four_digit)]
    random.shuffle(entity_pool)
    for r in game.rooms.values():
        r.id = entity_pool.pop()
    for obj in game.objects.values():
        obj.id = entity_pool.pop()

    # Reserve derived inventory IDs (TAKE + room_obj_id) from the pool
    take = game.verbs.get("TAKE")
    if take and game.auto_inventory:
        reserved = set()
        for key, room_obj in game.objects.items():
            if room_obj.name in game.auto_inventory or room_obj.base in game.auto_inventory:
                inv_id = take.id + room_obj.id
                reserved.add(inv_id)
        entity_pool = [n for n in entity_pool if n not in reserved]

    # Allocate explicit (non-auto) inventory objects from pool
    for name, inv_obj in game.inventory.items():
        if name not in game.auto_inventory:
            inv_obj.id = entity_pool.pop()

    # Derive auto-inventory IDs: TAKE + base room object ID
    # If no base room object exists, fall back to a stated room object with matching base
    if take:
        for name in game.auto_inventory:
            for key, room_obj in game.objects.items():
                if room_obj.name == name and room_obj.state is None:
                    game.inventory[name].id = take.id + room_obj.id
                    break
            else:
                for key, room_obj in game.objects.items():
                    if room_obj.base == name:
                        game.inventory[name].id = take.id + room_obj.id
                        break

    for cue in game.cues:
        cue.id = entity_pool.pop()


# ── Verb State Registration ────────────────────────────────────────────────

def register_verb_states(game: GameData):
    needed = set()
    for ix in game.interactions:
        if "__" in ix.verb and ix.verb not in game.verbs:
            needed.add(ix.verb)
        for arrow in ix.arrows:
            for name in (arrow.subject, arrow.destination):
                if name.startswith("@"):
                    continue
                if "__" in name:
                    base, _ = _split_name(name)
                    if base in game.verbs and name not in game.verbs:
                        needed.add(name)
    used = {v.id for v in game.verbs.values()}
    pool = [n for n in range(11, 100) if _valid_verb_id(n) and n not in used]
    random.shuffle(pool)
    for vn in sorted(needed):
        game.verbs[vn] = Verb(vn, pool.pop())


# ── Inheritance ─────────────────────────────────────────────────────────────

def apply_inheritance(game: GameData):
    parent_map: dict[tuple[str, str, str], Interaction] = {}
    child_exists: set[tuple[str, str, str]] = set()

    for ix in game.interactions:
        if len(ix.target_groups) == 1 and len(ix.target_groups[0]) == 1:
            target = ix.target_groups[0][0]
            base, state = _split_name(target.lstrip("@"))
            if state is not None:
                child_exists.add((ix.verb, target, ix.room))
            elif not ix.arrows:
                # Only inherit arrow-free interactions (observations, not actions)
                parent_map[(ix.verb, target.lstrip("@"), ix.room)] = ix

    new_ixs = []
    for key, room_obj in game.objects.items():
        if room_obj.state is None:
            continue
        for (verb, base, room), parent in parent_map.items():
            if base == room_obj.base and room == room_obj.room:
                if (verb, room_obj.name, room) not in child_exists:
                    new_ixs.append(Interaction(
                        verb=parent.verb, target_groups=[[room_obj.name]],
                        narrative=parent.narrative, arrows=[],
                        source_line=parent.source_line, room=room,
                    ))

    for name, rm in game.rooms.items():
        if rm.state is None:
            continue
        for (verb, base, room), parent in parent_map.items():
            if base == rm.base and (verb, f"@{name}", name) not in child_exists:
                new_ixs.append(Interaction(
                    verb=parent.verb, target_groups=[[f"@{name}"]],
                    narrative=parent.narrative, arrows=[],
                    source_line=parent.source_line, room=name,
                ))

    game.interactions.extend(new_ixs)


# ── Auto Verb Registration ────────────────────────────────────────────────

def auto_register_verbs(game: GameData):
    """Auto-create Verbs from -> VERBNAME arrows (empty subject = verb reveal)."""
    for ix in game.interactions:
        for a in ix.arrows:
            if a.subject == "" and a.destination not in game.verbs:
                game.verbs[a.destination] = Verb(a.destination)
                game.auto_verbs.add(a.destination)
    for cue in game.cues:
        for a in cue.arrows:
            if a.subject == "" and a.destination not in game.verbs:
                game.verbs[a.destination] = Verb(a.destination)
                game.auto_verbs.add(a.destination)


# ── Auto Inventory Registration ────────────────────────────────────────────────

def auto_register_inventory(game: GameData):
    """Auto-create InventoryObjects for room objects that have -> player arrows."""
    pickup_objects: dict[str, list[tuple[str, int]]] = {}  # base_name -> [(room, line)]
    for ix in game.interactions:
        for a in ix.arrows:
            if a.destination == "player" and a.subject != "player":
                # Use base name: KEY__UNREACHABLE -> player registers as KEY
                base, _ = _split_name(a.subject)
                if base not in pickup_objects:
                    pickup_objects[base] = []
                pickup_objects[base].append((ix.room, a.source_line))

    if not pickup_objects:
        return

    if not game.verbs.get("TAKE"):
        first_line = next(iter(pickup_objects.values()))[0][1]
        raise ParseError(first_line, "Arrow '-> player' requires a TAKE verb in # Verbs")

    for name, locations in pickup_objects.items():
        if name in game.inventory:
            continue
        rooms = {room for room, _ in locations}
        if len(rooms) > 1:
            raise ParseError(
                locations[0][1],
                f"Room object '{name}' has -> player in multiple rooms ({', '.join(sorted(rooms))}). "
                f"Use # Inventory to declare it explicitly, or rename one."
            )
        game.inventory[name] = InventoryObject(name)
        game.auto_inventory.add(name)


# ── Cue Resolution ──────────────────────────────────────────────────────────

def _cue_target_rooms(cue: Cue, game: GameData) -> list[str]:
    """Determine which room IDs a cue resolves against.

    - "Room"     → base room + all Room__STATE variants
    - "Room__"   → base room only (trailing __ = base state)
    - "Room__X"  → that specific state only
    """
    target = cue.target_room

    # Trailing __ = base state only
    if target.endswith("__"):
        base_name = target[:-2]
        rm = game.rooms.get(base_name)
        if not rm:
            raise ParseError(cue.source_line, f"Cue targets unknown room: {base_name}")
        return [base_name]

    # Explicit state (contains __)
    if "__" in target:
        rm = game.rooms.get(target)
        if not rm:
            raise ParseError(cue.source_line, f"Cue targets unknown room state: {target}")
        return [target]

    # Plain room name → base + all states
    rm = game.rooms.get(target)
    if not rm:
        raise ParseError(cue.source_line, f"Cue targets unknown room: {target}")
    names = [target]
    for name, r in game.rooms.items():
        if r.base == target and r.state is not None:
            names.append(name)
    return names


def cue_targets_room_name(target: str, room_name: str) -> bool:
    """Return whether a cue target string resolves against a specific room name."""
    if target.endswith("__"):
        return room_name == target[:-2]
    if "__" in target:
        return room_name == target
    return room_name == target or room_name.startswith(target + "__")


def resolve_cues(game: GameData):
    """Create ResolvedInteractions for each cue.

    A cue may resolve against multiple room states, producing multiple
    potentials entries that share the same ledger entry number.
    """
    for cue in game.cues:
        room_names = _cue_target_rooms(cue, game)
        first_ri = None
        for rn in room_names:
            rm = game.rooms[rn]
            sum_id = cue.id + rm.id
            ri = ResolvedInteraction(
                verb="CUE",
                targets=[],
                sum_id=sum_id,
                narrative=cue.narrative,
                arrows=cue.arrows,
                source_line=cue.source_line,
                room=rn,
                parent_label=f"Cue #{cue.id}",
            )
            game.resolved.append(ri)
            if first_ri is None:
                first_ri = ri
                cue.sum_id = sum_id


# ── Resolver ────────────────────────────────────────────────────────────────

def get_entity_id(name: str, game: GameData, room: str) -> int | None:
    if name.startswith("@"):
        rm = game.rooms.get(name[1:])
        return rm.id if rm else None
    key = f"{room}::{name}"
    if key in game.objects:
        return game.objects[key].id
    base_room = room.split("__", 1)[0]
    for obj in game.objects.values():
        obj_base_room = obj.room.split("__", 1)[0]
        if obj.name == name and obj_base_room == base_room:
            return obj.id
    if name in game.inventory:
        return game.inventory[name].id
    return None


def duplicate_inventory_interactions(game: GameData):
    """Create parallel ResolvedInteractions using inventory IDs for auto-inventory objects.

    For every resolved interaction that references an auto-inventory room object,
    create a copy with the room object ID swapped for the inventory ID in the sum.
    Skips:
    - Acquisition interactions (those with -> player arrow for the inventory object)
    - Verbs already explicitly defined for the inventory object (room="")
    """
    if not game.auto_inventory:
        return

    # Build room_obj_id -> (inv_obj_id, inv_obj_name) mapping for all auto-inventory room objects
    id_map: dict[int, tuple[int, str]] = {}
    for name in game.auto_inventory:
        inv_obj = game.inventory[name]
        for key, room_obj in game.objects.items():
            if room_obj.name == name:
                id_map[room_obj.id] = (inv_obj.id, name)

    # Collect verbs already explicitly defined for each inventory object
    existing: set[tuple[str, str]] = set()  # (verb, inv_obj_name)
    for ri in game.resolved:
        if ri.room == "":
            for target in ri.targets:
                if target in game.auto_inventory:
                    existing.add((ri.verb, target))
    for ix in game.suppressed_interactions:
        if ix.room == "":
            for group in ix.target_groups:
                for target in group:
                    if target in game.auto_inventory:
                        existing.add((ix.verb, target))

    new_resolved = []
    for ri in game.resolved:
        # Check if any target in this interaction is an auto-inventory room object
        for target in ri.targets:
            room_obj_id = get_entity_id(target, game, ri.room)
            if room_obj_id and room_obj_id in id_map:
                inv_id, inv_obj_name = id_map[room_obj_id]
                # Strip "inv_obj -> player" arrows — inventory object already picked up
                inv_arrows = [
                    a for a in ri.arrows
                    if not (a.subject == inv_obj_name and a.destination == "player")
                ]
                # Skip acquisition interactions: those where removing the
                # -> player arrow leaves no other arrows (the interaction's
                # sole purpose is acquiring the inventory object)
                had_player_arrow = len(inv_arrows) < len(ri.arrows)
                if had_player_arrow and not inv_arrows:
                    continue
                # Skip verbs already explicitly defined for this inventory object
                if (ri.verb, inv_obj_name) in existing:
                    continue
                new_sum = ri.sum_id - room_obj_id + inv_id
                new_resolved.append(ResolvedInteraction(
                    verb=ri.verb,
                    targets=ri.targets,
                    sum_id=new_sum,
                    narrative=ri.narrative,
                    arrows=inv_arrows,
                    source_line=ri.source_line,
                    room=ri.room,
                    parent_label=ri.parent_label,
                    from_inventory=frozenset({inv_obj_name}),
                ))

    game.resolved.extend(new_resolved)


def resolve_interactions(game: GameData):
    game.resolved = []
    game.suppressed_interactions = []
    for ix in game.interactions:
        vid = game.verbs.get(ix.verb)
        if not vid:
            raise ParseError(ix.source_line, f"Unknown verb: {ix.verb}")

        # Empty interaction (no narrative, no arrows) — suppress, don't resolve
        if not ix.narrative and not ix.arrows:
            game.suppressed_interactions.append(ix)
            continue

        if ix.target_groups == [["*"]] or (
                len(ix.target_groups) == 2 and ix.target_groups[1] == ["*"]):
            # Collect entities that have explicit interactions with this verb
            explicit = set()
            for other in game.interactions:
                if other is ix:
                    continue
                if other.verb == ix.verb and other.room == ix.room:
                    if len(other.target_groups) == 1 and len(other.target_groups[0]) == 1:
                        explicit.add(other.target_groups[0][0])
            targets = {}
            for key, room_obj in game.objects.items():
                if room_obj.room == ix.room and room_obj.name not in explicit:
                    targets[room_obj.name] = room_obj.id
            for ename, eid in targets.items():
                game.resolved.append(ResolvedInteraction(
                    verb=ix.verb, targets=[ename], sum_id=vid.id + eid,
                    narrative=ix.narrative, arrows=ix.arrows,
                    source_line=ix.source_line, room=ix.room,
                    parent_label=ix.label,
                ))
            continue

        for combo in cart_product(*ix.target_groups):
            targets = list(combo)
            total = vid.id
            for t in targets:
                eid = get_entity_id(t, game, ix.room)
                if eid is None:
                    raise ParseError(ix.source_line, f"Unknown target: {t}")
                total += eid
            game.resolved.append(ResolvedInteraction(
                verb=ix.verb, targets=targets, sum_id=total,
                narrative=ix.narrative, arrows=ix.arrows,
                source_line=ix.source_line, room=ix.room,
                parent_label=ix.label,
            ))

    # Assign entry numbers
    for idx, ri in enumerate(game.resolved, 1):
        ri.entry_number = idx


# ── Collision Detection ────────────────────────────────────────────────────

def check_authored_collisions(game: GameData) -> list[str]:
    errors = []
    seen: dict[int, ResolvedInteraction] = {}
    for ri in game.resolved:
        if ri.sum_id in seen:
            other = seen[ri.sum_id]
            errors.append(
                f"COLLISION: sum {ri.sum_id} — "
                f"[{ri.parent_label}] vs [{other.parent_label}]"
            )
        else:
            seen[ri.sum_id] = ri
    return errors


def check_potential_collisions(game: GameData) -> list[str]:
    all_ids = {}
    for key, room_obj in game.objects.items():
        all_ids[room_obj.name] = room_obj.id
    for name, inv_obj in game.inventory.items():
        # Use a distinct key for auto-inventory objects so room object ID isn't overwritten
        label = f"{name}(inv)" if name in game.auto_inventory else name
        all_ids[label] = inv_obj.id
    for n, rm in game.rooms.items():
        all_ids[f"@{n}"] = rm.id

    names = list(all_ids.keys())
    sums: dict[int, list[str]] = {}
    for v in game.verbs.values():
        for en, eid in all_ids.items():
            s = v.id + eid
            sums.setdefault(s, []).append(f"{v.name} + {en}")
        for a, b in combinations(names, 2):
            s = v.id + all_ids[a] + all_ids[b]
            sums.setdefault(s, []).append(f"{v.name} + {a} + {b}")

    return [
        f"sum {s}: {' | '.join(exprs)}"
        for s, exprs in sums.items() if len(exprs) > 1
    ]


# ── Auto-generation ───────────────────────────────────────────────────────

def ensure_room_looks(game: GameData):
    """Auto-generate LOOK + @room for any base room missing one."""
    if "LOOK" not in game.verbs:
        return

    has_look = set()
    for ix in game.interactions:
        if ix.verb == "LOOK" and len(ix.target_groups) == 1:
            target = ix.target_groups[0][0]
            if target.startswith("@"):
                has_look.add(target[1:])

    for room_name, rm in game.rooms.items():
        if rm.state is not None:
            continue
        if room_name not in has_look:
            game.interactions.append(Interaction(
                verb="LOOK",
                target_groups=[[f"@{room_name}"]],
                narrative="You look around.",
                arrows=[],
                source_line=0,
                room=room_name,
            ))


# ── Sealed Text Ref Generation ────────────────────────────────────────────

# Letters that avoid visual ambiguity (no I, O, S, Z)
_GREEK_LETTERS = [
    "Alpha", "Beta", "Gamma", "Delta", "Epsilon", "Zeta", "Eta", "Theta",
    "Iota", "Kappa", "Lambda", "Mu", "Nu", "Xi", "Omicron", "Pi", "Rho",
    "Sigma", "Tau", "Upsilon", "Phi", "Chi", "Psi", "Omega",
]

def _generate_sealed_refs(count: int) -> list[str]:
    """Generate sequential Greek letter reference codes for sealed texts."""
    refs = []
    for i in range(count):
        letter = _GREEK_LETTERS[i % len(_GREEK_LETTERS)]
        cycle = i // len(_GREEK_LETTERS)
        ref = f"{letter}-{cycle + 1}" if cycle > 0 else letter
        refs.append(ref)
    return refs


# ── Compile Pipeline ───────────────────────────────────────────────────────

def _reset_mutable(game: GameData):
    """Reset state that changes between allocation attempts."""
    game.resolved = []
    game.suppressed_interactions = []
    for cue in game.cues:
        cue.id = 0
        cue.sum_id = 0
        cue.entry_number = 0


def _try_compile_pass(game: GameData, max_retries: int, four_digit: bool = False) -> bool:
    """Try random allocations. Returns True if collision-free."""
    for attempt in range(max_retries):
        random.seed(attempt)
        _try_allocate(game, four_digit=four_digit)
        register_verb_states(game)
        apply_inheritance(game)
        resolve_interactions(game)
        if not check_authored_collisions(game):
            duplicate_inventory_interactions(game)
            if not check_authored_collisions(game):
                return True
        _reset_mutable(game)
    return False


def compile_game(global_source: str, room_sources: list[str],
                 max_retries=200) -> GameData:
    """
    Full compilation: parse → allocate IDs (with retry) → resolve → cues.
    Tries 3-digit entity IDs first, falls back to 4-digit for large games.
    Returns a validated GameData ready for the writer.
    """
    if max_retries < 1:
        raise ValueError("max_retries must be >= 1")

    game = parse_global(global_source)
    for src in room_sources:
        parse_room_file(src, game)

    ensure_room_looks(game)
    auto_register_verbs(game)
    auto_register_inventory(game)

    if not _try_compile_pass(game, max_retries):
        # Fall back to 4-digit entity IDs for larger games
        _reset_mutable(game)
        if not _try_compile_pass(game, max_retries, four_digit=True):
            raise RuntimeError(
                f"No collision-free allocation in {max_retries * 2} attempts."
            )

    resolve_cues(game)

    # Collect signal emissions from all resolved interactions
    for ri in game.resolved:
        for arrow in ri.arrows:
            if arrow.signal_name:
                game.signal_emissions.add(arrow.signal_name)
    for action in game.actions.values():
        for arrow in action.arrows:
            if arrow.signal_name:
                game.signal_emissions.add(arrow.signal_name)

    # Mark objects discovered via signal check arrows (-> room)
    start_room = game.metadata.get("start", "")
    if not start_room:
        for rm in game.rooms.values():
            if rm.state is None:
                start_room = rm.name
                break

    def _mark_signal_discovered(arrow, default_room):
        if arrow.destination != "room" or not arrow.subject or arrow.subject == "player":
            return
        subj = arrow.subject
        base, state = _split_name(subj)
        key = f"{default_room}::{subj}"
        if key in game.objects:
            game.objects[key].discovered = True
        else:
            game.objects[key] = RoomObject(subj, base, state, default_room, discovered=True)

    for sc in game.signal_checks:
        for arrow in sc.arrows:
            _mark_signal_discovered(arrow, start_room)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            for arrow in sc.arrows:
                _mark_signal_discovered(arrow, ix.room)

    # Validate signal names don't collide with game entities
    all_signal_names = set(game.signal_emissions)
    for sc in game.signal_checks:
        all_signal_names.update(sc.signal_names)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            all_signal_names.update(sc.signal_names)
    entity_names = (
        set(game.verbs.keys())
        | {obj.name for obj in game.objects.values()}
        | {rm.name for rm in game.rooms.values()}
        | set(game.inventory.keys())
    )
    for name in all_signal_names & entity_names:
        game.warnings.append(f"Signal name collides with game entity: {name}")

    # Renumber entries. Deduplicate entries with identical content:
    # - Cue aliases (same cue, different room state) share entry numbers
    # - Interactions with same narrative + arrows (e.g. wildcard expansions)
    cue_primary_entry = {}  # cue.id -> entry_number
    content_entry = {}  # (narrative, arrows_key) -> entry_number
    entry_num = 0
    for ri in game.resolved:
        if ri.verb == "CUE":
            # Extract cue id from parent_label "Cue #NNN"
            cue_id = int(ri.parent_label.split("#")[1])
            if cue_id in cue_primary_entry:
                ri.entry_number = cue_primary_entry[cue_id]
            else:
                entry_num += 1
                ri.entry_number = entry_num
                cue_primary_entry[cue_id] = entry_num
        else:
            arrows_key = tuple((a.subject, a.destination) for a in ri.arrows)
            # Include from_inventory in the dedup key only when it
            # would produce different instructions — i.e. when an arrow
            # trashes an entity that differs between room object/inventory.
            inv_key = frozenset(
                name for name in ri.from_inventory
                if any(a.subject == name and a.destination == "trash"
                       for a in ri.arrows)
            )
            key = (ri.narrative, arrows_key, inv_key)
            if key in content_entry:
                ri.entry_number = content_entry[key]
            else:
                entry_num += 1
                ri.entry_number = entry_num
                content_entry[key] = entry_num
    # Assign ledger entry numbers to actions, deduplicating by arrows + narrative
    action_content = {}  # arrows_key -> (entry_number, action_with_narrative)
    for action in game.actions.values():
        arrows_key = tuple((a.subject, a.destination) for a in action.arrows)
        if arrows_key in action_content:
            existing_entry, existing_action = action_content[arrows_key]
            # Check narrative compatibility
            if action.narrative and existing_action.narrative and action.narrative != existing_action.narrative:
                # Different narratives — unique entry
                entry_num += 1
                action.ledger_id = entry_num
            else:
                # Share entry; inherit narrative if needed
                action.ledger_id = existing_entry
                if not action.narrative and existing_action.narrative:
                    action.narrative = existing_action.narrative
                elif action.narrative and not existing_action.narrative:
                    existing_action.narrative = action.narrative
        else:
            entry_num += 1
            action.ledger_id = entry_num
            action_content[arrows_key] = (entry_num, action)

    # Assign entry numbers to signal checks (index-level)
    for sc in game.signal_checks:
        entry_num += 1
        sc.entry_number = entry_num

    # Assign entry numbers to signal checks (interaction-level)
    for ix in game.interactions:
        for sc in ix.signal_checks:
            entry_num += 1
            sc.entry_number = entry_num

    # Shuffle entry numbers so ledger order doesn't reveal game structure.
    # Deterministic: seeded by random.seed(attempt) in the allocation loop.
    unique_entries = list(range(1, entry_num + 1))
    random.shuffle(unique_entries)
    remap = {old: new for old, new in zip(range(1, entry_num + 1), unique_entries)}
    for ri in game.resolved:
        ri.entry_number = remap[ri.entry_number]
    for action in game.actions.values():
        action.ledger_id = remap[action.ledger_id]
    cue_primary_entry = {k: remap[v] for k, v in cue_primary_entry.items()}
    for sc in game.signal_checks:
        sc.entry_number = remap[sc.entry_number]
    for ix in game.interactions:
        for sc in ix.signal_checks:
            sc.entry_number = remap[sc.entry_number]

    # Copy entry numbers back to cue objects
    for cue in game.cues:
        cue.entry_number = cue_primary_entry.get(cue.id, 0)

    # Create SealedText objects from interactions with sealed_content
    sealed_interactions = [
        (ix, ri) for ix in game.interactions if ix.sealed_content
        for ri in game.resolved
        if ri.verb == ix.verb and ri.room == ix.room
        and ri.source_line == ix.source_line
    ]
    if sealed_interactions:
        refs = _generate_sealed_refs(len(sealed_interactions))
        for (ix, ri), ref in zip(sealed_interactions, refs):
            game.sealed_texts.append(SealedText(
                ref=ref,
                content=ix.sealed_content,
                images=[],
                source_line=ix.source_line,
                room=ix.room,
                entry_number=ri.entry_number,
            ))

    return game
