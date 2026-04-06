from .models import GameData, ResolvedInteraction
from .compiler import get_entity_id


def _display_name(name: str, style: str = "upper_words") -> str:
    """Convert internal names to player-facing display names.
    Strips state suffix (CRATE__OPEN -> CRATE) and converts
    single underscores to spaces.
    """
    base = name.split("__")[0]
    words = base.replace("_", " ")
    if style == "title":
        return words.title()
    return words


class GameWriter:
    """
    Transforms compiled GameData into player-facing printable components.

    All presentation logic lives here:
      - How instructions are phrased
      - When to direct-link vs require calculation
      - Physical sheet layout decisions
    """

    def __init__(self, game: GameData, blind: bool = False, jigsaw: bool = False):
        self.game = game
        self.blind = blind
        self.jigsaw = jigsaw
        self.entry_prefix = game.metadata.get("entry_prefix", "A")
        self.name_style = game.metadata.get("name_style", "upper_words")
        self.warnings: list[str] = []

    def display_name(self, name: str) -> str:
        return _display_name(name, self.name_style)

    def _generate_instructions(self, ri: ResolvedInteraction) -> list[str]:
        """Convert arrows into human-readable player instructions."""
        instructions = []
        dn = self.display_name
        current_room = ri.room

        for arrow in ri.arrows:
            subj = arrow.subject
            dest = arrow.destination

            # -> VERB (verb reveal)
            if subj == "" and dest in self.game.verbs:
                verb = self.game.verbs[dest]
                instructions.append(
                    f"Record {dn(dest)} ({verb.id}) on your Verb Sheet."
                )
                continue

            # player -> "Room"
            if subj == "player" and dest.startswith('"'):
                room_name = dest[1:-1]
                rm = self.game.rooms.get(room_name)
                if rm:
                    if self.blind:
                        room_ref = f"room sheet {rm.id}"
                    else:
                        room_ref = f"the {room_name} room sheet"
                    instructions.append(f"Switch to {room_ref}.")
                    current_room = room_name

            # THING -> trash
            elif dest == "trash":
                if subj in self.game.verbs:
                    verb = self.game.verbs[subj]
                    instructions.append(
                        f"Cross out {dn(subj)} ({verb.id}) on your Verb Sheet."
                    )
                else:
                    # Check if subject is an action in this room
                    action_key = f"{current_room}::{subj}"
                    action = self.game.actions.get(action_key)
                    if action:
                        prefix = self.entry_prefix
                        instructions.append(
                            f"Cross out {dn(subj)} ({prefix}-{action.ledger_id}) on this room sheet."
                        )
                    else:
                        sheet, entity_id = self._locate_entity(
                            subj, current_room, ri.from_inventory)
                        instructions.append(
                            f"Cross out {dn(subj)} ({entity_id}) on your {sheet}."
                        )

            # THING -> player
            elif dest == "player":
                entity_id = self._get_id(subj, current_room)
                # Check for inventory object by exact name, then by base name
                # (FUSE__FLOOR -> player registers inventory object as FUSE)
                base_name = subj.split("__")[0] if "__" in subj else subj
                inv_obj = self.game.inventory.get(subj) or self.game.inventory.get(base_name)
                if inv_obj:
                    # Auto-inventory object picked up via TAKE: player already computed the sum
                    if ri.verb == "TAKE" and subj in self.game.auto_inventory:
                        instructions.append(
                            f"Cross out {dn(subj)} on this room sheet. "
                            f"Write {dn(subj)} and your sum ({inv_obj.id}) on your Inventory."
                        )
                    else:
                        instructions.append(
                            f"Cross out {dn(subj)} on this room sheet. "
                            f"Write {dn(subj)} and {inv_obj.id} on your Inventory."
                        )
                else:
                    instructions.append(
                        f"Cross out {dn(subj)} on this room sheet. "
                        f"Write {dn(subj)} ({entity_id}) on your Inventory."
                    )

            # Action discovery: >ACTION_NAME -> room
            elif dest == "room" and subj.startswith(">"):
                action_name = subj[1:]
                action_key = f"{current_room}::{action_name}"
                action = self.game.actions.get(action_key)
                if action:
                    prefix = self.entry_prefix
                    instructions.append(
                        f"Write {dn(action_name)} ({prefix}-{action.ledger_id}) "
                        f"in a discovery slot on this room sheet."
                    )

            # THING -> room (reveal in current room)
            # But room__STATE -> room is a state revert, not a reveal
            elif dest == "room" and not subj.startswith("room__"):
                entity_id = self._get_id(subj, current_room)
                instructions.append(
                    f"Write {dn(subj)} ({entity_id}) in a discovery slot "
                    f"on this room sheet."
                )

            # ? -> "Room" (cue trigger — deferred cross-room effect)
            elif subj == "?":
                target_room = dest[1:-1]
                cue = next(
                    (c for c in self.game.cues
                     if c.target_room == target_room
                     and c.trigger_room == ri.room),
                    None
                )
                if cue:
                    instructions.append(
                        f"Write {cue.id} in your Cue Checks."
                    )

            # THING -> THING__STATE or THING__STATE -> THING (transform)
            elif "__" in dest or dest.startswith("@") or (
                    "__" in subj and subj not in self.game.verbs):
                # Resolve "room" / "room__STATE" shorthands
                base_room = current_room.split("__")[0]
                resolved_subj = subj.replace("room", f"@{base_room}", 1) if subj.startswith("room") and not subj.startswith("@") else subj
                resolved_dest = f"@{base_room}" if dest == "room" else dest.replace("room", f"@{base_room}", 1) if dest.startswith("room") and not dest.startswith("@") else dest
                old_id = self._get_id(resolved_subj, current_room)
                new_id = self._get_id(resolved_dest, current_room)
                # Check if it's a verb transform
                clean_subj = resolved_subj.lstrip("@")
                subj_display = dn(clean_subj)
                dest_display = dn(resolved_dest.lstrip("@"))
                if clean_subj in self.game.verbs or subj in self.game.verbs:
                    instructions.append(
                        f"Change {subj_display} to {new_id} on your Verb Sheet."
                    )
                else:
                    instructions.append(
                        f"Change {subj_display} to {new_id} on this room sheet."
                    )

            # Verb state restore: USE__RESTRAINED -> USE
            elif subj != dest and not dest.startswith('"'):
                # Could be a verb restore
                if subj in self.game.verbs and dest in self.game.verbs:
                    new_id = self.game.verbs[dest].id
                    dest_display = dn(dest)
                    instructions.append(
                        f"Change {dest_display} to {new_id} on your Verb Sheet."
                    )
                else:
                    self.warnings.append(
                        f"Line {arrow.source_line}: No instruction generated "
                        f"for arrow: {subj} -> {dest}"
                    )

            else:
                # Unhandled arrow type — e.g. cross-room placement (NOUN -> "Room")
                # is a potential future feature
                self.warnings.append(
                    f"Line {arrow.source_line}: No instruction generated "
                    f"for arrow: {subj} -> {dest}"
                )

        # Cue resolution: append "Cross out N from your Cue Checks"
        if ri.verb == "CUE":
            cue = next(
                (c for c in self.game.cues if c.sum_id == ri.sum_id),
                None
            )
            if cue:
                instructions.append(
                    f"Cross out {cue.id} from your Cue Checks."
                )

        # Sealed text: append instruction to open/assemble sealed content
        sealed = next(
            (st for st in self.game.sealed_texts if st.entry_number == ri.entry_number),
            None
        )
        if sealed:
            if self.jigsaw:
                instructions.append(f"Assemble Fragment {sealed.ref}.")
            else:
                instructions.append(f"Turn to Fragment {sealed.ref}.")

        # Blind mode: append room reveal instructions for LOOK + @room
        if self.blind:
            instructions.extend(self._blind_room_instructions(ri))

        return instructions

    def _blind_room_instructions(self, ri: ResolvedInteraction) -> list[str]:
        """In blind mode, LOOK + @room reveals room info to write on the sheet."""
        if ri.verb != "LOOK" or len(ri.targets) != 1 or not ri.targets[0].startswith("@"):
            return []

        room_name = ri.targets[0][1:]
        # Skip room states — they're internal, player is already in the room
        if "__" in room_name:
            return []
        start = self._start_room()
        objects = self._initial_objects(room_name)
        instructions = []

        dn = self.display_name
        if room_name == start:
            # Start room: names already on sheet, just reveal IDs
            if objects:
                for obj in objects:
                    instructions.append(
                        f"Write {obj.id} next to {dn(obj.name)} on this room sheet."
                    )
        else:
            # Non-start: reveal room name and all objects
            instructions.append(f'Write "{room_name}" as the room title.')
            for obj in objects:
                instructions.append(
                    f"Write {dn(obj.name)} ({obj.id}) in an object slot."
                )

        # Reveal pre-printed actions
        prefix = self.entry_prefix
        for action in self._preprinted_actions(room_name):
            instructions.append(
                f"Write {dn(action.name)} ({prefix}-{action.ledger_id}) in an object slot."
            )

        return instructions

    def _initial_objects(self, room_name: str):
        """Return visible room objects in a room (excludes discovered-via-arrow objects)."""
        return [
            obj for obj in self.game.objects.values()
            if obj.room == room_name and obj.state is None and not obj.discovered
        ]

    def _preprinted_actions(self, room_name: str):
        """Return pre-printed actions in a room."""
        return [
            a for a in self.game.actions.values()
            if a.room == room_name and not a.discovered
        ]

    def _start_room(self) -> str | None:
        """Return the starting room name from metadata, or first base room."""
        start = self.game.metadata.get("start")
        if start:
            return start
        for name, rm in self.game.rooms.items():
            if rm.state is None:
                return name
        return None

    def _max_discovery_slots(self) -> int:
        """Max discovery slot count across all base rooms."""
        max_count = 0
        for room_name, rm in self.game.rooms.items():
            if rm.state is not None:
                continue
            count = sum(
                1 for obj in self.game.objects.values()
                if obj.room == room_name and obj.state is None and obj.discovered
            ) + sum(
                1 for a in self.game.actions.values()
                if a.room == room_name and a.discovered
            )
            if count > max_count:
                max_count = count
        return max_count

    def _find_entry(self, verb: str, target: str, room: str) -> ResolvedInteraction | None:
        """Find a resolved interaction by verb + single target + room."""
        for ri in self.game.resolved:
            if ri.verb == verb and ri.targets == [target] and ri.room == room:
                return ri
        return None

    def _locate_entity(
        self, name: str, room: str,
        from_inventory: frozenset[str] = frozenset(),
    ) -> tuple[str, int]:
        """Return (sheet_name, id) for an entity.

        For inventory-duplicate interactions, entities in from_inventory
        are always located on the Inventory. Otherwise, room nouns are
        checked first so that -> trash generates the correct sheet reference.
        """
        if name in from_inventory and name in self.game.inventory:
            return "Inventory", self.game.inventory[name].id
        key = f"{room}::{name}"
        if key in self.game.objects:
            return "room sheet", self.game.objects[key].id
        base_room = room.split("__", 1)[0]
        for obj in self.game.objects.values():
            obj_base_room = obj.room.split("__", 1)[0]
            if obj.name == name and obj_base_room == base_room:
                return "room sheet", obj.id
        if name in self.game.inventory:
            return "Inventory", self.game.inventory[name].id
        return "sheet", 0

    def _get_id(self, name: str, room: str) -> int | None:
        """Get the ID for any entity."""
        return get_entity_id(name, self.game, room)

    def _action_instructions(self, action) -> list[str]:
        """Generate instructions for an action's ledger entry."""
        ri = ResolvedInteraction(
            verb="ACTION", targets=[], sum_id=0,
            narrative=action.narrative, arrows=action.arrows,
            source_line=0, room=action.room, parent_label=action.name,
        )
        return self._generate_instructions(ri)


# ── Build Summary ──────────────────────────────────────────────────────────

def print_build_summary(game: GameData, file=None):
    """Print build stats to the given file (default stderr)."""
    import sys
    file = file or sys.stderr

    def p(n, word):
        return f"{n} {word}" if n != 1 else f"{n} {word.rstrip('s')}"

    action_count = len({a.ledger_id for a in game.actions.values()})
    sealed_count = len(game.sealed_texts)
    parts = [
        p(len(game.verbs), "verbs"),
        p(len(game.rooms), "rooms"),
        p(len(game.objects), "objects"),
        p(len(game.inventory), "inventory"),
        p(len(game.resolved) + action_count, "entries"),
        p(len(game.cues), "cues"),
        p(len(game.actions), "actions"),
        p(sealed_count, "fragments"),
    ]
    print(f"✓ {', '.join(parts)}", file=file)
