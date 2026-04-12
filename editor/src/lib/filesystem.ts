/** Check if running in dev mode with filesystem access */
export async function isDevMode(): Promise<boolean> {
  try {
    const res = await fetch('/api/games');
    return res.ok;
  } catch {
    return false;
  }
}

/** List available game directories */
export async function listGameDirs(): Promise<{ name: string; files: string[] }[]> {
  const res = await fetch('/api/games');
  if (!res.ok) return [];
  const data = await res.json();
  return data.games ?? [];
}

/** Load a game from disk */
export async function loadGameFromDisk(name: string): Promise<Record<string, string> | null> {
  const res = await fetch(`/api/games/${encodeURIComponent(name)}`);
  if (!res.ok) return null;
  const data = await res.json();
  return data.files ?? null;
}

/** Save a game to disk */
export async function saveGameToDisk(name: string, files: Record<string, string>): Promise<boolean> {
  const res = await fetch(`/api/save/${encodeURIComponent(name)}`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ files }),
  });
  return res.ok;
}
