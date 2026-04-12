<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { displayName } from '../lib/helpers';

  function nameStyle(): string {
    return store.game?.metadata.name_style ?? 'upper_words';
  }

  function inventoryItems() {
    if (!store.game) return [];
    return Object.values(store.game.inventory);
  }

  /**
   * Find which room(s) can produce a given inventory item.
   * An item named X is produced when an object with the same base name
   * has a `-> player` arrow in an interaction. The game data stores objects
   * with a `room` field, so we look for objects whose base matches the item name.
   */
  function itemSourceRooms(itemName: string): string[] {
    if (!store.game) return [];
    const rooms = new Set<string>();

    // Check room objects — find objects whose base matches this inventory item
    for (const obj of Object.values(store.game.objects)) {
      if (obj.base === itemName || obj.name === itemName) {
        // Check if any interaction involves this object with a -> player arrow
        for (const interaction of store.game.interactions) {
          if (interaction.room !== obj.room) continue;
          const targetsThis = interaction.targetGroups.some((group) =>
            group.some((t) => t === obj.name || t === obj.base),
          );
          if (!targetsThis) continue;
          const hasPickup = interaction.arrows.some(
            (a) => a.destination === 'player',
          );
          if (hasPickup) {
            rooms.add(obj.room);
          }
        }
      }
    }

    return Array.from(rooms);
  }

  // Delete item
  let pendingDelete = $state<string | null>(null);

  function deleteItem(name: string) {
    if (pendingDelete === name) {
      store.mutate((g) => {
        delete g.inventory[name];
      });
      pendingDelete = null;
    } else {
      pendingDelete = name;
    }
  }

  function cancelDelete() {
    pendingDelete = null;
  }

  // Add item
  let addingItem = $state(false);
  let newItemName = $state('');

  function focusEl(el: HTMLElement) {
    el.focus();
  }

  function normalizeIdentifier(val: string) {
    return val.toUpperCase().replace(/ /g, '_');
  }

  function startAddItem() {
    addingItem = true;
    newItemName = '';
    pendingDelete = null;
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

  function onItemKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter') { e.preventDefault(); commitItem(); }
    else if (e.key === 'Escape') cancelItem();
  }
</script>

<div class="inventory-page">
  <div class="page-header">
    <h2>Inventory</h2>
    <p class="hint">
      Inventory items are objects players can carry. Most are auto-created when a room
      interaction has a <code>→ player</code> arrow, but you can also add them manually here.
    </p>
  </div>

  {#if store.game}
    <div class="item-list">
      {#each inventoryItems() as item (item.name)}
        {@const sourceRooms = itemSourceRooms(item.name)}
        <div class="item-row">
          <div class="item-info">
            <span class="item-name">{item.name}</span>
            <span class="item-display">{displayName(item.name, nameStyle())}</span>
          </div>

          <div class="item-sources">
            {#if sourceRooms.length > 0}
              <span class="source-label">obtained in:</span>
              {#each sourceRooms as room}
                <button
                  class="room-link"
                  onclick={() => store.showRoom(room)}
                  title="Go to {room}"
                >
                  {displayName(room, nameStyle())}
                </button>
              {/each}
            {:else}
              <span class="no-source">manually added</span>
            {/if}
          </div>

          <div class="item-actions">
            {#if pendingDelete === item.name}
              <span class="confirm-text">Delete?</span>
              <button class="btn-confirm-delete" onclick={() => deleteItem(item.name)}>Yes</button>
              <button class="btn-cancel" onclick={cancelDelete}>No</button>
            {:else}
              <button class="btn-delete" onclick={() => deleteItem(item.name)} title="Delete item">✕</button>
            {/if}
          </div>
        </div>
      {/each}

      {#if inventoryItems().length === 0}
        <p class="empty-message">No inventory items yet. They are auto-created from <code>→ player</code> arrows in room interactions, or add one below.</p>
      {/if}
    </div>

    <!-- Add form -->
    {#if addingItem}
      <div class="add-form">
        <input
          type="text"
          placeholder="ITEM_NAME…"
          bind:value={newItemName}
          oninput={(e) => { newItemName = normalizeIdentifier((e.target as HTMLInputElement).value); }}
          onkeydown={onItemKeydown}
          onblur={cancelItem}
          use:focusEl
        />
        <button class="btn-commit" onmousedown={(e) => { e.preventDefault(); commitItem(); }}>Add</button>
        <button class="btn-cancel" onmousedown={(e) => { e.preventDefault(); cancelItem(); }}>Cancel</button>
      </div>
    {:else}
      <button class="btn-add-item" onclick={startAddItem}>+ Add Item</button>
    {/if}
  {:else}
    <p class="hint">No game loaded.</p>
  {/if}
</div>

<style>
  .inventory-page {
    padding: 2rem;
    max-width: 700px;
  }

  .page-header {
    margin-bottom: 1.5rem;
  }

  h2 {
    font-family: var(--font-title);
    font-weight: 900;
    font-size: 1.5rem;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--gold);
    margin-bottom: 0.5rem;
  }

  .hint {
    color: var(--text-mid);
    font-size: 0.85rem;
    line-height: 1.5;
    margin: 0;
  }

  code {
    font-family: var(--font-mono);
    background-color: var(--mid-dark);
    padding: 0.1em 0.3em;
    border-radius: 2px;
    font-size: 0.8em;
    color: var(--parchment);
  }

  /* ── Item list ──────────────────────── */
  .item-list {
    display: flex;
    flex-direction: column;
    gap: 2px;
    margin-bottom: 1rem;
  }

  .item-row {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.5rem 0.75rem;
    background-color: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    transition: border-color 0.15s;
  }

  .item-row:hover {
    border-color: var(--parchment-dark);
  }

  .item-info {
    flex: 1;
    display: flex;
    flex-direction: column;
    gap: 0.1rem;
    min-width: 0;
  }

  .item-name {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--parchment-light);
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
  }

  .item-display {
    font-family: var(--font-body);
    font-size: 0.75rem;
    color: var(--text-dim);
  }

  /* ── Source rooms ────────────────────── */
  .item-sources {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-wrap: wrap;
    flex-shrink: 0;
  }

  .source-label {
    font-family: var(--font-title);
    font-size: 0.6rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
  }

  .room-link {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--amber);
    background: none;
    border: 1px solid rgba(180, 140, 60, 0.3);
    border-radius: 2px;
    padding: 0.1em 0.5em;
    cursor: pointer;
    transition: color 0.15s, border-color 0.15s, background-color 0.15s;
    white-space: nowrap;
  }

  .room-link:hover {
    color: var(--gold);
    border-color: var(--gold-dim);
    background-color: rgba(201, 168, 76, 0.1);
  }

  .no-source {
    font-family: var(--font-body);
    font-size: 0.75rem;
    color: var(--text-dim);
    font-style: italic;
  }

  /* ── Item actions ────────────────────── */
  .item-actions {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    flex-shrink: 0;
  }

  .btn-delete {
    background: none;
    border: none;
    color: var(--text-dim);
    font-size: 0.75rem;
    padding: 0.2em 0.5em;
    border-radius: 2px;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
    opacity: 0;
  }

  .item-row:hover .btn-delete {
    opacity: 1;
  }

  .btn-delete:hover {
    color: var(--red-ink);
    background-color: rgba(180, 60, 60, 0.1);
  }

  .confirm-text {
    font-family: var(--font-title);
    font-size: 0.7rem;
    color: var(--red-ink);
    text-transform: uppercase;
    letter-spacing: 0.06em;
  }

  .btn-confirm-delete {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2em 0.6em;
    background-color: var(--red-ink);
    color: var(--parchment-light);
    border: none;
    border-radius: 2px;
    cursor: pointer;
  }

  .btn-cancel {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.2em 0.6em;
    background: none;
    color: var(--text-dim);
    border: 1px solid var(--warm-gray);
    border-radius: 2px;
    cursor: pointer;
  }

  .btn-cancel:hover {
    color: var(--parchment);
    border-color: var(--parchment-dark);
  }

  /* ── Add form ────────────────────────── */
  .add-form {
    display: flex;
    align-items: center;
    gap: 0.5rem;
    padding: 0.5rem 0.75rem;
    background-color: var(--mid-dark);
    border: 1px solid var(--gold-dim);
    border-radius: 4px;
    margin-bottom: 1rem;
  }

  .add-form input {
    flex: 1;
    font-family: var(--font-mono);
    font-size: 0.85rem;
    padding: 0.3em 0.5em;
    background-color: var(--dark);
    border: 1px solid var(--warm-gray);
    border-radius: 2px;
    color: var(--text-light);
    min-width: 0;
  }

  .add-form input:focus {
    outline: none;
    border-color: var(--gold);
  }

  .btn-commit {
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    padding: 0.3em 0.8em;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 2px;
    cursor: pointer;
    flex-shrink: 0;
  }

  .btn-commit:hover {
    background-color: var(--gold);
    color: var(--black);
  }

  .btn-add-item {
    font-family: var(--font-title);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.4em 1em;
    background-color: var(--gold-dim);
    color: var(--parchment-light);
    border: none;
    border-radius: 3px;
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
    margin-bottom: 1rem;
  }

  .btn-add-item:hover {
    background-color: var(--gold);
    color: var(--black);
  }

  .empty-message {
    color: var(--text-dim);
    font-size: 0.85rem;
    padding: 0.5rem 0;
    line-height: 1.5;
  }
</style>
