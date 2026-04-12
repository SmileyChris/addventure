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

  const aiEnabled = $derived(store.settings.ollamaEnabled && !!store.settings.ollamaModel);
</script>

<div class="tab-bar">
  <div class="tabs-left">
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
  {#if aiEnabled}
    <div class="tabs-right">
      <button
        class="tab tab-ai"
        class:active={store.activeView === 'narrator'}
        onclick={() => store.showNarrator()}
      >
        ✦ Narrator Voice
      </button>
    </div>
  {/if}
</div>

<style>
  .tab-bar {
    display: flex;
    align-items: stretch;
    justify-content: space-between;
    background-color: var(--dark-warm);
    border-bottom: 1px solid var(--warm-gray);
    flex-shrink: 0;
    padding: 0 4px;
  }

  .tabs-left, .tabs-right {
    display: flex;
    align-items: stretch;
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

  .tab-ai {
    color: var(--gold-dim);
    font-size: 0.7rem;
  }

  .tab-ai:hover {
    color: var(--gold);
  }

  .tab-ai.active {
    color: var(--gold);
    border-bottom-color: var(--gold);
  }
</style>
