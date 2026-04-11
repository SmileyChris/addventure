<script lang="ts">
  import type { Arrow } from '../lib/types';
  import { store } from '../lib/store.svelte';
  import { classifyArrow } from '../lib/helpers';
  import { createArrow } from '../lib/factory';

  interface Props {
    arrow: Arrow;
    onchange: (a: Arrow) => void;
    ondelete: () => void;
    roomName: string;
  }

  let { arrow, onchange, ondelete, roomName }: Props = $props();

  const ARROW_TYPES = [
    { value: 'destroy', label: 'Destroy' },
    { value: 'pickup', label: 'Pick up' },
    { value: 'move', label: 'Move player' },
    { value: 'transform', label: 'Transform' },
    { value: 'reveal', label: 'Reveal in room' },
    { value: 'cue', label: 'Cue' },
    { value: 'signal', label: 'Signal' },
    { value: 'reveal_verb', label: 'Reveal verb' },
    { value: 'discover_action', label: 'Discover action' },
    { value: 'room_state', label: 'Change room state' },
  ] as const;

  const currentType = $derived(classifyArrow(arrow));

  const allRooms = $derived(store.game ? Object.keys(store.game.rooms) : []);

  const roomObjects = $derived.by(() => {
    if (!store.game) return [] as string[];
    return Object.values(store.game.objects)
      .filter((o) => o.room === roomName)
      .map((o) => o.name);
  });

  const objectListId = $derived(`arrow-objects-${roomName.replace(/\s+/g, '-')}`);

  function setType(newType: string) {
    switch (newType) {
      case 'destroy':
        onchange(createArrow('OBJECT', 'trash'));
        break;
      case 'pickup':
        onchange(createArrow('OBJECT', 'player'));
        break;
      case 'move':
        onchange(createArrow('player', allRooms[0] ?? 'ROOM'));
        break;
      case 'transform':
        onchange(createArrow('OBJECT', 'OBJECT__STATE'));
        break;
      case 'reveal':
        onchange(createArrow('OBJECT', 'room'));
        break;
      case 'cue':
        onchange(createArrow('?', allRooms[0] ?? 'ROOM'));
        break;
      case 'signal':
        onchange({ subject: 'SIGNAL_NAME', destination: 'signal', signalName: 'SIGNAL_NAME' });
        break;
      case 'reveal_verb':
        onchange(createArrow('', 'VERB'));
        break;
      case 'discover_action':
        onchange(createArrow('>ACTION', ''));
        break;
      case 'room_state':
        onchange(createArrow('room', 'STATE'));
        break;
    }
  }

  function updateSubject(val: string) {
    onchange({ ...arrow, subject: val });
  }

  function updateDestination(val: string) {
    onchange({ ...arrow, destination: val });
  }

  function updateSignalName(val: string) {
    onchange({ ...arrow, subject: val, signalName: val });
  }
</script>

<datalist id={objectListId}>
  {#each roomObjects as obj (obj)}
    <option value={obj}></option>
  {/each}
</datalist>

<div class="arrow-row">
  <!-- Type selector -->
  <select
    class="type-select"
    value={currentType}
    onchange={(e) => setType((e.target as HTMLSelectElement).value)}
  >
    {#each ARROW_TYPES as t (t.value)}
      <option value={t.value}>{t.label}</option>
    {/each}
  </select>

  <!-- Adaptive fields -->
  {#if currentType === 'destroy'}
    <input
      type="text"
      class="field-input"
      value={arrow.subject}
      placeholder="OBJECT"
      list={objectListId}
      oninput={(e) => updateSubject((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'pickup'}
    <input
      type="text"
      class="field-input"
      value={arrow.subject}
      placeholder="OBJECT"
      list={objectListId}
      oninput={(e) => updateSubject((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'reveal'}
    <input
      type="text"
      class="field-input"
      value={arrow.subject}
      placeholder="OBJECT"
      list={objectListId}
      oninput={(e) => updateSubject((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'move'}
    <select
      class="field-select"
      value={arrow.destination}
      onchange={(e) => updateDestination((e.target as HTMLSelectElement).value)}
    >
      {#each allRooms as r (r)}
        <option value={r}>{r}</option>
      {/each}
    </select>
  {:else if currentType === 'cue'}
    <select
      class="field-select"
      value={arrow.destination}
      onchange={(e) => updateDestination((e.target as HTMLSelectElement).value)}
    >
      {#each allRooms as r (r)}
        <option value={r}>{r}</option>
      {/each}
    </select>
  {:else if currentType === 'transform'}
    <input
      type="text"
      class="field-input field-half"
      value={arrow.subject}
      placeholder="OBJECT"
      list={objectListId}
      oninput={(e) => updateSubject((e.target as HTMLInputElement).value)}
    />
    <span class="transform-arrow">→</span>
    <input
      type="text"
      class="field-input field-half"
      value={arrow.destination}
      placeholder="OBJECT__STATE"
      oninput={(e) => updateDestination((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'signal'}
    <input
      type="text"
      class="field-input mono"
      value={arrow.signalName ?? arrow.subject}
      placeholder="SIGNAL_NAME"
      oninput={(e) => updateSignalName((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'reveal_verb'}
    <input
      type="text"
      class="field-input"
      value={arrow.destination}
      placeholder="VERB"
      oninput={(e) => updateDestination((e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'discover_action'}
    <input
      type="text"
      class="field-input"
      value={arrow.subject.startsWith('>') ? arrow.subject.slice(1) : arrow.subject}
      placeholder="ACTION"
      oninput={(e) => updateSubject('>' + (e.target as HTMLInputElement).value)}
    />
  {:else if currentType === 'room_state'}
    <input
      type="text"
      class="field-input"
      value={arrow.destination}
      placeholder="STATE"
      oninput={(e) => updateDestination((e.target as HTMLInputElement).value)}
    />
  {:else}
    <!-- Fallback for verb_restore or unknown -->
    <input
      type="text"
      class="field-input field-half"
      value={arrow.subject}
      placeholder="subject"
      oninput={(e) => updateSubject((e.target as HTMLInputElement).value)}
    />
    <span class="transform-arrow">→</span>
    <input
      type="text"
      class="field-input field-half"
      value={arrow.destination}
      placeholder="destination"
      oninput={(e) => updateDestination((e.target as HTMLInputElement).value)}
    />
  {/if}

  <!-- Delete -->
  <button class="delete-btn" title="Remove arrow" onclick={ondelete}>×</button>
</div>

<style>
  .arrow-row {
    display: flex;
    align-items: center;
    gap: 6px;
    margin-bottom: 4px;
  }

  .type-select,
  .field-select {
    font-family: var(--font-body);
    font-size: 0.78rem;
    color: var(--text-light);
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    padding: 3px 6px;
    cursor: pointer;
    outline: none;
  }

  .type-select:focus,
  .field-select:focus {
    border-color: var(--gold-dim);
  }

  .type-select {
    flex-shrink: 0;
  }

  .field-select {
    flex: 1;
  }

  .field-input {
    font-family: var(--font-mono);
    font-size: 0.78rem;
    flex: 1;
    min-width: 80px;
  }

  .field-input.mono {
    font-family: var(--font-mono);
    letter-spacing: 0.02em;
  }

  .field-half {
    flex: 0.5;
    min-width: 60px;
  }

  .transform-arrow {
    color: var(--text-dim);
    font-size: 0.85rem;
    flex-shrink: 0;
  }

  .delete-btn {
    font-family: var(--font-mono);
    font-size: 0.9rem;
    font-weight: 700;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px solid transparent;
    color: var(--text-dim);
    padding: 2px 7px;
    border-radius: 3px;
    flex-shrink: 0;
    cursor: pointer;
    line-height: 1;
    transition: color 0.1s;
  }

  .delete-btn:hover {
    color: var(--red-ink);
    background: rgba(139, 58, 58, 0.15);
  }
</style>
