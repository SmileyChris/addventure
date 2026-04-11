<script lang="ts">
  import { store } from '../lib/store.svelte';
  import GameSummary from './GameSummary.svelte';
  import RoomView from './RoomView.svelte';
</script>

<div class="main-panel">
  {#if store.activeView === 'summary'}
    <GameSummary />
  {:else if store.activeView === 'room' && store.activeRoom}
    <RoomView roomName={store.activeRoom} />
  {:else if store.activeView === 'map'}
    <div class="placeholder">
      <p>Map view — coming soon</p>
    </div>
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
  }
</style>
