"""Reachability validator — walks the game state space to find unreachable interactions."""

from collections import deque
from dataclasses import dataclass

from .compiler import cue_targets_room_name
from .models import Arrow, GameData


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
    initial_objects = set()
    for key, obj in game.objects.items():
        if obj.state is None and not obj.discovered:
            initial_objects.add((obj.room, obj.name))
    # Pre-printed actions tracked with > prefix
    for key, action in game.actions.items():
        if not action.discovered:
            initial_objects.add((action.room, f">{action.name}"))

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
    queue = deque([start])
    triggered = set()  # (verb, tuple(targets), room) of interactions that fired

    while queue:
        state = queue.popleft()  # BFS for more thorough exploration
        if state in visited:
            continue
        visited.add(state)

        # Check cue resolutions on room entry
        resolved = _resolve_cues(state, game)
        if resolved != state:
            queue.append(resolved)
            continue

        # Follow any available actions (direct ledger lookups, no addition)
        for key, action in game.actions.items():
            action_room = action.room
            # Check if action is in the current room (or room state)
            if action_room != state.room:
                current_room_state = None
                for base, sname in state.room_states:
                    if base == state.room or sname == state.room:
                        current_room_state = sname
                        break
                if action_room != current_room_state:
                    continue

            # Actions (pre-printed and discovered) are tracked in room_objects
            # with > prefix
            if (action_room, f">{action.name}") not in state.room_objects:
                continue

            new_state = _apply_arrows(state, action.arrows, action_room, game)
            if new_state != state:
                queue.append(new_state)

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
                objects.discard((room, f">{subj}"))  # Action removal

        elif dest == "player":
            # Move to inventory — use base name for stated room objects
            objects.discard((room, subj))
            base = subj.split("__")[0] if "__" in subj else subj
            inventory.add(base)

        elif dest == "room" and subj.startswith(">"):
            # Action discovery — track as visible action
            objects.add((room, subj))

        elif dest == "room" and not subj.startswith("room__"):
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

        elif ("__" in dest and not dest.startswith('"')) or (
                "__" in subj and subj not in game.verbs
                and dest not in ("trash", "player")
                and not dest.startswith('"')):
            # Entity or room state transform (forward or revert)
            clean_subj = subj.lstrip("@")
            clean_dest = dest.lstrip("@")
            # Resolve "room" shorthand to current room name
            if clean_dest == "room":
                clean_dest = room.split("__")[0]
            if clean_subj.startswith("room__"):
                clean_subj = room.split("__")[0] + clean_subj[4:]
            is_room = dest.startswith("@") or clean_dest in game.rooms
            if is_room:
                # Room state change
                base = clean_dest.split("__")[0]
                room_states = {
                    (b, s) for b, s in room_states if b != base
                }
                room_states.add((base, clean_dest))
            else:
                # Room object state change
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

    resolved_state = state
    changed = False

    for cue in game.cues:
        if cue.id not in resolved_state.cues:
            continue
        # Check if cue resolves in the room the player is currently in
        for base, sname in resolved_state.room_states:
            if base != resolved_state.room and sname != resolved_state.room:
                continue
            if cue_targets_room_name(cue.target_room, sname):
                next_state = _apply_arrows(resolved_state, cue.arrows, resolved_state.room, game)
                cues = set(next_state.cues)
                cues.discard(cue.id)
                resolved_state = GameState(
                    room=next_state.room,
                    inventory=next_state.inventory,
                    verbs=next_state.verbs,
                    room_objects=next_state.room_objects,
                    room_states=next_state.room_states,
                    cues=frozenset(cues),
                )
                changed = True
                break

    if not changed:
        return state

    return resolved_state


def _target_combos(target_groups: list[list[str]]) -> list[list[str]]:
    """Generate all target combinations from target groups."""
    if not target_groups:
        return [[]]
    result = []
    for t in target_groups[0]:
        for rest in _target_combos(target_groups[1:]):
            result.append([t] + rest)
    return result
