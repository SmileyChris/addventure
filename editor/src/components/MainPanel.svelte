<script lang="ts">
  import { store } from '../lib/store.svelte';
  import GameSummary from './GameSummary.svelte';
  import RoomView from './RoomView.svelte';
  import MapView from './MapView.svelte';
</script>

<div class="main-panel">
  {#if store.activeView === 'summary'}
    <GameSummary />
  {:else if store.activeView === 'room' && store.activeRoom}
    <RoomView roomName={store.activeRoom} />
  {:else if store.activeView === 'map'}
    <MapView />
  {/if}
</div>

<style>
  .main-panel {
    flex: 1;
    background-color: var(--dark);
    overflow-y: auto;
  }

</style>
