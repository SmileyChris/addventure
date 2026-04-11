import { describe, it, expect, beforeEach } from 'vitest';
import {
  loadProjectIndex,
  saveProjectIndex,
  loadProject,
  saveProject,
  deleteProject,
  loadUndoStack,
  saveUndoStack,
  type ProjectEntry,
} from '../src/lib/persistence';
import { createGameProject } from '../src/lib/factory';

beforeEach(() => {
  localStorage.clear();
});

describe('loadProjectIndex', () => {
  it('returns empty array when nothing stored', () => {
    expect(loadProjectIndex()).toEqual([]);
  });

  it('returns empty array when localStorage contains corrupted data', () => {
    localStorage.setItem('addventure:projects', 'not-valid-json{{{');
    expect(loadProjectIndex()).toEqual([]);
  });
});

describe('saveProjectIndex / loadProjectIndex', () => {
  it('round-trips an array of entries', () => {
    const entries: ProjectEntry[] = [
      { id: 'abc', name: 'Test Game', lastModified: 1000 },
      { id: 'def', name: 'Another Game', lastModified: 2000 },
    ];
    saveProjectIndex(entries);
    expect(loadProjectIndex()).toEqual(entries);
  });
});

describe('saveProject / loadProject', () => {
  it('round-trips a project', () => {
    const project = createGameProject('My Game');
    saveProject(project);
    const loaded = loadProject(project.id);
    expect(loaded).toEqual(project);
  });

  it('returns null for an unknown id', () => {
    expect(loadProject('nonexistent-id')).toBeNull();
  });

  it('returns null when project data is corrupted', () => {
    localStorage.setItem('addventure:project:bad-id', '{corrupted');
    expect(loadProject('bad-id')).toBeNull();
  });

  it('updates the project index when saving', () => {
    const project = createGameProject('Index Test');
    saveProject(project);

    const index = loadProjectIndex();
    expect(index).toHaveLength(1);
    expect(index[0].id).toBe(project.id);
    expect(index[0].name).toBe('Index Test');
    expect(index[0].lastModified).toBe(project.lastModified);
  });

  it('updates existing index entry on re-save', () => {
    const project = createGameProject('Original Name');
    saveProject(project);

    const updated = { ...project, name: 'Updated Name', lastModified: project.lastModified + 1 };
    saveProject(updated);

    const index = loadProjectIndex();
    expect(index).toHaveLength(1);
    expect(index[0].name).toBe('Updated Name');
  });
});

describe('deleteProject', () => {
  it('removes project data and index entry', () => {
    const project = createGameProject('To Delete');
    saveProject(project);

    deleteProject(project.id);

    expect(loadProject(project.id)).toBeNull();
    expect(loadProjectIndex()).toHaveLength(0);
  });

  it('removes only the target project from the index', () => {
    const p1 = createGameProject('Keep Me');
    const p2 = createGameProject('Delete Me');
    saveProject(p1);
    saveProject(p2);

    deleteProject(p2.id);

    expect(loadProject(p2.id)).toBeNull();
    const index = loadProjectIndex();
    expect(index).toHaveLength(1);
    expect(index[0].id).toBe(p1.id);
  });

  it('removes undo and map data', () => {
    const project = createGameProject('With Extras');
    saveProject(project);
    localStorage.setItem(`addventure:project:${project.id}:undo`, '["snap1"]');
    localStorage.setItem(`addventure:project:${project.id}:map`, '{}');

    deleteProject(project.id);

    expect(localStorage.getItem(`addventure:project:${project.id}:undo`)).toBeNull();
    expect(localStorage.getItem(`addventure:project:${project.id}:map`)).toBeNull();
  });

  it('is a no-op for a nonexistent project', () => {
    expect(() => deleteProject('ghost-id')).not.toThrow();
    expect(loadProjectIndex()).toEqual([]);
  });
});

describe('loadUndoStack / saveUndoStack', () => {
  it('returns empty array when nothing stored', () => {
    expect(loadUndoStack('some-id')).toEqual([]);
  });

  it('round-trips an undo stack', () => {
    const stack = ['snap1', 'snap2', 'snap3'];
    saveUndoStack('my-id', stack);
    expect(loadUndoStack('my-id')).toEqual(stack);
  });

  it('caps the undo stack at 50 entries', () => {
    const stack = Array.from({ length: 60 }, (_, i) => `snap${i}`);
    saveUndoStack('my-id', stack);
    const loaded = loadUndoStack('my-id');
    expect(loaded).toHaveLength(50);
    // Should keep the last 50
    expect(loaded[0]).toBe('snap10');
    expect(loaded[49]).toBe('snap59');
  });

  it('returns empty array when undo data is corrupted', () => {
    localStorage.setItem('addventure:project:bad:undo', 'not-json');
    expect(loadUndoStack('bad')).toEqual([]);
  });
});
