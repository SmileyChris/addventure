from .models import GameData, ResolvedInteraction
from .compiler import get_entity_id, check_authored_collisions, check_potential_collisions


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

    # ── Verb Sheet (BIOS) ──────────────────────────────────────────────────

    def write_verb_sheet(self) -> str:
        lines = ["ADDVENTURE — VERB SHEET", "=" * 40, ""]
        lines.append("Your available actions. Each has an ID number.")
        lines.append("When the game changes a verb, cross out the old ID")
        lines.append("and write the new one.\n")

        for v in self.game.verbs.values():
            if "__" not in v.name:  # only base verbs on the printed sheet
                lines.append(f"  {v.name:<20} [ {v.id} ]")

        lines.append("\n(Blank slots for verb changes:)")
        for _ in range(3):
            lines.append(f"  {'_' * 20} [ ____ ]")

        start_room = self._start_room()
        if start_room:
            lines.append(f"\nYou begin in: {start_room}")
            look_entry = self._find_entry("LOOK", f"@{start_room}", start_room)
            if look_entry:
                lines.append(f"Open the {start_room} room sheet and read Ledger {self.entry_prefix}-{look_entry.entry_number}.")

        return "\n".join(lines)

    # ── Room Sheet ──────────────────────────────────────────────────────────

    def write_room_sheet(self, room_name: str) -> str:
        rm = self.game.rooms.get(room_name)
        if not rm:
            return f"ERROR: Unknown room '{room_name}'"

        is_start = room_name == self._start_room()
        header = f"ROOM: {room_name}"
        if is_start:
            header += "  ★ START"
        lines = [header, f"Room ID: {rm.id}", "=" * 40, ""]

        # Initial nouns (no state = visible on entry)
        lines.append("Objects in this room:")
        initial = [
            n for n in self.game.nouns.values()
            if n.room == room_name and n.state is None
        ]
        # Exclude items that only appear via discovery
        discovered_names = set()
        for ix in self.game.interactions:
            for a in ix.arrows:
                if a.destination == "room" and ix.room == room_name:
                    discovered_names.add(a.subject)
        for cue in self.game.cues:
            if cue.target_room == room_name:
                for a in cue.arrows:
                    if a.destination == "room":
                        discovered_names.add(a.subject)

        for n in initial:
            if n.name not in discovered_names:
                lines.append(f"  {n.name:<24} {n.id}")

        # Discovery slots — use max across all rooms to avoid leaking info
        disc_count = self._max_discovery_slots()
        if disc_count:
            slots_word = "slot" if disc_count == 1 else "slots"
            lines.append(f"\nDiscoveries ({disc_count} {slots_word}):")
            lines.append(f"  If objects are discovered here, record them.")
            for _ in range(disc_count):
                lines.append(f"  {'_' * 24} ____")

        return "\n".join(lines)

    # ── Inventory Sheet ─────────────────────────────────────────────────────

    def write_inventory_sheet(self, max_slots=12) -> str:
        lines = ["ADDVENTURE — INVENTORY & POTENTIALS", "=" * 40, ""]

        lines.append("INVENTORY")
        lines.append("-" * 40)
        lines.append("Items you're carrying. Cross out when used.\n")
        for _ in range(max_slots):
            lines.append(f"  {'_' * 24} ____")

        if self.game.cues:
            lines.append("\n\nCUE CHECKS")
            lines.append("-" * 40)
            lines.append("On room entry, add each cue + Room ID and check the Potentials List.\n")
            lines.append("  ____  ____  ____  ____  ____  ____")

        lines.append("\n\nMASTER POTENTIALS LIST")
        lines.append("-" * 40)
        lines.append("Look up your calculated sum here.\n")

        potentials = sorted(self.game.resolved, key=lambda r: r.sum_id)
        for ri in potentials:
            lines.append(f"  {ri.sum_id:>6}  →  Ledger {self.entry_prefix}-{ri.entry_number}")

        return "\n".join(lines)

    # ── Story Ledger ────────────────────────────────────────────────────────

    def write_story_ledger(self) -> str:
        lines = ["ADDVENTURE — STORY LEDGER", "=" * 40, ""]
        lines.append("Only read an entry when directed to by the Potentials List.\n")

        seen_entries = set()
        sorted_resolved = sorted(self.game.resolved, key=lambda r: r.entry_number)
        for ri in sorted_resolved:
            if ri.entry_number in seen_entries:
                continue
            seen_entries.add(ri.entry_number)
            lines.append(f"── {self.entry_prefix}-{ri.entry_number} ──")
            lines.append(f'"{ri.narrative}"')

            instructions = self._generate_instructions(ri)
            if instructions:
                lines.append("")
                for inst in instructions:
                    lines.append(f"  → {inst}")

            lines.append("")

        return "\n".join(lines)

    def _generate_instructions(self, ri: ResolvedInteraction) -> list[str]:
        """Convert arrows into human-readable player instructions."""
        instructions = []
        dn = _display_name

        for arrow in ri.arrows:
            subj = arrow.subject
            dest = arrow.destination

            # player -> "Room"
            if subj == "player" and dest.startswith('"'):
                room_name = dest[1:-1]
                rm = self.game.rooms.get(room_name)
                if rm:
                    # Find the room's LOOK entry
                    look_entry = self._find_entry("LOOK", f"@{room_name}", room_name)
                    if self.blind:
                        room_ref = f"room sheet {rm.id}"
                    else:
                        room_ref = f"the {room_name} room sheet"
                    if look_entry:
                        instructions.append(
                            f"Switch to {room_ref}. "
                            f"Read Ledger {self.entry_prefix}-{look_entry.entry_number}."
                        )
                    else:
                        instructions.append(f"Switch to {room_ref}.")

            # THING -> trash
            elif dest == "trash":
                sheet, entity_id = self._locate_entity(subj, ri.room)
                instructions.append(
                    f"Cross out {dn(subj)} ({entity_id}) on your {sheet}."
                )

            # THING -> player
            elif dest == "player":
                entity_id = self._get_id(subj, ri.room)
                item = self.game.items.get(subj)
                if item:
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                        f"Write {dn(subj)} ({item.id}) on your Inventory."
                    )
                else:
                    instructions.append(
                        f"Cross out {dn(subj)} ({entity_id}) on your room sheet. "
                        f"Write {dn(subj)} ({entity_id}) on your Inventory."
                    )

            # THING -> room (reveal in current room)
            elif dest == "room":
                entity_id = self._get_id(subj, ri.room)
                instructions.append(
                    f"Write {dn(subj)} ({entity_id}) in a discovery slot "
                    f"on your room sheet."
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

            # THING -> THING__STATE (transform)
            elif "__" in dest or dest.startswith("@"):
                old_id = self._get_id(subj, ri.room)
                new_id = self._get_id(dest, ri.room)
                if old_id and new_id:
                    # Check if it's a verb transform
                    clean_subj = subj.lstrip("@")
                    subj_display = dn(clean_subj)
                    dest_display = dn(dest.lstrip("@"))
                    if clean_subj in self.game.verbs or subj in self.game.verbs:
                        instructions.append(
                            f"Change {subj_display} to {new_id} on your Verb Sheet."
                        )
                    else:
                        instructions.append(
                            f"Change {subj_display} to {new_id} on your room sheet."
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
                        f"Write {obj.id} next to {dn(obj.name)} on your room sheet."
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
            if cue.target_room == room_name:
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

    def _locate_entity(self, name: str, room: str) -> tuple[str, int]:
        """Return (sheet_name, id) for an entity."""
        if name in self.game.items:
            return "Inventory", self.game.items[name].id
        key = f"{room}::{name}"
        if key in self.game.nouns:
            return "room sheet", self.game.nouns[key].id
        for k, n in self.game.nouns.items():
            if n.name == name:
                return "room sheet", n.id
        return "sheet", 0

    def _get_id(self, name: str, room: str) -> int | None:
        """Get the ID for any entity."""
        return get_entity_id(name, self.game, room)


# ── Full Report (for development) ──────────────────────────────────────────

def print_full_report(game: GameData):
    """Print all components for review."""
    writer = GameWriter(game)

    print(writer.write_verb_sheet())
    print("\n" + "═" * 50 + "\n")

    for room_name in game.rooms:
        rm = game.rooms[room_name]
        if rm.state is None:  # only print base room sheets
            print(writer.write_room_sheet(room_name))
            print("\n" + "═" * 50 + "\n")

    print(writer.write_inventory_sheet())
    print("\n" + "═" * 50 + "\n")

    print(writer.write_story_ledger())
    print("\n" + "═" * 50 + "\n")

    # Collision summary
    authored = check_authored_collisions(game)
    potential = check_potential_collisions(game)
    print("COLLISION REPORT")
    print("=" * 40)
    if authored:
        for c in authored:
            print(f"  ⚠  {c}")
    else:
        print("  ✓  No authored collisions.")
    print(f"  ({len(potential)} potential collisions in unused address space)")

    # Stats
    print(f"\nSTATS")
    print(f"  Verbs: {len(game.verbs)}")
    print(f"  Rooms: {len(game.rooms)}")
    print(f"  Nouns: {len(game.nouns)}")
    print(f"  Items: {len(game.items)}")
    print(f"  Resolved: {len(game.resolved)}")
    print(f"  Cues: {len(game.cues)}")
