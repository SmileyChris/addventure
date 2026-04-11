import { describe, it, expect, vi } from 'vitest';
import JSZip from 'jszip';
import { exportZip, downloadBlob } from '../src/lib/export';
import {
  createGameData,
  createVerb,
  createRoom,
  createInteraction,
} from '../src/lib/factory';

describe('exportZip', () => {
  it('creates a zip blob containing index.md and room files', async () => {
    const game = createGameData();
    game.metadata = { title: 'Test Game', start: 'Hallway' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Hallway'] = createRoom('Hallway');
    game.rooms['Control Room'] = createRoom('Control Room');

    const blob = await exportZip(game, 'Test Game');

    expect(blob).toBeInstanceOf(Blob);
    expect(blob.size).toBeGreaterThan(0);

    // Verify zip contents
    const zip = await JSZip.loadAsync(blob);
    const filenames = Object.keys(zip.files);

    expect(filenames).toContain('test-game/index.md');
    expect(filenames).toContain('test-game/hallway.md');
    expect(filenames).toContain('test-game/control_room.md');
  });

  it('puts files inside a folder named after the project (lowercase, hyphenated)', async () => {
    const game = createGameData();
    game.rooms['Start'] = createRoom('Start');

    const blob = await exportZip(game, 'My Adventure Game');

    const zip = await JSZip.loadAsync(blob);
    const filenames = Object.keys(zip.files);

    // All files should be under 'my-adventure-game/'
    const nonFolder = filenames.filter((f) => !zip.files[f].dir);
    expect(nonFolder.every((f) => f.startsWith('my-adventure-game/'))).toBe(true);
  });

  it('index.md contains frontmatter and verbs', async () => {
    const game = createGameData();
    game.metadata = { title: 'Escape Room', author: 'Tester' };
    game.verbs['LOOK'] = createVerb('LOOK');
    game.verbs['USE'] = createVerb('USE');
    game.rooms['Hall'] = createRoom('Hall');

    const blob = await exportZip(game, 'Escape Room');
    const zip = await JSZip.loadAsync(blob);

    const indexContent = await zip.files['escape-room/index.md'].async('string');
    expect(indexContent).toContain('title: Escape Room');
    expect(indexContent).toContain('author: Tester');
    expect(indexContent).toContain('# Verbs');
    expect(indexContent).toContain('LOOK');
    expect(indexContent).toContain('USE');
  });

  it('room files contain room content', async () => {
    const game = createGameData();
    game.verbs['LOOK'] = createVerb('LOOK');
    game.rooms['Basement'] = createRoom('Basement');

    const roomLook = createInteraction('LOOK', 'Basement');
    roomLook.targetGroups = [];
    roomLook.narrative = 'Damp stone walls.';
    game.interactions.push(roomLook);

    const blob = await exportZip(game, 'My Game');
    const zip = await JSZip.loadAsync(blob);

    const roomContent = await zip.files['my-game/basement.md'].async('string');
    expect(roomContent).toContain('# Basement');
    expect(roomContent).toContain('LOOK: Damp stone walls.');
  });
});

describe('downloadBlob', () => {
  it('creates a link and clicks it to trigger download', () => {
    const mockUrl = 'blob:http://localhost/test-url';
    const mockAnchor = {
      href: '',
      download: '',
      click: vi.fn(),
    };

    const createObjectURL = vi.fn().mockReturnValue(mockUrl);
    const revokeObjectURL = vi.fn();
    const createElement = vi.fn().mockReturnValue(mockAnchor);

    vi.stubGlobal('URL', { createObjectURL, revokeObjectURL });
    Object.defineProperty(global, 'document', {
      value: { createElement },
      writable: true,
    });

    const blob = new Blob(['test'], { type: 'application/zip' });
    downloadBlob(blob, 'game.zip');

    expect(createObjectURL).toHaveBeenCalledWith(blob);
    expect(mockAnchor.href).toBe(mockUrl);
    expect(mockAnchor.download).toBe('game.zip');
    expect(mockAnchor.click).toHaveBeenCalled();
    expect(revokeObjectURL).toHaveBeenCalledWith(mockUrl);
  });
});
