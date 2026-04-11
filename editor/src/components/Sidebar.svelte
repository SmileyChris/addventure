<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getSignalEmissions } from '../lib/helpers';
  import { displayName } from '../lib/helpers';

  // Focus action (avoids a11y autofocus warning)
  function focusEl(el: HTMLElement) {
    el.focus();
  }

  // Inline-add state
  let addingRoom = $state(false);
  let newRoomName = $state('');
  let addingVerb = $state(false);
  let newVerbName = $state('');
  let addingItem = $state(false);
  let newItemName = $state('');

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

  // Room add
  function startAddRoom() {
    addingRoom = true;
    newRoomName = '';
  }

  function commitRoom() {
    const name = newRoomName.trim();
    if (!name) { cancelRoom(); return; }
    if (store.game?.rooms[name]) { cancelRoom(); return; }
    store.addRoom(name);
    store.showRoom(name);
    cancelRoom();
  }

  function cancelRoom() {
    addingRoom = false;
    newRoomName = '';
  }

  // Verb add
  function startAddVerb() {
    addingVerb = true;
    newVerbName = '';
  }

  function normalizeIdentifier(val: string) {
    return val.toUpperCase().replace(/ /g, '_');
  }

  function commitVerb() {
    const name = normalizeIdentifier(newVerbName.trim());
    if (!name) { cancelVerb(); return; }
    if (store.game?.verbs[name]) { cancelVerb(); return; }
    store.addVerb(name);
    cancelVerb();
  }

  function cancelVerb() {
    addingVerb = false;
    newVerbName = '';
  }

  // Inventory add
  function startAddItem() {
    addingItem = true;
    newItemName = '';
  }

  function commitItem() {
    const name = normalizeIdentifier(newItemName.trim());
    if (!name) { cancelItem(); return; }
    if (store.game?.inventory[name]) { cancelItem(); return; }
    store.addInventoryItem(name);
    cancelItem();
  }

  function cancelItem() {
    addingItem = false;
    newItemName = '';
  }

  function onRoomKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); commitRoom(); }
    else if (e.key === 'Escape') cancelRoom();
  }

  function onVerbKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); commitVerb(); }
    else if (e.key === 'Escape') cancelVerb();
  }

  function onItemKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); commitItem(); }
    else if (e.key === 'Escape') cancelItem();
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
      {#if !addingRoom}
        <button class="btn-add" title="Add room" onclick={startAddRoom}>+ Add</button>
      {/if}
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
    {#if addingRoom}
      <div class="inline-add">
        <input
          type="text"
          placeholder="Room name…"
          bind:value={newRoomName}
          onkeydown={onRoomKeydown}
          onblur={cancelRoom}
          use:focusEl
        />
      </div>
    {/if}
  </div>

  <!-- Verbs -->
  <div class="section">
    <div class="section-header verbs-header">
      <span>Verbs</span>
      {#if !addingVerb}
        <button class="btn-add" title="Add verb" onclick={startAddVerb}>+ Add</button>
      {/if}
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
    {#if addingVerb}
      <div class="inline-add">
        <input
          type="text"
          placeholder="VERB_NAME…"
          bind:value={newVerbName}
          oninput={(e) => { newVerbName = normalizeIdentifier((e.target as HTMLInputElement).value); }}
          onkeydown={onVerbKeydown}
          onblur={cancelVerb}
          use:focusEl
        />
      </div>
    {/if}
  </div>

  <!-- Inventory -->
  <div class="section">
    <div class="section-header inventory-header">
      <span>Inventory</span>
      {#if !addingItem}
        <button class="btn-add" title="Add inventory item" onclick={startAddItem}>+ Add</button>
      {/if}
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
    {#if addingItem}
      <div class="inline-add">
        <input
          type="text"
          placeholder="ITEM_NAME…"
          bind:value={newItemName}
          oninput={(e) => { newItemName = normalizeIdentifier((e.target as HTMLInputElement).value); }}
          onkeydown={onItemKeydown}
          onblur={cancelItem}
          use:focusEl
        />
      </div>
    {/if}
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

  /* ── Inline add ────────────────────── */
  .inline-add {
    padding: 3px 12px;
  }

  .inline-add input {
    width: 100%;
    font-size: 0.8rem;
    padding: 3px 6px;
    background-color: var(--mid-dark);
    border: 1px solid var(--gold-dim);
    border-radius: 2px;
    color: var(--text-light);
    font-family: var(--font-body);
    box-sizing: border-box;
  }

  .inline-add input:focus {
    outline: none;
    border-color: var(--gold);
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
