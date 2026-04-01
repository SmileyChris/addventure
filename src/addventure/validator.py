"""Reachability validator — walks the game state space to find unreachable interactions."""

import sys
from dataclasses import dataclass, field

from .models import GameData, Arrow
from .compiler import get_entity_id


@dataclass(frozen=True)
class GameState:
    room: str
    inventory: frozenset[str]
    verbs: frozenset[str]  # active verb names (e.g. USE__RESTRAINED or USE)
    room_objects: frozenset[tuple[str, str]]  # (room, noun_name) visible objects
    room_states: frozenset[tuple[str, str]]  # (base_room, current_state_name)
    cues: frozenset[int]  # active cue IDs


def validate_reachability(game: GameData) -> list[str]:
    """Walk game states from start, report unreachable interactions."""
    warnings = []

    start_room = game.metadata.get("start")
    if not start_room:
        for name, rm in game.rooms.items():
            if rm.state is None:
                start_room = name
                break
    if not start_room:
        return []

    # Initial verb set: for each base verb, use state variant if one exists
    # Exclude auto-verbs (revealed during play via -> VERB arrows)
    initial_verbs = set()
    base_verbs = {v.name for v in game.verbs.values() if "__" not in v.name and v.name not in game.auto_verbs}
    for bv in base_verbs:
        state_variant = None
        for v in game.verbs.values():
            if v.name.startswith(bv + "__"):
                state_variant = v.name
                break
        initial_verbs.add(state_variant if state_variant else bv)

    # Initial visible objects per room (not discovered via arrows/cues)
    discovered_names: dict[str, set[str]] = {}
    for ix in game.interactions:
        for a in ix.arrows:
            if a.destination == "room":
                discovered_names.setdefault(ix.room, set()).add(a.subject)
    for cue in game.cues:
        for a in cue.arrows:
            if a.destination == "room":
                discovered_names.setdefault(cue.target_room, set()).add(a.subject)

    initial_objects = set()
    for key, n in game.nouns.items():
        if n.state is None and n.name not in discovered_names.get(n.room, set()):
            initial_objects.add((n.room, n.name))

    initial_room_states = set()
    for name, rm in game.rooms.items():
        if rm.state is None:
            initial_room_states.add((name, name))

    start = GameState(
        room=start_room,
        inventory=frozenset(),
        verbs=frozenset(initial_verbs),
        room_objects=frozenset(initial_objects),
        room_states=frozenset(initial_room_states),
        cues=frozenset(),
    )

    visited = set()
    queue = [start]
    triggered = set()  # (verb, tuple(targets), room) of interactions that fired

    while queue:
        state = queue.pop(0)  # BFS for more thorough exploration
        if state in visited:
            continue
        visited.add(state)

        # Check cue resolutions on room entry
        resolved = _resolve_cues(state, game)
        if resolved != state:
            queue.append(resolved)
            continue

        # Find all interactions the player can trigger in this state
        for ix in game.interactions:
            # Must be in matching room (or room state)
            ix_room_base = ix.room.split("__")[0] if "__" in ix.room else ix.room
            current_room_state = None
            for base, sname in state.room_states:
                if base == state.room or sname == state.room:
                    current_room_state = sname
                    break

            if ix.room != state.room and ix.room != current_room_state:
                continue

            # Must have the verb
            if ix.verb not in state.verbs:
                continue

            # Must have access to all targets
            if ix.target_groups == [["*"]]:
                # Wildcard — always available if verb matches
                targets_available = True
                target_list = ["*"]
            else:
                targets_available = True
                target_list = []
                for group in ix.target_groups:
                    found = False
                    for t in group:
                        if _can_access(t, state, ix.room):
                            target_list.append(t)
                            found = True
                            break
                    if not found:
                        targets_available = False
                        break

            if not targets_available:
                continue

            key = (ix.verb, tuple(sorted(target_list)), ix.room)
            triggered.add(key)

            # Apply arrows to produce new states
            new_state = _apply_arrows(state, ix.arrows, ix.room, game)
            if new_state != state:
                queue.append(new_state)

    # Check which interactions were never triggered
    for ix in game.interactions:
        if ix.target_groups == [["*"]]:
            continue  # Wildcards are catch-alls, skip
        for group_combo in _target_combos(ix.target_groups):
            key = (ix.verb, tuple(sorted(group_combo)), ix.room)
            if key not in triggered:
                warnings.append(
                    f"Line {ix.source_line}: Unreachable — {ix.label} "
                    f"in {ix.room}"
                )
                break  # One warning per interaction

    return warnings


def _can_access(target: str, state: GameState, room: str) -> bool:
    """Check if player can access a target entity."""
    if target.startswith("@"):
        return True  # Room entity always accessible
    # In inventory?
    if target in state.inventory:
        return True
    # Visible in current room?
    if (room, target) in state.room_objects:
        return True
    # Check state variants
    for rm, name in state.room_objects:
        if rm == room and name == target:
            return True
    return False


def _apply_arrows(state: GameState, arrows: list[Arrow], room: str, game: GameData) -> GameState:
    """Apply interaction arrows to produce a new game state."""
    new_room = state.room
    inventory = set(state.inventory)
    verbs = set(state.verbs)
    objects = set(state.room_objects)
    room_states = set(state.room_states)
    cues = set(state.cues)

    for a in arrows:
        subj = a.subject
        dest = a.destination

        if subj == "" and dest in game.verbs:
            # Verb reveal: -> VERBNAME
            verbs.add(dest)
            continue

        if dest == "trash":
            if subj in game.verbs:
                # Verb removal
                verbs.discard(subj)
            else:
                # Remove from wherever it is
                inventory.discard(subj)
                objects.discard((room, subj))

        elif dest == "player":
            # Move to inventory
            objects.discard((room, subj))
            inventory.add(subj)

        elif dest == "room":
            # Reveal in current room
            objects.add((room, subj))

        elif subj == "player" and dest.startswith('"') and dest.endswith('"'):
            # Movement
            new_room = dest[1:-1]

        elif subj == "?":
            # Cue — find the cue and add its ID
            target_room = dest[1:-1] if dest.startswith('"') else dest
            for cue in game.cues:
                if cue.target_room == target_room and cue.trigger_room == room:
                    cues.add(cue.id)

        elif subj in game.verbs and dest in game.verbs:
            # Verb state change
            verbs.discard(subj)
            verbs.add(dest)

        elif "__" in dest and not dest.startswith('"'):
            # Entity or room state transform
            clean_subj = subj.lstrip("@")
            clean_dest = dest.lstrip("@")
            if dest.startswith("@") or clean_dest in game.rooms:
                # Room state change
                base = clean_dest.split("__")[0]
                room_states = {
                    (b, s) for b, s in room_states if b != base
                }
                room_states.add((base, clean_dest))
            else:
                # Noun state change
                objects.discard((room, subj))
                objects.add((room, dest))

    return GameState(
        room=new_room,
        inventory=frozenset(inventory),
        verbs=frozenset(verbs),
        room_objects=frozenset(objects),
        room_states=frozenset(room_states),
        cues=frozenset(cues),
    )


def _resolve_cues(state: GameState, game: GameData) -> GameState:
    """Check if any active cues resolve in the current room."""
    if not state.cues:
        return state

    objects = set(state.room_objects)
    cues = set(state.cues)
    changed = False

    for cue in game.cues:
        if cue.id not in cues:
            continue
        # Check if cue resolves in the room the player is currently in
        for base, sname in state.room_states:
            if base != state.room and sname != state.room:
                continue
            if cue.target_room in (base, sname):
                # Apply cue arrows
                for a in cue.arrows:
                    if a.destination == "room":
                        objects.add((state.room, a.subject))
                cues.discard(cue.id)
                changed = True
                break

    if not changed:
        return state

    return GameState(
        room=state.room,
        inventory=state.inventory,
        verbs=state.verbs,
        room_objects=frozenset(objects),
        room_states=state.room_states,
        cues=frozenset(cues),
    )


def _target_combos(target_groups: list[list[str]]) -> list[list[str]]:
    """Generate all target combinations from target groups."""
    if not target_groups:
        return [[]]
    result = []
    for t in target_groups[0]:
        for rest in _target_combos(target_groups[1:]):
            result.append([t] + rest)
    return result
