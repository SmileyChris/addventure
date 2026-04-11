<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';
  import { displayName } from '../lib/helpers';

  function rooms() {
    if (!store.game) return [];
    return Object.values(store.game.rooms).filter((r) => r.state === null);
  }

  function startRoom() {
    if (!store.game) return null;
    return store.game.metadata.start ?? null;
  }

  function verbs() {
    if (!store.game) return [];
    return Object.values(store.game.verbs);
  }

  function inventory() {
    if (!store.game) return [];
    return Object.values(store.game.inventory);
  }

  function signals() {
    if (!store.game) return [];
    return getSignalEmissions(store.game);
  }

  function cueRooms() {
    if (!store.game) return [];
    const seen = new Set<string>();
    return store.game.cues
      .map((c) => c.targetRoom)
      .filter((r) => {
        if (seen.has(r)) return false;
        seen.add(r);
        return true;
      });
  }

  function isStateVerb(name: string) {
    return name.includes('__');
  }

  function isActiveRoom(name: string) {
    return store.activeView === 'room' && store.activeRoom === name;
  }
</script>

<nav class="sidebar">
  <!-- Game Summary -->
  <button
    class="summary-item"
    class:active={store.activeView === 'summary'}
    onclick={() => store.showSummary()}
  >
    Game Summary
  </button>

  <!-- Rooms -->
  <div class="section">
    <div class="section-header rooms-header">
      <span>Rooms</span>
      <button class="btn-add" title="Add room" onclick={() => {}}>+ Add</button>
    </div>
    <ul class="section-list">
      {#each rooms() as room (room.name)}
        <li>
          <button
            class="list-item"
            class:active={isActiveRoom(room.name)}
            onclick={() => store.showRoom(room.name)}
          >
            <span class="item-label">{displayName(room.name)}</span>
            {#if room.name === startRoom()}
              <span class="badge badge-start">start</span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  </div>

  <!-- Verbs -->
  <div class="section">
    <div class="section-header verbs-header">
      <span>Verbs</span>
      <button class="btn-add" title="Add verb" onclick={() => {}}>+ Add</button>
    </div>
    <ul class="section-list">
      {#each verbs() as verb (verb.name)}
        <li>
          <button class="list-item" onclick={() => {}}>
            <span class="item-label">{displayName(verb.name)}</span>
            {#if isStateVerb(verb.name)}
              <span class="badge badge-state">state</span>
            {/if}
          </button>
        </li>
      {/each}
    </ul>
  </div>

  <!-- Inventory -->
  <div class="section">
    <div class="section-header inventory-header">
      <span>Inventory</span>
      <button class="btn-add" title="Add inventory item" onclick={() => {}}>+ Add</button>
    </div>
    <ul class="section-list">
      {#each inventory() as item (item.name)}
        <li>
          <button class="list-item" onclick={() => {}}>
            <span class="item-label">{displayName(item.name)}</span>
          </button>
        </li>
      {/each}
    </ul>
  </div>

  <!-- Signals & Cues -->
  <div class="section">
    <div class="section-header signals-header">
      <span>Signals &amp; Cues</span>
      <button class="btn-add" title="Add signal" onclick={() => {}}>+ Add</button>
    </div>
    <ul class="section-list">
      {#each signals() as sig}
        <li>
          <div class="list-item static-item">
            <span class="signal-icon">⚡</span>
            <span class="item-label">{displayName(sig)}</span>
          </div>
        </li>
      {/each}
      {#each cueRooms() as room}
        <li>
          <div class="list-item static-item">
            <span class="signal-icon">⟐</span>
            <span class="item-label">{displayName(room)}</span>
          </div>
        </li>
      {/each}
    </ul>
  </div>

  <!-- Footer -->
  <div class="footer">
    <button
      class="map-btn"
      class:active={store.activeView === 'map'}
      onclick={() => store.showMap()}
    >
      🗺 Map View
    </button>
  </div>
</nav>

<style>
  .sidebar {
    width: 220px;
    flex-shrink: 0;
    background-color: var(--dark-warm);
    border-right: 1px solid var(--warm-gray);
    display: flex;
    flex-direction: column;
    overflow-y: auto;
    overflow-x: hidden;
  }

  /* ── Game Summary item ─────────────── */
  .summary-item {
    display: block;
    width: 100%;
    text-align: left;
    background-color: var(--mid-dark);
    border: none;
    border-bottom: 1px solid var(--warm-gray);
    border-radius: 0;
    padding: 0.85em 1em;
    font-family: var(--font-title);
    font-size: 0.85rem;
    font-weight: 700;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--parchment-light);
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
  }

  .summary-item:hover {
    background-color: rgba(201, 168, 76, 0.08);
    color: var(--parchment-light);
  }

  .summary-item.active {
    background-color: rgba(201, 168, 76, 0.1);
    border-left: 3px solid var(--gold);
    color: var(--gold);
  }

  /* ── Section ───────────────────────── */
  .section {
    border-bottom: 1px solid var(--warm-gray);
    padding-bottom: 0.4rem;
  }

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0.6em 0.75em 0.3em;
    font-family: var(--font-title);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.12em;
    text-transform: uppercase;
  }

  .rooms-header { color: var(--gold); }
  .verbs-header { color: var(--parchment); }
  .inventory-header { color: var(--amber); }
  .signals-header { color: var(--parchment-dark); }

  .btn-add {
    font-family: var(--font-title);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.15em 0.5em;
    background-color: var(--gold-dim);
    border: none;
    border-radius: 2px;
    color: var(--parchment);
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
  }

  .btn-add:hover {
    background-color: var(--gold);
    color: var(--black);
  }

  .section-list {
    list-style: none;
    padding: 0 0.3rem;
  }

  /* ── List items ────────────────────── */
  .list-item {
    display: flex;
    align-items: center;
    justify-content: space-between;
    width: 100%;
    text-align: left;
    background: none;
    border: none;
    border-radius: 2px;
    padding: 0.3em 0.6em;
    font-family: var(--font-body);
    font-size: 0.88rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    color: var(--text-light);
    cursor: pointer;
    transition: background-color 0.12s;
    border-left: 3px solid transparent;
  }

  .list-item:hover {
    background-color: rgba(201, 168, 76, 0.06);
    color: var(--parchment);
  }

  .list-item.active {
    background-color: rgba(201, 168, 76, 0.1);
    border-left: 3px solid var(--gold);
    color: var(--parchment-light);
  }

  .static-item {
    cursor: default;
    gap: 0.4rem;
  }

  .static-item:hover {
    background: none;
    color: var(--text-light);
  }

  .item-label {
    flex: 1;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .signal-icon {
    font-size: 0.8rem;
    opacity: 0.7;
  }

  /* ── Badges ────────────────────────── */
  .badge {
    font-family: var(--font-title);
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.1em 0.4em;
    border-radius: 2px;
    flex-shrink: 0;
  }

  .badge-start {
    background-color: var(--gold-dim);
    color: var(--parchment-light);
  }

  .badge-state {
    background-color: var(--amber);
    color: var(--black);
  }

  /* ── Footer ────────────────────────── */
  .footer {
    margin-top: auto;
    padding: 0.75rem;
    border-top: 1px solid var(--warm-gray);
  }

  .map-btn {
    width: 100%;
    text-align: center;
    background-color: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-mid);
    font-size: 0.8rem;
    padding: 0.45em 1em;
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
  }

  .map-btn:hover,
  .map-btn.active {
    background-color: rgba(201, 168, 76, 0.1);
    border-color: var(--gold-dim);
    color: var(--gold);
  }
</style>
