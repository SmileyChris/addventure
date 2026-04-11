export interface GameProject {
  id: string;
  name: string;
  lastModified: number;
  game: GameData;
}

export interface GameData {
  metadata: Record<string, string>;
  verbs: Record<string, Verb>;
  objects: Record<string, RoomObject>;
  inventory: Record<string, InventoryObject>;
  rooms: Record<string, Room>;
  interactions: Interaction[];
  cues: Cue[];
  actions: Record<string, Action>;
  signalChecks: SignalCheck[];
}

export interface Verb {
  name: string;
}

export interface Room {
  name: string;
  base: string;
  state: string | null;
}

export interface RoomObject {
  name: string;
  base: string;
  state: string | null;
  room: string;
  discovered: boolean;
}

export interface InventoryObject {
  name: string;
}

export interface Arrow {
  subject: string;
  destination: string;
  signalName: string | null;
}

export interface Interaction {
  verb: string;
  targetGroups: string[][];
  narrative: string;
  arrows: Arrow[];
  room: string;
  sealedContent: string | null;
  sealedArrows: Arrow[];
  signalChecks: SignalCheck[];
}

export interface Cue {
  targetRoom: string;
  narrative: string;
  arrows: Arrow[];
  triggerRoom: string;
}

export interface Action {
  name: string;
  room: string;
  narrative: string;
  arrows: Arrow[];
  discovered: boolean;
}

export interface SignalCheck {
  signalNames: string[];
  narrative: string;
  arrows: Arrow[];
}
