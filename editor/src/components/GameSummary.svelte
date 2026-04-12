<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';
  import { buildGameContext } from '../lib/ollama';
  import { exportZip, downloadBlob } from '../lib/export';
  import { parseGameFiles } from '../lib/parser';
  import { deleteProject } from '../lib/persistence';
  import JSZip from 'jszip';
  import GenerateDialog from './GenerateDialog.svelte';

  let showDescriptionGen = $state(false);
  let fileInput: HTMLInputElement = $state()!;

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
    store.mutate((game) => {
      Object.assign(game, gameData);
    });
  }

  function handleDelete() {
    if (!store.project) return;
    if (!confirm(`Delete "${store.project.name}"? This cannot be undone.`)) return;
    const id = store.project.id;
    store.close();
    deleteProject(id);
  }

  function signals() {
    if (!store.game) return [];
    return getSignalEmissions(store.game);
  }

  function baseRooms() {
    if (!store.game) return [];
    return Object.values(store.game.rooms).filter((r) => r.state === null);
  }

  function descriptionContext(): string {
    if (!store.game) return '';
    const ctx = buildGameContext(store.game, store.settings.narratorVoice || undefined);
    const rooms = baseRooms().map(r => r.name).join(', ');
    return `You are writing the opening narrative for a paper-based text adventure game.

${ctx}

${rooms ? `The game has these rooms: ${rooms}` : ''}

Write an atmospheric opening description (2-4 paragraphs) that sets the scene and hooks the player. This text is the first thing players read before they begin exploring.

Rules:
- Write only the narrative text, no labels or formatting
- Set the tone and atmosphere for the entire game
- Be evocative — this is printed on paper and should feel literary
- End with something that propels the player into action`;
  }
</script>

<div class="game-summary">
  {#if store.game}
    <form class="summary-layout" onsubmit={(e) => e.preventDefault()}>
      <!-- Main column: title + description -->
      <div class="main-col">
        <div class="field">
          <label for="meta-title">Title</label>
          <input
            id="meta-title"
            type="text"
            class="title-input"
            value={store.game.metadata.title ?? ''}
            oninput={(e) => {
              const val = (e.target as HTMLInputElement).value;
              store.mutate((g) => {
                g.metadata.title = val;
              });
              if (store.project && val.trim()) {
                store.project.name = val.trim();
              }
            }}
            placeholder="Game title..."
          />
        </div>

        <div class="field">
          <div class="label-row">
            <label for="meta-description">Description</label>
            {#if store.settings.ollamaEnabled && store.settings.ollamaModel}
              <button class="ai-btn" onclick={() => showDescriptionGen = true} title="Generate with AI">✦ AI</button>
            {/if}
          </div>
          <textarea
            id="meta-description"
            rows="16"
            value={store.game.metadata.description ?? ''}
            oninput={(e) =>
              store.mutate((g) => {
                g.metadata.description = (e.target as HTMLTextAreaElement).value;
              })}
            placeholder="Opening narrative that sets the scene for the player..."
          ></textarea>
        </div>

        <!-- Signal Checks -->
        {#if signals().length > 0}
          <div class="field signals-section">
            <span class="label-text">Signal Checks</span>
            <p class="hint">
              {signals().length} signal{signals().length === 1 ? '' : 's'} — edit in room interactions.
            </p>
            <ul class="signal-list">
              {#each signals() as sig}
                <li><span class="signal-chip">{sig}</span></li>
              {/each}
            </ul>
          </div>
        {/if}
      </div>

      <!-- Right column: meta fields -->
      <div class="meta-col">
        <div class="field">
          <label for="meta-author">Author</label>
          <input
            id="meta-author"
            type="text"
            value={store.game.metadata.author ?? ''}
            oninput={(e) =>
              store.mutate((g) => {
                g.metadata.author = (e.target as HTMLInputElement).value;
              })}
            placeholder="Author name..."
          />
        </div>

        <div class="field">
          <label for="meta-start">Start Room</label>
          <select
            id="meta-start"
            value={store.game.metadata.start ?? ''}
            onchange={(e) =>
              store.mutate((g) => {
                g.metadata.start = (e.target as HTMLSelectElement).value;
              })}
          >
            <option value="">— none —</option>
            {#each baseRooms() as room (room.name)}
              <option value={room.name}>{room.name}</option>
            {/each}
          </select>
        </div>

        <div class="field">
          <label for="meta-style">Name Style</label>
          <select
            id="meta-style"
            value={store.game.metadata.name_style ?? 'upper_words'}
            onchange={(e) =>
              store.mutate((g) => {
                g.metadata.name_style = (e.target as HTMLSelectElement).value;
              })}
          >
            <option value="upper_words">UPPER WORDS</option>
            <option value="title">Title Case</option>
          </select>
        </div>

        <div class="field">
          <label for="meta-prefix">Ledger Prefix</label>
          <input
            id="meta-prefix"
            type="text"
            maxlength="1"
            value={store.game.metadata.ledger_prefix ?? ''}
            oninput={(e) =>
              store.mutate((g) => {
                g.metadata.ledger_prefix = (
                  e.target as HTMLInputElement
                ).value.toUpperCase();
              })}
            placeholder="A"
          />
        </div>

        <!-- Project actions -->
        <div class="project-actions">
          <button class="btn-action-export" onclick={handleExport}>↓ Export .zip</button>
          <button class="btn-action-import" onclick={handleImport}>Import</button>
          <input type="file" accept=".zip,.md" bind:this={fileInput} onchange={onFileSelected} style="display:none" />
          <button class="btn-action-delete" onclick={handleDelete}>Delete Project</button>
        </div>
      </div>
    </form>

    {#if showDescriptionGen}
      <GenerateDialog
        context={descriptionContext()}
        label="Opening Description"
        ongenerated={(text) => store.mutate((g) => { g.metadata.description = text; })}
        onclose={() => showDescriptionGen = false}
      />
    {/if}
  {:else}
    <p class="hint">No game loaded.</p>
  {/if}
</div>

<style>
  .game-summary {
    padding: 2rem;
  }

  .summary-layout {
    display: flex;
    gap: 2rem;
    max-width: 900px;
  }

  .main-col {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    min-width: 0;
  }

  .meta-col {
    width: 200px;
    flex-shrink: 0;
    display: flex;
    flex-direction: column;
    gap: 1rem;
    padding-top: 0.2rem;
  }

  .field {
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }

  .title-input {
    font-size: 1.2rem;
    font-weight: 600;
    padding: 0.5em 0.6em;
  }

  label,
  .label-text {
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-mid);
  }

  input,
  select,
  textarea {
    background-color: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.9rem;
    padding: 0.4em 0.6em;
    transition: border-color 0.15s;
  }

  input:focus,
  select:focus,
  textarea:focus {
    outline: none;
    border-color: var(--gold-dim);
  }

  textarea {
    resize: vertical;
    width: 100%;
    box-sizing: border-box;
  }

  select {
    cursor: pointer;
    width: 100%;
  }

  .meta-col input {
    width: 100%;
  }

  .signals-section {
    border-top: 1px solid var(--warm-gray);
    padding-top: 1rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.8rem;
    margin: 0.3rem 0;
    line-height: 1.4;
  }

  .signal-list {
    list-style: none;
    padding: 0;
    display: flex;
    flex-wrap: wrap;
    gap: 0.4rem;
    margin-top: 0.4rem;
  }

  .signal-chip {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    padding: 0.2em 0.6em;
    border-radius: 2px;
  }

  .label-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  /* .ai-btn defined globally in theme.css */

  .project-actions {
    display: flex;
    flex-direction: column;
    gap: 0.4rem;
    margin-top: 1rem;
    padding-top: 1rem;
    border-top: 1px solid var(--warm-gray);
  }

  .btn-action-export,
  .btn-action-import,
  .btn-action-delete {
    font-size: 0.75rem;
    padding: 0.4em 0.8em;
    text-align: left;
    border-radius: 3px;
  }

  .btn-action-export {
    background: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
  }

  .btn-action-export:hover {
    background: var(--gold);
    color: var(--black);
  }

  .btn-action-import {
    background: none;
    color: var(--text-mid);
    border: 1px solid var(--warm-gray);
  }

  .btn-action-import:hover {
    color: var(--parchment);
    border-color: var(--parchment-dark);
  }

  .btn-action-delete {
    background: none;
    color: var(--text-dim);
    border: 1px solid var(--warm-gray);
  }

  .btn-action-delete:hover {
    color: var(--red-ink);
    border-color: var(--red-ink);
  }
</style>
