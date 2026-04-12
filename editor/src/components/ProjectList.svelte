<script lang="ts">
  import { onMount } from 'svelte';
  import { store } from '../lib/store.svelte';
  import { loadProjectIndex, deleteProject } from '../lib/persistence';
  import { parseGameFiles } from '../lib/parser';
  import { isDevMode, listGameDirs, loadGameFromDisk } from '../lib/filesystem';
  import JSZip from 'jszip';

  let newGameName = $state('');
  let fileInput: HTMLInputElement = $state()!;
  let projects = $state(loadProjectIndex());
  let devMode = $state(false);
  let diskGames = $state<{ name: string; files: string[] }[]>([]);

  function refreshProjects() {
    projects = loadProjectIndex();
  }

  function handleCreate() {
    const name = newGameName.trim();
    if (!name) return;
    store.create(name);
    newGameName = '';
  }

  function handleOpen(id: string) {
    store.open(id);
  }

  function handleDelete(id: string, name: string) {
    if (!confirm(`Delete "${name}"? This cannot be undone.`)) return;
    deleteProject(id);
    refreshProjects();
  }

  function formatDate(ts: number): string {
    return new Date(ts).toLocaleDateString(undefined, {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
    });
  }

  function handleImport() {
    fileInput.click();
  }

  async function onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;
    input.value = '';

    const files: Record<string, string> = {};
    if (file.name.endsWith('.zip')) {
      const zip = await JSZip.loadAsync(file);
      for (const [path, entry] of Object.entries(zip.files)) {
        if (entry.dir) continue;
        const filename = path.split('/').pop();
        if (filename && filename.endsWith('.md')) {
          files[filename] = await entry.async('string');
        }
      }
    } else if (file.name.endsWith('.md')) {
      files[file.name] = await file.text();
    }
    if (Object.keys(files).length === 0) return;

    const gameData = parseGameFiles(files);
    const projectName = gameData.metadata['title'] ?? file.name.replace(/\.(zip|md)$/, '').replace(/[-_]/g, ' ');
    store.create(projectName);
    store.mutate((game) => {
      game.metadata = gameData.metadata;
      game.verbs = gameData.verbs;
      game.objects = gameData.objects;
      game.inventory = gameData.inventory;
      game.rooms = gameData.rooms;
      game.interactions = gameData.interactions;
      game.cues = gameData.cues;
      game.actions = gameData.actions;
      game.signalChecks = gameData.signalChecks;
    });
  }

  const sorted = $derived(
    projects.slice().sort((a, b) => b.lastModified - a.lastModified)
  );

  interface AdventureEntry {
    kind: 'local' | 'disk';
    id: string;
    name: string;
    detail: string;
    icon: string;
  }

  const allAdventures = $derived.by(() => {
    const entries: AdventureEntry[] = [];
    // Disk games first
    for (const game of diskGames) {
      entries.push({
        kind: 'disk',
        id: `disk:${game.name}`,
        name: game.name,
        detail: `${game.files.length} files`,
        icon: '📂',
      });
    }
    // Local projects
    for (const entry of sorted) {
      entries.push({
        kind: 'local',
        id: entry.id,
        name: entry.name,
        detail: formatDate(entry.lastModified),
        icon: '📜',
      });
    }
    return entries;
  });

  onMount(async () => {
    devMode = await isDevMode();
    if (devMode) {
      diskGames = await listGameDirs();
    }
  });

  async function openDiskGame(name: string) {
    const files = await loadGameFromDisk(name);
    if (!files) return;
    const gameData = parseGameFiles(files);
    store.openFromDisk(name, gameData);
  }

  function openAdventure(entry: AdventureEntry) {
    if (entry.kind === 'disk') {
      openDiskGame(entry.name);
    } else {
      handleOpen(entry.id);
    }
  }

  function deleteAdventure(entry: AdventureEntry) {
    if (entry.kind === 'local') {
      handleDelete(entry.id, entry.name);
    }
  }
</script>

<div class="landing">
  <!-- Hero section -->
  <section class="hero">
    <img src="/logo.png" alt="Addventure logo" class="hero-logo" />
    <h1 class="hero-title">
      <span class="hero-title-add"><span class="hero-title-add-inner">Add</span></span>venture
      <span class="hero-suffix">Editor</span>
    </h1>
    <p class="hero-tagline">Design interactive fiction played with pencil, paper, and&nbsp;addition.</p>

    <div class="hero-cta">
      <div class="new-game-row">
        <input
          type="text"
          class="new-game-input"
          placeholder="Name your adventure…"
          bind:value={newGameName}
          onkeydown={(e) => e.key === 'Enter' && handleCreate()}
        />
        <button class="btn btn-primary" onclick={handleCreate} disabled={!newGameName.trim()}>
          New Game
        </button>
      </div>
      <button class="btn btn-ghost" onclick={handleImport}>Import Existing Game</button>
      <input type="file" accept=".zip,.md" bind:this={fileInput} onchange={onFileSelected} style="display:none" />
    </div>
  </section>

  <!-- All adventures (disk + local) -->
  {#if allAdventures.length > 0}
    <section class="projects">
      <div class="projects-inner">
        <span class="section-label">Your Adventures</span>
        <div class="project-grid">
          {#each allAdventures as entry (entry.id)}
            <div class="project-card">
              <button class="project-open" onclick={() => openAdventure(entry)}>
                <span class="project-icon">{entry.icon}</span>
                <div class="project-info">
                  <span class="project-name">{entry.name}</span>
                  <span class="project-date">{entry.detail}</span>
                </div>
              </button>
              {#if entry.kind === 'local'}
                <button
                  class="btn-delete"
                  onclick={() => deleteAdventure(entry)}
                  title="Delete project"
                >
                  ✕
                </button>
              {/if}
            </div>
          {/each}
        </div>
      </div>
    </section>
  {/if}

</div>

<style>
  /* ═══════════════════════════════════════════
     LANDING LAYOUT
     ═══════════════════════════════════════════ */
  .landing {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
    background-color: var(--black);
    overflow-y: auto;
  }

  /* ═══════════════════════════════════════════
     HERO — matches site/index.html hero section
     ═══════════════════════════════════════════ */
  .hero {
    min-height: 60vh;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    text-align: center;
    padding: 2rem;
    position: relative;
    overflow: hidden;
  }

  /* Radial glow behind logo */
  .hero::before {
    content: '';
    position: absolute;
    top: 30%;
    left: 50%;
    transform: translate(-50%, -50%);
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(201,168,76,0.08) 0%, transparent 70%);
    pointer-events: none;
  }

  /* Grid paper pattern */
  .hero::after {
    content: '';
    position: absolute;
    inset: 0;
    background-image:
      linear-gradient(rgba(201,168,76,0.03) 1px, transparent 1px),
      linear-gradient(90deg, rgba(201,168,76,0.03) 1px, transparent 1px);
    background-size: 40px 40px;
    pointer-events: none;
    mask-image: radial-gradient(ellipse 60% 50% at 50% 40%, black, transparent);
  }

  .hero-logo {
    width: 200px;
    height: 200px;
    position: relative;
    z-index: 1;
    animation: logoReveal 3s cubic-bezier(0.2, 0, 0.2, 1) both;
  }

  @keyframes logoReveal {
    from { opacity: 0; transform: scale(0.9); }
    to { opacity: 1; transform: scale(1); }
  }

  .hero-title {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: clamp(2rem, 5vw, 3.2rem);
    color: #f5e6a8;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    line-height: 1.1;
    position: relative;
    z-index: 1;
    animation: fadeIn 1s ease-out 0.3s both;
    cursor: default;
  }

  .hero-title-add {
    display: inline-block;
    animation: slideUp 1s ease-out 0.3s backwards;
  }

  .hero-title-add-inner {
    display: inline-block;
    transition: transform 0.9s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .hero-title:hover .hero-title-add-inner {
    transform: translateY(4px);
  }

  .hero-suffix {
    display: block;
    font-size: 0.35em;
    letter-spacing: 0.3em;
    color: var(--gold-dim);
    margin-top: 0.3rem;
  }

  @keyframes fadeIn {
    from { opacity: 0; }
    to { opacity: 1; }
  }

  @keyframes slideUp {
    from { transform: translateY(20px); }
    to { transform: translateY(0); }
  }

  @keyframes titleReveal {
    from { opacity: 0; transform: translateY(20px); }
    to { opacity: 1; transform: translateY(0); }
  }

  .hero-tagline {
    font-family: var(--font-body);
    font-size: clamp(1rem, 2.5vw, 1.25rem);
    font-style: italic;
    color: var(--text-mid);
    margin-top: 1rem;
    max-width: 480px;
    position: relative;
    z-index: 1;
    animation: titleReveal 1s ease-out 0.5s both;
  }

  .hero-cta {
    margin-top: 2.5rem;
    position: relative;
    z-index: 1;
    animation: titleReveal 1s ease-out 0.7s both;
    width: 100%;
    max-width: 480px;
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.75rem;
  }

  /* ═══════════════════════════════════════════
     NEW GAME INPUT
     ═══════════════════════════════════════════ */
  .new-game-row {
    display: flex;
    gap: 0.5rem;
  }

  .new-game-input {
    flex: 1;
    font-family: var(--font-body);
    font-size: 1rem;
    padding: 0.85rem 1.2rem;
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    color: var(--text-light);
    transition: border-color 0.2s, box-shadow 0.2s;
  }

  .new-game-input::placeholder {
    color: var(--text-dim);
    font-style: italic;
  }

  .new-game-input:focus {
    outline: none;
    border-color: var(--gold);
    box-shadow: 0 0 0 3px rgba(201,168,76,0.15);
  }

  /* ═══════════════════════════════════════════
     BUTTONS — match site style
     ═══════════════════════════════════════════ */
  .btn {
    font-family: var(--font-title);
    font-weight: 800;
    font-size: 0.8rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    padding: 0.85rem 2rem;
    border: none;
    cursor: pointer;
    transition: all 0.2s;
    border-radius: 4px;
    white-space: nowrap;
  }

  .btn-primary {
    background: var(--gold);
    color: var(--black);
  }

  .btn-primary:hover:not(:disabled) {
    background: var(--gold-bright);
    transform: translateY(-2px);
    box-shadow: 0 6px 24px rgba(201,168,76,0.3);
  }

  .btn-primary:disabled {
    opacity: 0.4;
    cursor: not-allowed;
    transform: none;
    box-shadow: none;
  }

  .btn-ghost {
    background: transparent;
    color: var(--parchment);
    border: 1px solid var(--warm-gray);
  }

  .btn-ghost:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    transform: translateY(-2px);
  }

  /* ═══════════════════════════════════════════
     PROJECTS SECTION
     ═══════════════════════════════════════════ */
  .projects {
    background: var(--dark);
    border-top: 1px solid rgba(201,168,76,0.08);
    padding: 3rem 2rem 4rem;
  }

  .projects-inner {
    max-width: 640px;
    margin: 0 auto;
  }

  .section-label {
    font-family: var(--font-mono);
    font-size: 0.65rem;
    letter-spacing: 0.25em;
    text-transform: uppercase;
    color: var(--gold-dim);
    margin-bottom: 1.2rem;
    display: block;
  }

  .project-grid {
    display: flex;
    flex-direction: column;
    gap: 0.5rem;
  }

  .project-card {
    display: flex;
    align-items: stretch;
    gap: 0.4rem;
  }

  .project-open {
    flex: 1;
    display: flex;
    align-items: center;
    gap: 1rem;
    text-align: left;
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    padding: 0.8rem 1.2rem;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 1rem;
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
    color: var(--text-light);
    transition: all 0.2s;
  }

  .project-open:hover {
    background: var(--mid-dark);
    border-color: var(--gold-dim);
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(0,0,0,0.3);
  }

  .project-icon {
    font-size: 1.4rem;
    line-height: 1;
  }

  .project-info {
    display: flex;
    flex-direction: column;
    gap: 0.15rem;
  }

  .project-name {
    font-weight: 600;
    color: var(--parchment-light);
  }

  .project-date {
    font-size: 0.75rem;
    color: var(--text-dim);
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
  }

  .btn-delete {
    background: transparent;
    border: 1px solid var(--warm-gray);
    color: var(--text-dim);
    padding: 0.4em 0.7em;
    font-size: 0.8rem;
    font-family: var(--font-body);
    text-transform: none;
    letter-spacing: 0;
    font-weight: 400;
    border-radius: 4px;
    transition: all 0.15s;
  }

  .btn-delete:hover {
    background: var(--red-ink);
    border-color: var(--red-ink);
    color: var(--parchment-light);
  }


</style>
