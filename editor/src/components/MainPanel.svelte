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
        <p>Select a room from the sidebar, or</p>
        <button class="placeholder-add" onclick={() => {
          const name = prompt('Room name:');
          if (name?.trim()) {
            store.addRoom(name.trim());
            store.showRoom(name.trim());
          }
        }}>+ Add Room</button>
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
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 1rem;
    height: 100%;
    color: var(--text-dim);
    font-style: italic;
    font-size: 0.9rem;
  }

  .placeholder-add {
    font-size: 0.85rem;
    padding: 0.5em 1.5em;
    background: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 4px;
    font-style: normal;
  }

  .placeholder-add:hover {
    background: var(--gold);
    color: var(--black);
  }
</style>
