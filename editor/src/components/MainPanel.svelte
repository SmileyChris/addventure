<script lang="ts">
  import { store } from '../lib/store.svelte';
  import GameSummary from './GameSummary.svelte';
  import RoomView from './RoomView.svelte';
  import MapView from './MapView.svelte';
  import PuzzleFlow from './PuzzleFlow.svelte';
  import VerbsPage from './VerbsPage.svelte';
  import InventoryPage from './InventoryPage.svelte';
  import NarratorPage from './NarratorPage.svelte';
</script>

<div class="main-panel">
  {#if store.activeView === 'summary'}
    <GameSummary />
  {:else if store.activeView === 'editor'}
    {#if store.activeRoom}
      <RoomView roomName={store.activeRoom} />
    {:else}
      <div class="placeholder">
        <p>Select a room from the sidebar, or add a new one.</p>
      </div>
    {/if}
  {:else if store.activeView === 'map'}
    <MapView />
  {:else if store.activeView === 'puzzleflow'}
    <PuzzleFlow />
  {:else if store.activeView === 'verbs'}
    <VerbsPage />
  {:else if store.activeView === 'inventory'}
    <InventoryPage />
  {:else if store.activeView === 'narrator'}
    <NarratorPage />
  {/if}
</div>

<style>
  .main-panel {
    flex: 1;
    background-color: var(--dark);
    overflow-y: auto;
  }

  .placeholder {
    display: flex;
    align-items: center;
    justify-content: center;
    height: 100%;
    color: var(--text-dim);
    font-style: italic;
    font-size: 0.9rem;
  }
</style>
