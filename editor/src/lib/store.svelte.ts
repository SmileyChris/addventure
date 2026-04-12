import type { GameProject, GameData } from './types';
import {
  createGameProject,
  createRoom,
  createVerb,
  createInventoryObject,
  createRoomObject,
  objectKey,
} from './factory';
import { autoCreateFromArrows } from './autocreate';
import {
  saveProject,
  loadProject,
  saveUndoStack,
  loadUndoStack,
  loadSettings,
  saveSettings,
  type EditorSettings,
} from './persistence';

let _project = $state<GameProject | null>(null);
let _undoStack = $state<string[]>([]);
let _redoStack = $state<string[]>([]);
let _saveTimer: ReturnType<typeof setTimeout> | null = null;
let _activeView = $state<'summary' | 'room' | 'map'>('summary');
let _activeRoom = $state<string | null>(null);
let _settings = $state<EditorSettings>(loadSettings());

export const store = {
  // Getters
  get project() {
    return _project;
  },
  get game() {
    return _project?.game ?? null;
  },
  get activeView() {
    return _activeView;
  },
  get activeRoom() {
    return _activeRoom;
  },
  get canUndo() {
    return _undoStack.length > 0;
  },
  get canRedo() {
    return _redoStack.length > 0;
  },
  get settings() {
    return _settings;
  },

  updateSettings(settings: EditorSettings) {
    _settings = settings;
    saveSettings(settings);
  },

  // Project lifecycle

  open(id: string): boolean {
    const project = loadProject(id);
    if (!project) return false;
    _project = project;
    _undoStack = loadUndoStack(id);
    _redoStack = [];
    _activeView = 'summary';
    _activeRoom = null;
    return true;
  },

  create(name: string): GameProject {
    const project = createGameProject(name);
    _project = project;
    _undoStack = [];
    _redoStack = [];
    _activeView = 'summary';
    _activeRoom = null;
    saveProject(project);
    return project;
  },

  close(): void {
    if (_saveTimer !== null) {
      clearTimeout(_saveTimer);
      _saveTimer = null;
    }
    if (_project) {
      saveProject(_project);
    }
    _project = null;
    _undoStack = [];
    _redoStack = [];
    _activeView = 'summary';
    _activeRoom = null;
  },

  // Navigation

  showSummary(): void {
    _activeView = 'summary';
    _activeRoom = null;
  },

  showRoom(roomName: string): void {
    _activeView = 'room';
    _activeRoom = roomName;
  },

  showMap(): void {
    _activeView = 'map';
  },

  // Mutation

  mutate(fn: (game: GameData) => void): void {
    if (!_project) return;

    // Push a snapshot of the current state onto the undo stack
    const snapshot = JSON.stringify(_project.game);
    _undoStack = [..._undoStack, snapshot];

    // Clear redo stack on new mutation
    _redoStack = [];

    // Apply the mutation
    fn(_project.game);
    autoCreateFromArrows(_project.game);
    _project.lastModified = Date.now();

    // Persist undo stack and schedule a debounced save
    saveUndoStack(_project.id, _undoStack);
    this._scheduleSave();
  },

  // Undo / redo

  undo(): void {
    if (!_project || _undoStack.length === 0) return;

    const stack = [..._undoStack];
    const snapshot = stack.pop()!;
    _undoStack = stack;

    // Push current state onto redo stack
    _redoStack = [..._redoStack, JSON.stringify(_project.game)];

    // Restore the snapshot
    _project.game = JSON.parse(snapshot) as GameData;
    _project.lastModified = Date.now();

    saveUndoStack(_project.id, _undoStack);
    this._scheduleSave();
  },

  redo(): void {
    if (!_project || _redoStack.length === 0) return;

    const stack = [..._redoStack];
    const snapshot = stack.pop()!;
    _redoStack = stack;

    // Push current state onto undo stack
    _undoStack = [..._undoStack, JSON.stringify(_project.game)];

    // Restore the redo snapshot
    _project.game = JSON.parse(snapshot) as GameData;
    _project.lastModified = Date.now();

    saveUndoStack(_project.id, _undoStack);
    this._scheduleSave();
  },

  // Save

  flushSave(): void {
    if (_saveTimer !== null) {
      clearTimeout(_saveTimer);
      _saveTimer = null;
    }
    if (_project) {
      saveProject(_project);
    }
  },

  // Add helpers

  addRoom(name: string): void {
    this.mutate((game) => {
      game.rooms[name] = createRoom(name);
    });
  },

  addVerb(name: string): void {
    this.mutate((game) => {
      game.verbs[name] = createVerb(name);
    });
  },

  addInventoryItem(name: string): void {
    this.mutate((game) => {
      game.inventory[name] = createInventoryObject(name);
    });
  },

  addObject(roomName: string, objectName: string, discovered = false): void {
    this.mutate((game) => {
      const key = objectKey(roomName, objectName);
      game.objects[key] = createRoomObject(objectName, roomName, discovered);
    });
  },

  _scheduleSave(): void {
    if (_saveTimer !== null) {
      clearTimeout(_saveTimer);
    }
    _saveTimer = setTimeout(() => {
      _saveTimer = null;
      if (_project) {
        saveProject(_project);
      }
    }, 500);
  },
};
