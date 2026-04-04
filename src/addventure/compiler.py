import random
from itertools import combinations, product as cart_product

from .models import (
    GameData, Verb, Noun, Item, Interaction, ResolvedInteraction, Cue,
)
from .parser import parse_global, parse_room_file, _split_name, ParseError


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
    for n in game.nouns.values():
        n.id = entity_pool.pop()

    # Reserve derived inventory IDs (TAKE + noun_id) from the pool
    take = game.verbs.get("TAKE")
    if take and game.auto_items:
        reserved = set()
        for key, noun in game.nouns.items():
            if noun.name in game.auto_items or noun.base in game.auto_items:
                inv_id = take.id + noun.id
                reserved.add(inv_id)
        entity_pool = [n for n in entity_pool if n not in reserved]

    # Allocate explicit (non-auto) items from pool
    for name, it in game.items.items():
        if name not in game.auto_items:
            it.id = entity_pool.pop()

    # Derive auto-item IDs: TAKE + base noun ID
    # If no base noun exists, fall back to a stated noun with matching base
    if take:
        for name in game.auto_items:
            for key, noun in game.nouns.items():
                if noun.name == name and noun.state is None:
                    game.items[name].id = take.id + noun.id
                    break
            else:
                for key, noun in game.nouns.items():
                    if noun.base == name:
                        game.items[name].id = take.id + noun.id
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
    for key, noun in game.nouns.items():
        if noun.state is None:
            continue
        for (verb, base, room), parent in parent_map.items():
            if base == noun.base and room == noun.room:
                if (verb, noun.name, room) not in child_exists:
                    new_ixs.append(Interaction(
                        verb=parent.verb, target_groups=[[noun.name]],
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


# ── Auto Item Registration ────────────────────────────────────────────────

def auto_register_items(game: GameData):
    """Auto-create Items for nouns that have -> player arrows."""
    pickup_nouns: dict[str, list[tuple[str, int]]] = {}  # base_name -> [(room, line)]
    for ix in game.interactions:
        for a in ix.arrows:
            if a.destination == "player" and a.subject != "player":
                # Use base name: KEY__UNREACHABLE -> player registers as KEY
                base, _ = _split_name(a.subject)
                if base not in pickup_nouns:
                    pickup_nouns[base] = []
                pickup_nouns[base].append((ix.room, a.source_line))

    if not pickup_nouns:
        return

    if not game.verbs.get("TAKE"):
        first_line = next(iter(pickup_nouns.values()))[0][1]
        raise ParseError(first_line, "Arrow '-> player' requires a TAKE verb in # Verbs")

    for name, locations in pickup_nouns.items():
        if name in game.items:
            continue
        rooms = {room for room, _ in locations}
        if len(rooms) > 1:
            raise ParseError(
                locations[0][1],
                f"Noun '{name}' has -> player in multiple rooms ({', '.join(sorted(rooms))}). "
                f"Use # Items to declare it explicitly, or rename one."
            )
        game.items[name] = Item(name)
        game.auto_items.add(name)


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
    if key in game.nouns:
        return game.nouns[key].id
    base_room = room.split("__", 1)[0]
    for n in game.nouns.values():
        noun_base_room = n.room.split("__", 1)[0]
        if n.name == name and noun_base_room == base_room:
            return n.id
    if name in game.items:
        return game.items[name].id
    return None


def duplicate_item_interactions(game: GameData):
    """Create parallel ResolvedInteractions using inventory IDs for auto-items.

    For every resolved interaction that references an auto-item noun,
    create a copy with the noun ID swapped for the inventory ID in the sum.
    Skips:
    - Acquisition interactions (those with -> player arrow for the item)
    - Verbs already explicitly defined for the item (room="")
    """
    if not game.auto_items:
        return

    # Build noun_id -> (item_id, item_name) mapping for all auto-item nouns
    id_map: dict[int, tuple[int, str]] = {}
    for name in game.auto_items:
        item = game.items[name]
        for key, noun in game.nouns.items():
            if noun.name == name:
                id_map[noun.id] = (item.id, name)

    # Collect verbs already explicitly defined for each item
    existing: set[tuple[str, str]] = set()  # (verb, item_name)
    for ri in game.resolved:
        if ri.room == "":
            for target in ri.targets:
                if target in game.auto_items:
                    existing.add((ri.verb, target))
    for ix in game.suppressed_interactions:
        if ix.room == "":
            for group in ix.target_groups:
                for target in group:
                    if target in game.auto_items:
                        existing.add((ix.verb, target))

    new_resolved = []
    for ri in game.resolved:
        # Check if any target in this interaction is an auto-item noun
        for target in ri.targets:
            noun_id = get_entity_id(target, game, ri.room)
            if noun_id and noun_id in id_map:
                inv_id, item_name = id_map[noun_id]
                # Strip "item -> player" arrows — item is already in inventory
                inv_arrows = [
                    a for a in ri.arrows
                    if not (a.subject == item_name and a.destination == "player")
                ]
                # Skip acquisition interactions: those where removing the
                # -> player arrow leaves no other arrows (the interaction's
                # sole purpose is acquiring the item)
                had_player_arrow = len(inv_arrows) < len(ri.arrows)
                if had_player_arrow and not inv_arrows:
                    continue
                # Skip verbs already explicitly defined for this item
                if (ri.verb, item_name) in existing:
                    continue
                new_sum = ri.sum_id - noun_id + inv_id
                new_resolved.append(ResolvedInteraction(
                    verb=ri.verb,
                    targets=ri.targets,
                    sum_id=new_sum,
                    narrative=ri.narrative,
                    arrows=inv_arrows,
                    source_line=ri.source_line,
                    room=ri.room,
                    parent_label=ri.parent_label,
                    from_inventory=frozenset({item_name}),
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

        if ix.target_groups == [["*"]]:
            # Collect entities that have explicit interactions with this verb
            explicit = set()
            for other in game.interactions:
                if other is ix:
                    continue
                if other.verb == ix.verb and other.room == ix.room:
                    if len(other.target_groups) == 1 and len(other.target_groups[0]) == 1:
                        explicit.add(other.target_groups[0][0])
            targets = {}
            for key, n in game.nouns.items():
                if n.room == ix.room and n.name not in explicit:
                    targets[n.name] = n.id
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
    for key, n in game.nouns.items():
        all_ids[n.name] = n.id
    for n, it in game.items.items():
        # Use a distinct key for auto-items so noun ID isn't overwritten
        label = f"{n}(inv)" if n in game.auto_items else n
        all_ids[label] = it.id
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
            duplicate_item_interactions(game)
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
    auto_register_items(game)

    if not _try_compile_pass(game, max_retries):
        # Fall back to 4-digit entity IDs for larger games
        _reset_mutable(game)
        if not _try_compile_pass(game, max_retries, four_digit=True):
            raise RuntimeError(
                f"No collision-free allocation in {max_retries * 2} attempts."
            )

    resolve_cues(game)

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
            # trashes an entity that differs between noun/inventory.
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
    # Shuffle entry numbers so ledger order doesn't reveal game structure.
    # Deterministic: seeded by random.seed(attempt) in the allocation loop.
    unique_entries = list(range(1, entry_num + 1))
    random.shuffle(unique_entries)
    remap = {old: new for old, new in zip(range(1, entry_num + 1), unique_entries)}
    for ri in game.resolved:
        ri.entry_number = remap[ri.entry_number]
    cue_primary_entry = {k: remap[v] for k, v in cue_primary_entry.items()}

    # Copy entry numbers back to cue objects
    for cue in game.cues:
        cue.entry_number = cue_primary_entry.get(cue.id, 0)

    return game
