import JSZip from 'jszip';
import type { GameData } from './types';
import { serializeGame } from './serializer';

export async function exportZip(game: GameData, projectName: string): Promise<Blob> {
  const files = serializeGame(game);
  const zip = new JSZip();
  const folderName = projectName.toLowerCase().replace(/\s+/g, '-');
  const folder = zip.folder(folderName)!;
  for (const [filename, content] of Object.entries(files)) {
    folder.file(filename, content);
  }
  return zip.generateAsync({ type: 'blob' });
}

export function downloadBlob(blob: Blob, filename: string): void {
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
