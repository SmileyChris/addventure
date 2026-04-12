<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { exportZip, downloadBlob } from '../lib/export';
  import { parseGameFiles } from '../lib/parser';
  import JSZip from 'jszip';
  import SettingsPanel from './SettingsPanel.svelte';

  let showSettings = $state(false);

  let editingName = $state(false);
  let nameInput = $state('');
  let fileInput: HTMLInputElement = $state()!;

  function startEditName() {
    if (!store.project) return;
    nameInput = store.project.name;
    editingName = true;
  }

  function commitNameEdit() {
    if (!store.project) return;
    const trimmed = nameInput.trim();
    if (trimmed) {
      store.mutate((game) => {
        // Name is on the project, not game — use a side-channel
        store.project!.name = trimmed;
      });
    }
    editingName = false;
  }

  function handleNameKey(e: KeyboardEvent) {
    if (e.key === 'Enter') commitNameEdit();
    else if (e.key === 'Escape') editingName = false;
  }

  async function handleExport() {
    if (!store.project || !store.game) return;
    const blob = await exportZip(store.game, store.project.name);
    const filename = store.project.name.toLowerCase().replace(/\s+/g, '-') + '.zip';
    downloadBlob(blob, filename);
  }

  function handleImport() {
    fileInput.click();
  }

  async function onFileSelected(e: Event) {
    const input = e.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) return;

    // Reset so the same file can be re-imported
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
      const text = await file.text();
      files[file.name] = text;
    }

    if (Object.keys(files).length === 0) return;

    const gameData = parseGameFiles(files);
    const projectName =
      gameData.metadata['title'] ??
      file.name.replace(/\.(zip|md)$/, '').replace(/[-_]/g, ' ');

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
</script>

<header class="topbar">
  <div class="left">
    <button class="logo-btn" onclick={() => store.close()} title="Close project">
      <img src="/logo.png" alt="" class="topbar-logo" />
      <span class="topbar-title"><span class="topbar-add">Add</span>venture</span>
    </button>

    {#if store.project}
      <span class="sep">›</span>
      {#if editingName}
        <input
          class="name-input"
          type="text"
          bind:value={nameInput}
          onblur={commitNameEdit}
          onkeydown={handleNameKey}
        />
      {:else}
        <button
          class="project-name"
          ondblclick={startEditName}
          title="Double-click to rename"
        >
          {store.project.name}
        </button>
      {/if}
    {/if}
  </div>

  {#if store.project}
    <div class="right">
      <button
        class="btn-action"
        onclick={() => store.undo()}
        disabled={!store.canUndo}
        title="Undo"
      >
        ↩ Undo
      </button>
      <button
        class="btn-action"
        onclick={() => store.redo()}
        disabled={!store.canRedo}
        title="Redo"
      >
        ↪ Redo
      </button>
      <button class="btn-export" onclick={handleExport} title="Export as .zip">
        ↓ Export .zip
      </button>
      <button class="btn-action" title="Import .zip or .md" onclick={handleImport}>
        Import
      </button>
      <input
        type="file"
        accept=".zip,.md"
        bind:this={fileInput}
        onchange={onFileSelected}
        style="display:none"
      />
      <button
        class="btn-action btn-settings"
        title="Settings"
        onclick={() => (showSettings = true)}
      >
        ⚙
      </button>
    </div>
  {/if}
</header>

{#if showSettings}
  <SettingsPanel onclose={() => (showSettings = false)} />
{/if}

<style>
  .topbar {
    height: 48px;
    background-color: var(--dark);
    border-bottom: 1px solid var(--warm-gray);
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 1rem;
    flex-shrink: 0;
  }

  .left,
  .right {
    display: flex;
    align-items: center;
    gap: 0.5rem;
  }

  .logo-btn {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 0.9rem;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
    background: none;
    border: none;
    padding: 0.3em 0.5em;
    cursor: pointer;
    transition: color 0.15s;
  }

  .logo-btn:hover {
    color: var(--gold-bright);
    background: none;
  }

  .logo-btn:hover .topbar-logo {
    opacity: 0.7;
    transform: scale(1.1);
  }

  .topbar-logo {
    width: 1.5rem;
    height: 1.5rem;
    opacity: 0.5;
    transition: opacity 0.2s, transform 0.2s;
  }

  .topbar-title {
    color: var(--gold);
  }

  .topbar-add {
    display: inline-block;
    transition: transform 0.6s cubic-bezier(0.34, 1.56, 0.64, 1);
  }

  .logo-btn:hover .topbar-add {
    transform: translateY(2px);
  }

  .sep {
    color: var(--warm-gray);
    font-size: 1rem;
  }

  .project-name {
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.95rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    cursor: pointer;
    padding: 0.2em 0.4em;
    border-radius: 2px;
    background: none;
    border: none;
    transition: background-color 0.15s;
  }

  .project-name:hover {
    background-color: var(--mid-dark);
    color: var(--parchment);
  }

  .name-input {
    font-family: var(--font-body);
    font-size: 0.95rem;
    padding: 0.15em 0.4em;
    background-color: var(--mid-dark);
    border: 1px solid var(--gold-dim);
    color: var(--text-light);
    border-radius: 2px;
    min-width: 160px;
  }

  .btn-action {
    font-size: 0.78rem;
    padding: 0.3em 0.7em;
    background-color: var(--dark-warm);
    border-color: var(--warm-gray);
    color: var(--text-mid);
  }

  .btn-action:hover:not(:disabled) {
    background-color: var(--mid-dark);
    color: var(--parchment);
  }

  .btn-action:disabled {
    opacity: 0.35;
    cursor: not-allowed;
  }

  .btn-export {
    font-size: 0.78rem;
    padding: 0.3em 0.7em;
    background-color: var(--gold-dim);
    border-color: var(--gold-dim);
    color: var(--parchment-light);
  }

  .btn-export:hover {
    background-color: var(--gold);
    border-color: var(--gold);
    color: var(--black);
  }

  .btn-settings {
    font-size: 0.9rem;
    padding: 0.2em 0.5em;
  }
</style>
