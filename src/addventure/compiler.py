import random
from itertools import combinations, product as cart_product

from .models import (
    GameData, Verb, Noun, Interaction, ResolvedInteraction, RoomAlert,
)
from .parser import parse_global, parse_room_file, _split_name, ParseError


# ── ID Allocation ───────────────────────────────────────────────────────────

def _valid_verb_id(n):
    return 11 <= n <= 99 and n % 10 != 0 and n % 5 != 0

def _valid_entity_id(n):
    return 100 <= n <= 999 and n % 10 != 0 and n % 5 != 0


def _try_allocate(game: GameData):
    verb_pool = [n for n in range(11, 100) if _valid_verb_id(n)]
    random.shuffle(verb_pool)
    for v in game.verbs.values():
        v.id = verb_pool.pop()

    entity_pool = [n for n in range(100, 1000) if _valid_entity_id(n)]
    random.shuffle(entity_pool)
    for r in game.rooms.values():
        r.id = entity_pool.pop()
    for n in game.nouns.values():
        n.id = entity_pool.pop()
    for it in game.items.values():
        it.id = entity_pool.pop()


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
            else:
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


# ── Room Alerts ─────────────────────────────────────────────────────────────

def generate_room_alerts(game: GameData):
    counter = 1
    for ix in game.interactions:
        for arrow in ix.arrows:
            dest = arrow.destination
            if dest.startswith('"') and dest.endswith('"'):
                target_room = dest[1:-1]
                if target_room != ix.room:
                    game.alerts.append(RoomAlert(
                        trigger_room=ix.room,
                        target_room=target_room,
                        trigger_label=ix.label,
                        alert_number=counter,
                        resolution_arrows=[arrow],
                    ))
                    counter += 1


# ── Resolver ────────────────────────────────────────────────────────────────

def get_entity_id(name: str, game: GameData, room: str) -> int | None:
    if name.startswith("@"):
        rm = game.rooms.get(name[1:])
        return rm.id if rm else None
    key = f"{room}::{name}"
    if key in game.nouns:
        return game.nouns[key].id
    for k, n in game.nouns.items():
        if n.name == name:
            return n.id
    if name in game.items:
        return game.items[name].id
    return None


def resolve_interactions(game: GameData):
    game.resolved = []
    for ix in game.interactions:
        vid = game.verbs.get(ix.verb)
        if not vid:
            raise ParseError(ix.source_line, f"Unknown verb: {ix.verb}")

        if ix.target_groups == [["*"]]:
            targets = {}
            for key, n in game.nouns.items():
                if n.room == ix.room:
                    targets[n.name] = n.id
            for n, it in game.items.items():
                targets[n] = it.id
            if ix.room in game.rooms:
                targets[f"@{ix.room}"] = game.rooms[ix.room].id
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
        all_ids[n] = it.id
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


# ── Compile Pipeline ───────────────────────────────────────────────────────

def compile_game(global_source: str, room_sources: list[str],
                 max_retries=200) -> GameData:
    """
    Full compilation: parse → allocate IDs (with retry) → resolve → alerts.
    Returns a validated GameData ready for the writer.
    """
    game = parse_global(global_source)
    for src in room_sources:
        parse_room_file(src, game)

    # Try allocations until collision-free
    for attempt in range(max_retries):
        random.seed(attempt)
        _try_allocate(game)
        register_verb_states(game)
        apply_inheritance(game)
        resolve_interactions(game)
        if not check_authored_collisions(game):
            break
        # Reset mutable state for retry
        game.resolved = []
    else:
        print(f"WARNING: No collision-free allocation in {max_retries} attempts.")

    generate_room_alerts(game)
    return game
