import type { GameProject } from './types';

const PROJECTS_KEY = 'addventure:projects';
const SETTINGS_KEY = 'addventure:settings';

export interface EditorSettings {
  ollamaEnabled: boolean;
  ollamaModel: string;
}

const DEFAULT_SETTINGS: EditorSettings = {
  ollamaEnabled: false,
  ollamaModel: '',
};

export function loadSettings(): EditorSettings {
  const raw = localStorage.getItem(SETTINGS_KEY);
  if (!raw) return { ...DEFAULT_SETTINGS };
  try {
    return { ...DEFAULT_SETTINGS, ...JSON.parse(raw) };
  } catch {
    return { ...DEFAULT_SETTINGS };
  }
}

export function saveSettings(settings: EditorSettings): void {
  localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
}
const projectKey = (id: string) => `addventure:project:${id}`;
const undoKey = (id: string) => `addventure:project:${id}:undo`;
const mapKey = (id: string) => `addventure:project:${id}:map`;

export interface ProjectEntry {
  id: string;
  name: string;
  lastModified: number;
}

export function loadProjectIndex(): ProjectEntry[] {
  try {
    const raw = localStorage.getItem(PROJECTS_KEY);
    if (!raw) return [];
    return JSON.parse(raw) as ProjectEntry[];
  } catch {
    return [];
  }
}

export function saveProjectIndex(entries: ProjectEntry[]): void {
  localStorage.setItem(PROJECTS_KEY, JSON.stringify(entries));
}

export function loadProject(id: string): GameProject | null {
  try {
    const raw = localStorage.getItem(projectKey(id));
    if (!raw) return null;
    return JSON.parse(raw) as GameProject;
  } catch {
    return null;
  }
}

export function saveProject(project: GameProject): void {
  localStorage.setItem(projectKey(project.id), JSON.stringify(project));

  // Also update the project index
  const entries = loadProjectIndex();
  const idx = entries.findIndex((e) => e.id === project.id);
  const entry: ProjectEntry = {
    id: project.id,
    name: project.name,
    lastModified: project.lastModified,
  };
  if (idx === -1) {
    entries.push(entry);
  } else {
    entries[idx] = entry;
  }
  saveProjectIndex(entries);
}

export function deleteProject(id: string): void {
  localStorage.removeItem(projectKey(id));
  localStorage.removeItem(undoKey(id));
  localStorage.removeItem(mapKey(id));

  const entries = loadProjectIndex().filter((e) => e.id !== id);
  saveProjectIndex(entries);
}

export function loadMapPositions(
  id: string,
): Record<string, { x: number; y: number }> {
  try {
    const raw = localStorage.getItem(mapKey(id));
    if (!raw) return {};
    return JSON.parse(raw) as Record<string, { x: number; y: number }>;
  } catch {
    return {};
  }
}

export function saveMapPositions(
  id: string,
  positions: Record<string, { x: number; y: number }>,
): void {
  localStorage.setItem(mapKey(id), JSON.stringify(positions));
}

export function loadUndoStack(id: string): string[] {
  try {
    const raw = localStorage.getItem(undoKey(id));
    if (!raw) return [];
    return JSON.parse(raw) as string[];
  } catch {
    return [];
  }
}

export function saveUndoStack(id: string, stack: string[]): void {
  const capped = stack.slice(-50);
  localStorage.setItem(undoKey(id), JSON.stringify(capped));
}
