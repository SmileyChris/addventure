from .models import GameData, ResolvedInteraction
from .compiler import cue_targets_room_name, get_entity_id


def _display_name(name: str) -> str:
    """Convert internal names to player-facing display names.
    Strips state suffix (CRATE__OPEN -> CRATE) and converts
    single underscores to spaces (WALL_PANEL -> WALL PANEL).
    """
    base = name.split("__")[0]
    return base.replace("_", " ")


class GameWriter:
    """
    Transforms compiled GameData into player-facing printable components.

    All presentation logic lives here:
      - How instructions are phrased
      - When to direct-link vs require calculation
      - Physical sheet layout decisions
    """

    def __init__(self, game: GameData, blind: bool = False):
        self.game = game
        self.blind = blind
        self.entry_prefix = game.metadata.get("entry_prefix", "A")
        self.warnings: list[str] = []

    def _generate_instructions(self, ri: ResolvedInteraction) -> list[str]:
        """Convert arrows into human-readable player instructions."""
        instructions = []
        dn = _display_name

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

            # THING -> trash
            elif dest == "trash":
                if subj in self.game.verbs:
                    verb = self.game.verbs[subj]
                    instructions.append(
                        f"Cross out {dn(subj)} ({verb.id}) on your Verb Sheet."
                    )
                else:
                    sheet, entity_id = self._locate_entity(
                        subj, ri.room, ri.from_inventory)
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your {sheet}."
                    )

            # THING -> player
            elif dest == "player":
                entity_id = self._get_id(subj, ri.room)
                item = self.game.items.get(subj)
                if item:
                    # Auto-item picked up via TAKE: player already computed the sum
                    if ri.verb == "TAKE" and subj in self.game.auto_items:
                        instructions.append(
                            f"Cross out {dn(subj)} on this room sheet. "
                            f"Write {dn(subj)} and your sum ({item.id}) on your Inventory."
                        )
                    else:
                        instructions.append(
                            f"Cross out {dn(subj)} on this room sheet. "
                            f"Write {dn(subj)} and {item.id} on your Inventory."
                        )
                else:
                    instructions.append(
                        f"Cross out {dn(subj)} on this room sheet. "
                        f"Write {dn(subj)} ({entity_id}) on your Inventory."
                    )

            # THING -> room (reveal in current room)
            # But THING__STATE -> room is a state revert, not a reveal
            elif dest == "room" and "__" not in subj:
                entity_id = self._get_id(subj, ri.room)
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
                base_room = ri.room.split("__")[0]
                resolved_subj = subj.replace("room", f"@{base_room}", 1) if subj.startswith("room") and not subj.startswith("@") else subj
                resolved_dest = f"@{base_room}" if dest == "room" else dest.replace("room", f"@{base_room}", 1) if dest.startswith("room") and not dest.startswith("@") else dest
                old_id = self._get_id(resolved_subj, ri.room)
                new_id = self._get_id(resolved_dest, ri.room)
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

        dn = _display_name
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

        return instructions

    def _initial_objects(self, room_name: str):
        """Return visible objects in a room (excludes discovered-via-arrow objects)."""
        discovered_names = set()
        for ix in self.game.interactions:
            for a in ix.arrows:
                if a.destination == "room" and ix.room == room_name:
                    discovered_names.add(a.subject)
        for cue in self.game.cues:
            if cue_targets_room_name(cue.target_room, room_name):
                for a in cue.arrows:
                    if a.destination == "room":
                        discovered_names.add(a.subject)
        return [
            n for n in self.game.nouns.values()
            if n.room == room_name and n.state is None and n.name not in discovered_names
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
                1 for ix in self.game.interactions if ix.room == room_name
                for a in ix.arrows if a.destination == "room"
            ) + sum(
                1 for cue in self.game.cues if cue.target_room == room_name
                for a in cue.arrows if a.destination == "room"
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
        if name in from_inventory and name in self.game.items:
            return "Inventory", self.game.items[name].id
        key = f"{room}::{name}"
        if key in self.game.nouns:
            return "room sheet", self.game.nouns[key].id
        base_room = room.split("__", 1)[0]
        for n in self.game.nouns.values():
            noun_base_room = n.room.split("__", 1)[0]
            if n.name == name and noun_base_room == base_room:
                return "room sheet", n.id
        if name in self.game.items:
            return "Inventory", self.game.items[name].id
        return "sheet", 0

    def _get_id(self, name: str, room: str) -> int | None:
        """Get the ID for any entity."""
        return get_entity_id(name, self.game, room)


# ── Build Summary ──────────────────────────────────────────────────────────

def print_build_summary(game: GameData, file=None):
    """Print build stats to the given file (default stderr)."""
    import sys
    file = file or sys.stderr

    def p(n, word):
        return f"{n} {word}" if n != 1 else f"{n} {word.rstrip('s')}"

    parts = [
        p(len(game.verbs), "verbs"),
        p(len(game.rooms), "rooms"),
        p(len(game.nouns), "nouns"),
        p(len(game.items), "items"),
        p(len(game.resolved), "entries"),
        p(len(game.cues), "cues"),
    ]
    print(f"✓ {', '.join(parts)}", file=file)
