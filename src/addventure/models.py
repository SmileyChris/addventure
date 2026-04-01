from dataclasses import dataclass, field


@dataclass
class Verb:
    name: str
    id: int = 0

@dataclass
class Noun:
    name: str
    base: str
    state: str | None
    room: str
    id: int = 0

@dataclass
class Item:
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

@dataclass
class RoomAlert:
    trigger_room: str
    target_room: str
    trigger_label: str
    alert_number: int = 0
    resolution_arrows: list[Arrow] = field(default_factory=list)

@dataclass
class GameData:
    metadata: dict[str, str] = field(default_factory=dict)
    verbs: dict[str, Verb] = field(default_factory=dict)
    nouns: dict[str, Noun] = field(default_factory=dict)
    items: dict[str, Item] = field(default_factory=dict)
    rooms: dict[str, Room] = field(default_factory=dict)
    interactions: list[Interaction] = field(default_factory=list)
    resolved: list[ResolvedInteraction] = field(default_factory=list)
    alerts: list[RoomAlert] = field(default_factory=list)
