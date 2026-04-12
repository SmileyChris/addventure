<script lang="ts">
  import { store } from '../lib/store.svelte';

  const tabs = [
    { id: 'summary',    label: 'Summary',      action: () => store.showSummary() },
    { id: 'editor',     label: 'Editor',       action: () => store.showEditor() },
    { id: 'map',        label: 'Room Map',     action: () => store.showMap() },
    { id: 'puzzleflow', label: 'Puzzle Flow',  action: () => store.showPuzzleFlow() },
    { id: 'verbs',      label: 'Verbs',        action: () => store.showVerbs() },
    { id: 'inventory',  label: 'Inventory',    action: () => store.showInventory() },
  ] as const;
</script>

<div class="tab-bar">
  {#each tabs as tab (tab.id)}
    <button
      class="tab"
      class:active={store.activeView === tab.id}
      onclick={tab.action}
    >
      {tab.label}
    </button>
  {/each}
</div>

<style>
  .tab-bar {
    display: flex;
    align-items: stretch;
    background-color: var(--dark-warm);
    border-bottom: 1px solid var(--warm-gray);
    flex-shrink: 0;
    padding: 0 4px;
    gap: 2px;
  }

  .tab {
    font-family: var(--font-title);
    font-size: 0.75rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    background: none;
    border: none;
    border-bottom: 2px solid transparent;
    padding: 10px 16px;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s;
    white-space: nowrap;
  }

  .tab:hover {
    color: var(--parchment);
  }

  .tab.active {
    color: var(--gold);
    border-bottom: 2px solid var(--gold);
  }
</style>
