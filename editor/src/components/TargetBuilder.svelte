<script lang="ts">
  import { store } from '../lib/store.svelte';

  interface Props {
    targetGroups: string[][];
    onchange: (groups: string[][]) => void;
    roomName: string;
  }

  let { targetGroups, onchange, roomName }: Props = $props();

  /** All autocomplete options: room objects + inventory items + wildcard */
  const datalistOptions = $derived.by(() => {
    const opts = new Set<string>();
    opts.add('*');
    if (!store.game) return Array.from(opts);
    for (const obj of Object.values(store.game.objects)) {
      if (obj.room === roomName) {
        opts.add(obj.name);
      }
    }
    for (const name of Object.keys(store.game.inventory)) {
      opts.add(name);
    }
    return Array.from(opts);
  });

  const listId = $derived(`targets-datalist-${roomName.replace(/\s+/g, '-')}`);

  function groupToInput(group: string[]): string {
    return group.join(' | ');
  }

  function inputToGroup(raw: string): string[] {
    return raw
      .split('|')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
  }

  function handleGroupInput(index: number, e: Event) {
    const raw = (e.target as HTMLInputElement).value;
    const updated = targetGroups.map((g, i) => (i === index ? inputToGroup(raw) : g));
    onchange(updated);
  }

  function addGroup() {
    onchange([...targetGroups, []]);
  }

  function removeGroup(index: number) {
    onchange(targetGroups.filter((_, i) => i !== index));
  }
</script>

<datalist id={listId}>
  {#each datalistOptions as opt (opt)}
    <option value={opt}></option>
  {/each}
</datalist>

<div class="target-builder">
  {#each targetGroups as group, i (i)}
    {#if i > 0}
      <span class="plus-sep">+</span>
    {/if}
    <div class="group-row">
      <input
        type="text"
        class="group-input"
        value={groupToInput(group)}
        placeholder="TARGET | ALT"
        list={listId}
        oninput={(e) => handleGroupInput(i, e)}
      />
      {#if targetGroups.length > 1}
        <button
          class="remove-btn"
          title="Remove group"
          onclick={() => removeGroup(i)}
        >×</button>
      {/if}
    </div>
  {/each}
  <button class="add-group-btn" onclick={addGroup}>+ target group</button>
</div>

<style>
  .target-builder {
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 4px;
  }

  .group-row {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .group-input {
    font-family: var(--font-mono);
    font-size: 0.8rem;
    min-width: 120px;
    width: auto;
  }

  .plus-sep {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 700;
    color: var(--gold-dim);
    padding: 0 2px;
  }

  .remove-btn {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-dim);
    padding: 2px 6px;
    border-radius: 3px;
    line-height: 1;
    cursor: pointer;
    transition: color 0.1s;
  }

  .remove-btn:hover {
    color: var(--red-ink);
    background: rgba(139, 58, 58, 0.15);
  }

  .add-group-btn {
    font-family: var(--font-mono);
    font-size: 0.72rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--text-dim);
    padding: 2px 8px;
    border-radius: 3px;
    cursor: pointer;
    transition: border-color 0.1s, color 0.1s;
  }

  .add-group-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: transparent;
  }
</style>
