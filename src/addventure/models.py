from dataclasses import dataclass, field


@dataclass
class Verb:
    name: str
    id: int = 0

@dataclass
class RoomObject:
    name: str
    base: str
    state: str | None
    room: str
    id: int = 0
    discovered: bool = False

@dataclass
class InventoryObject:
    name: str
    id: int = 0

@dataclass
class Room:
    name: str
    base: str
    state: str | None
    id: int = 0

@dataclass
class Arrow:
    subject: str
    destination: str
    source_line: int = 0
    signal_name: str | None = None  # Set when subject is NAME and destination is `signal`
    def __repr__(self):
        return f"{self.subject} -> {self.destination}"

@dataclass
class Interaction:
    verb: str
    target_groups: list[list[str]]
    narrative: str
    arrows: list[Arrow] = field(default_factory=list)
    source_line: int = 0
    room: str = ""
    sealed_content: str | None = None
    signal_checks: list['SignalCheck'] = field(default_factory=list)

    @property
    def label(self):
        parts = [self.verb]
        for g in self.target_groups:
            parts.append(" | ".join(g))
        return " + ".join(parts)

@dataclass
class ResolvedInteraction:
    verb: str
    targets: list[str]
    sum_id: int
    narrative: str
    arrows: list[Arrow]
    source_line: int
    room: str
    parent_label: str
    entry_number: int = 0
    from_inventory: frozenset[str] = frozenset()

@dataclass
class Cue:
    target_room: str
    narrative: str
    arrows: list[Arrow]
    source_line: int
    trigger_room: str
    id: int = 0
    sum_id: int = 0
    entry_number: int = 0

@dataclass
class Action:
    name: str
    room: str
    narrative: str
    arrows: list[Arrow]
    discovered: bool
    ledger_id: int = 0

@dataclass
class SealedText:
    ref: str           # Opaque reference code, e.g. "K-7"
    content: str       # The sealed text content (may contain markup/image refs)
    images: list[str]  # Image filenames referenced in the content
    source_line: int
    room: str
    entry_number: int = 0  # The ledger entry that triggers this

@dataclass
class SignalCheck:
    signal_names: list[str]  # Empty list = otherwise
    narrative: str
    arrows: list[Arrow] = field(default_factory=list)
    entry_number: int = 0

@dataclass
class GameData:
    metadata: dict[str, str] = field(default_factory=dict)
    verbs: dict[str, Verb] = field(default_factory=dict)
    objects: dict[str, RoomObject] = field(default_factory=dict)
    inventory: dict[str, InventoryObject] = field(default_factory=dict)
    rooms: dict[str, Room] = field(default_factory=dict)
    interactions: list[Interaction] = field(default_factory=list)
    resolved: list[ResolvedInteraction] = field(default_factory=list)
    cues: list[Cue] = field(default_factory=list)
    auto_inventory: set[str] = field(default_factory=set)
    auto_verbs: set[str] = field(default_factory=set)
    suppressed_interactions: list[Interaction] = field(default_factory=list)
    actions: dict[str, Action] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    sealed_texts: list[SealedText] = field(default_factory=list)
    signal_checks: list[SignalCheck] = field(default_factory=list)  # Index-level
    signal_emissions: set[str] = field(default_factory=set)
