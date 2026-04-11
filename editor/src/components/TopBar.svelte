<script lang="ts">
  import { store } from '../lib/store.svelte';

  let editingName = $state(false);
  let nameInput = $state('');

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
</script>

<header class="topbar">
  <div class="left">
    <button class="logo-btn" onclick={() => store.close()} title="Close project">
      ▲ Addventure
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
      <button class="btn-export" title="Export as .zip">
        ↓ Export .zip
      </button>
      <button class="btn-action" title="Import .zip">
        Import
      </button>
    </div>
  {/if}
</header>

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
</style>
