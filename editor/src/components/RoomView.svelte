<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getRoomObjects, getRoomInteractions, displayName } from '../lib/helpers';
  import { serializeGame } from '../lib/serializer';
  import { parseGameFiles } from '../lib/parser';
  import ObjectCard from './ObjectCard.svelte';
  import InteractionCard from './InteractionCard.svelte';
  import InteractionEditor from './InteractionEditor.svelte';
  import SourceView from './SourceView.svelte';
  import GenerateButton from './GenerateButton.svelte';
  import SuggestObjectsDialog from './SuggestObjectsDialog.svelte';
  import ArrowEditor from './ArrowEditor.svelte';
  import { roomDescriptionPrompt } from '../lib/ollama';
  import type { Arrow } from '../lib/types';

  interface Props {
    roomName: string;
  }

  let { roomName }: Props = $props();

  import { objectKey, actionKey, createAction, createArrow } from '../lib/factory';

  let sourceMode = $state(false);
  let showSuggestObjects = $state(false);

  function handleSuggestedObjects(items: { name: string; description: string }[]) {
    store.mutate((g) => {
      for (const item of items) {
        const key = objectKey(roomName, item.name);
        if (!g.objects[key]) {
          g.objects[key] = {
            name: item.name,
            base: item.name.split('__')[0],
            state: item.name.includes('__') ? item.name.split('__').slice(1).join('__') : null,
            room: roomName,
            discovered: false,
          };
          g.interactions.push({
            verb: 'LOOK',
            targetGroups: [[item.name]],
            narrative: item.description,
            arrows: [],
            room: roomName,
            sealedContent: null,
            sealedArrows: [],
            signalChecks: [],
          });
        }
      }
    });
  }

  // Inline add state
  let addingObject = $state(false);
  let newObjectName = $state('');
  let addingFreeform = $state(false);
  let newFreeformVerb = $state('');
  let editingFreeformIdx = $state<number | null>(null);
  let addingAction = $state(false);
  let newActionName = $state('');
  let editingActionKey = $state<string | null>(null);

  function focusEl(el: HTMLElement) {
    el.focus();
  }

  function submitObject() {
    const name = newObjectName.trim().toUpperCase().replace(/\s+/g, '_');
    if (!name || !game) return;
    const key = objectKey(roomName, name);
    if (game.objects[key]) return; // already exists
    store.addObject(roomName, name);
    // Auto-create a LOOK interaction stub for the new object
    store.mutate((g) => {
      g.interactions.push({
        verb: 'LOOK',
        targetGroups: [[name]],
        narrative: '',
        arrows: [],
        room: roomName,
        sealedContent: null,
        sealedArrows: [],
        signalChecks: [],
      });
    });
    newObjectName = '';
    addingObject = false;
  }

  function submitFreeform() {
    const verb = newFreeformVerb.trim().toUpperCase().replace(/\s+/g, '_');
    if (!verb || !game) return;
    store.mutate((g) => {
      g.interactions.push({
        verb,
        targetGroups: [['*']],
        narrative: '',
        arrows: [],
        room: roomName,
        sealedContent: null,
        sealedArrows: [],
        signalChecks: [],
      });
    });
    newFreeformVerb = '';
    addingFreeform = false;
  }

  function submitAction() {
    const name = newActionName.trim().toUpperCase().replace(/\s+/g, '_');
    if (!name || !game) return;
    const key = actionKey(roomName, name);
    if (game.actions[key]) return; // already exists
    store.mutate((g) => {
      g.actions[key] = createAction(name, roomName);
    });
    newActionName = '';
    addingAction = false;
  }

  function deleteAction(key: string) {
    store.mutate((g) => {
      delete g.actions[key];
    });
    if (editingActionKey === key) editingActionKey = null;
  }

  const game = $derived(store.game);

  const isStartRoom = $derived(game?.metadata.start === roomName);

  /** LOOK interaction: verb === 'LOOK' and targetGroups is empty or contains @ROOM */
  const lookInteraction = $derived.by(() => {
    if (!game) return null;
    return (
      game.interactions.find(
        (i) =>
          i.room === roomName &&
          i.verb === 'LOOK' &&
          (i.targetGroups.length === 0 ||
            i.targetGroups.some((g) => g.includes('@ROOM'))),
      ) ?? null
    );
  });

  const lookText = $derived(lookInteraction?.narrative ?? '');

  function updateLookText(value: string) {
    store.mutate((g) => {
      const existing = g.interactions.find(
        (i) =>
          i.room === roomName &&
          i.verb === 'LOOK' &&
          (i.targetGroups.length === 0 ||
            i.targetGroups.some((group) => group.includes('@ROOM'))),
      );
      if (existing) {
        existing.narrative = value;
      } else {
        g.interactions.push({
          verb: 'LOOK',
          targetGroups: [],
          narrative: value,
          arrows: [],
          room: roomName,
          sealedContent: null,
          sealedArrows: [],
          signalChecks: [],
        });
      }
    });
  }

  /** Unique base object names in room */
  const roomObjectBases = $derived.by(() => {
    if (!game) return [];
    const grouped = getRoomObjects(game, roomName);
    return Object.keys(grouped).sort();
  });

  /** Flat list of object names for prompt building */
  const objectNames = $derived(roomObjectBases);

  /** Freeform interactions: wildcard (*) or multi-group targets */
  const freeformInteractions = $derived.by(() => {
    if (!game) return [];
    return getRoomInteractions(game, roomName).filter((i) => {
      if (i.verb === 'LOOK' && i.targetGroups.length === 0) return false;
      if (i.targetGroups.length === 0) return true; // room-level, non-LOOK
      // wildcard
      if (i.targetGroups.some((g) => g.includes('*'))) return true;
      // multi-group
      if (i.targetGroups.length > 1) return true;
      return false;
    });
  });

  function freeformInteractionIndex(interaction: (typeof freeformInteractions)[number]): number {
    if (!game) return -1;
    return game.interactions.indexOf(interaction);
  }

  /** Room actions */
  const roomActions = $derived.by(() => {
    if (!game) return [] as { key: string; action: typeof game.actions[string] }[];
    return Object.entries(game.actions)
      .filter(([, a]) => a.room === roomName)
      .map(([key, action]) => ({ key, action }));
  });

  /** Serialized content for this room's .md file */
  const roomSource = $derived.by(() => {
    if (!game) return '';
    const files = serializeGame(game);
    const filename = roomName.toLowerCase().replace(/ /g, '_') + '.md';
    return files[filename] ?? '';
  });

  function handleSourceChange(newSource: string): void {
    if (!game) return;
    store.mutate((g) => {
      // Remove old data for this room
      g.interactions = g.interactions.filter((i) => i.room !== roomName);
      for (const key of Object.keys(g.objects)) {
        if (g.objects[key].room === roomName) {
          delete g.objects[key];
        }
      }
      for (const key of Object.keys(g.actions)) {
        if (g.actions[key].room === roomName) {
          delete g.actions[key];
        }
      }
      // Remove room state variants (keep only the base room entry)
      for (const key of Object.keys(g.rooms)) {
        const r = g.rooms[key];
        if (r.name !== roomName && r.base === roomName.split('__')[0]) {
          delete g.rooms[key];
        }
      }
      // Re-parse the updated room file and merge in
      const parsed = parseGameFiles({ 'index.md': '', [roomName.toLowerCase().replace(/ /g, '_') + '.md']: newSource });
      // Merge objects
      for (const [key, obj] of Object.entries(parsed.objects)) {
        g.objects[key] = obj;
      }
      // Merge interactions
      g.interactions.push(...parsed.interactions);
      // Merge cues
      g.cues.push(...parsed.cues);
      // Merge actions
      for (const [key, action] of Object.entries(parsed.actions)) {
        g.actions[key] = action;
      }
      // Merge any new rooms (state variants)
      for (const [key, room] of Object.entries(parsed.rooms)) {
        if (!g.rooms[key]) {
          g.rooms[key] = room;
        }
      }
    });
  }
</script>

<div class="room-view">
  <!-- Room header -->
  <div class="room-header">
    <div class="header-left">
      <h2>{roomName}</h2>
      {#if isStartRoom}
        <span class="badge badge-start">start room</span>
      {/if}
    </div>
    <div class="header-right">
      <div class="view-toggle">
        <button
          class="toggle-btn"
          class:active={!sourceMode}
          onclick={() => (sourceMode = false)}
        >Visual</button>
        <button
          class="toggle-btn"
          class:active={sourceMode}
          onclick={() => (sourceMode = true)}
        >Source</button>
      </div>
    </div>
  </div>

  {#if sourceMode}
    <SourceView content={roomSource} onchange={handleSourceChange} />
  {:else}
    <div class="room-content">
      <!-- Room Description -->
      <section class="section">
        <div class="label-row">
          <label class="section-label" for="room-look">Room Description (LOOK)</label>
          <GenerateButton
            prompt={roomDescriptionPrompt(roomName, objectNames, store.game!, store.settings.narratorVoice || undefined)}
            ongenerated={(text) => updateLookText(text)}
          />
        </div>
        <textarea
          id="room-look"
          rows="3"
          value={lookText}
          oninput={(e) => updateLookText((e.target as HTMLTextAreaElement).value)}
          placeholder="What does the player see when they look around?"
        ></textarea>
      </section>

      <!-- Objects -->
      <section class="section">
        <div class="section-header-row">
          <span class="section-label">Objects in this Room</span>
          {#if store.settings.ollamaEnabled && store.settings.ollamaModel}
            <button class="ai-btn" onclick={() => showSuggestObjects = true} title="Suggest objects with AI">✦ AI suggest</button>
          {/if}
        </div>
        {#if roomObjectBases.length === 0}
          <p class="empty-hint">No objects in this room yet.</p>
        {:else}
          {#each roomObjectBases as baseName (baseName)}
            <ObjectCard objectName={baseName} {roomName} />
          {/each}
        {/if}
        {#if addingObject}
          <div class="inline-add">
            <input
              type="text"
              class="mono"
              bind:value={newObjectName}
              placeholder="OBJECT_NAME"
              use:focusEl
              onkeydown={(e) => {
                if (e.key === 'Enter') submitObject();
                if (e.key === 'Escape') { addingObject = false; newObjectName = ''; }
              }}
              onblur={() => { addingObject = false; newObjectName = ''; }}
            />
          </div>
        {:else}
          <button class="add-btn" onclick={() => addingObject = true}>+ Add object</button>
        {/if}
      </section>

      <!-- Freeform interactions -->
      <section class="section">
        <div class="section-header-row">
          <span class="section-label">Freeform Interactions</span>
        </div>
        {#if freeformInteractions.length === 0}
          <p class="empty-hint">No wildcard or multi-target interactions.</p>
        {:else}
          {#each freeformInteractions as interaction, localIdx (interaction.verb + JSON.stringify(interaction.targetGroups))}
            {@const globalIdx = freeformInteractionIndex(interaction)}
            {#if editingFreeformIdx === globalIdx && globalIdx !== -1}
              <InteractionEditor
                {interaction}
                interactionIndex={globalIdx}
                onclose={() => { editingFreeformIdx = null; }}
              />
            {:else}
              <button
                class="card-btn"
                onclick={() => { editingFreeformIdx = globalIdx; }}
                title="Click to edit"
              >
                <InteractionCard {interaction} />
              </button>
            {/if}
          {/each}
        {/if}
        {#if addingFreeform}
          <div class="inline-add">
            <input
              type="text"
              class="mono"
              bind:value={newFreeformVerb}
              placeholder="VERB (e.g. USE)"
              use:focusEl
              onkeydown={(e) => {
                if (e.key === 'Enter') submitFreeform();
                if (e.key === 'Escape') { addingFreeform = false; newFreeformVerb = ''; }
              }}
              onblur={() => { addingFreeform = false; newFreeformVerb = ''; }}
            />
          </div>
        {:else}
          <button class="add-btn" onclick={() => addingFreeform = true}>+ Add freeform interaction</button>
        {/if}
      </section>

      <!-- Actions -->
      <section class="section">
        <div class="section-header-row">
          <span class="section-label">Actions</span>
        </div>
        {#if roomActions.length === 0}
          <p class="empty-hint">No direct actions (&gt; ACTION_NAME) in this room.</p>
        {:else}
          {#each roomActions as { key, action } (key)}
            {#if editingActionKey === key}
              <div class="action-editor">
                <div class="action-editor-header">
                  <span class="action-name mono">&gt; {action.name}</span>
                  <div class="action-header-controls">
                    <label class="discovered-label">
                      <input
                        type="checkbox"
                        checked={action.discovered}
                        onchange={(e) => store.mutate((g) => { g.actions[key].discovered = (e.target as HTMLInputElement).checked; })}
                      />
                      discovered
                    </label>
                    <button class="delete-action-btn" onclick={() => deleteAction(key)}>Delete</button>
                    <button class="done-btn-small" onclick={() => { editingActionKey = null; }}>Done</button>
                  </div>
                </div>
                <label class="field-label-sm" for="action-narrative-{key}">Narrative</label>
                <textarea
                  id="action-narrative-{key}"
                  rows="3"
                  class="action-narrative"
                  value={action.narrative}
                  oninput={(e) => store.mutate((g) => { g.actions[key].narrative = (e.target as HTMLTextAreaElement).value; })}
                  placeholder="What happens when this action is used?"
                ></textarea>
                <div class="action-arrows">
                  <div class="field-label-sm">Arrows</div>
                  {#each action.arrows as arrow, i (i)}
                    <ArrowEditor
                      {arrow}
                      onchange={(a: Arrow) => store.mutate((g) => { g.actions[key].arrows[i] = a; })}
                      ondelete={() => store.mutate((g) => { g.actions[key].arrows.splice(i, 1); })}
                      roomName={roomName}
                    />
                  {/each}
                  <button class="add-arrow-btn-sm" onclick={() => store.mutate((g) => { g.actions[key].arrows.push(createArrow('', '')); })}>+ Add arrow</button>
                </div>
              </div>
            {:else}
              <div class="action-card">
                <button
                  class="action-card-inner"
                  onclick={() => { editingActionKey = key; }}
                  title="Click to edit"
                >
                  <span class="action-card-name mono">&gt; {action.name}</span>
                  {#if action.discovered}
                    <span class="badge-discovered">discovered</span>
                  {/if}
                  {#if action.narrative}
                    <span class="action-card-narrative">{action.narrative.slice(0, 60)}{action.narrative.length > 60 ? '…' : ''}</span>
                  {/if}
                </button>
              </div>
            {/if}
          {/each}
        {/if}
        {#if addingAction}
          <div class="inline-add">
            <input
              type="text"
              class="mono"
              bind:value={newActionName}
              placeholder="ACTION_NAME (e.g. GO_NORTH)"
              use:focusEl
              onkeydown={(e) => {
                if (e.key === 'Enter') submitAction();
                if (e.key === 'Escape') { addingAction = false; newActionName = ''; }
              }}
              onblur={() => { addingAction = false; newActionName = ''; }}
            />
          </div>
        {:else}
          <button class="add-btn" onclick={() => addingAction = true}>+ Add action</button>
        {/if}
      </section>
    </div>
  {/if}
</div>

{#if showSuggestObjects}
  <SuggestObjectsDialog
    {roomName}
    existingObjects={roomObjectBases}
    onselected={handleSuggestedObjects}
    onclose={() => showSuggestObjects = false}
  />
{/if}

<style>
  .room-view {
    display: flex;
    flex-direction: column;
    height: 100%;
    overflow: hidden;
  }

  /* Header */
  .room-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 12px 24px;
    border-bottom: 1px solid var(--warm-gray);
    flex-shrink: 0;
  }

  .header-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  h2 {
    font-family: var(--font-title);
    font-size: 1.2rem;
    font-weight: 900;
    letter-spacing: 0.05em;
    text-transform: uppercase;
    color: var(--parchment-light);
  }

  .badge {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 2px 8px;
    border-radius: 3px;
  }

  .badge-start {
    background: rgba(201, 168, 76, 0.2);
    color: var(--gold);
    border: 1px solid var(--gold-dim);
  }

  .header-right {
    display: flex;
    align-items: center;
  }

  .view-toggle {
    display: flex;
    gap: 2px;
    background: var(--dark);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    padding: 2px;
  }

  .toggle-btn {
    font-family: var(--font-title);
    font-size: 0.7rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    background: transparent;
    border: none;
    color: var(--text-dim);
    padding: 3px 10px;
    border-radius: 3px;
    cursor: pointer;
    transition: background-color 0.15s, color 0.15s;
  }

  .toggle-btn.active {
    background: var(--warm-gray);
    color: var(--parchment);
  }

  /* Content */
  .room-content {
    flex: 1;
    overflow-y: auto;
    padding: 20px 24px;
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  .section {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  .section-label {
    font-family: var(--font-title);
    font-size: 0.72rem;
    font-weight: 800;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-mid);
  }

  .label-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  .section-header-row {
    display: flex;
    align-items: center;
    gap: 8px;
    margin-bottom: 4px;
  }

  textarea {
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.9rem;
    padding: 0.5em 0.7em;
    resize: vertical;
    width: 100%;
    transition: border-color 0.15s;
  }

  textarea:focus {
    outline: none;
    border-color: var(--gold-dim);
  }

  .empty-hint {
    font-size: 0.82rem;
    color: var(--text-dim);
    font-style: italic;
  }

  .add-btn {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--text-dim);
    padding: 5px 12px;
    border-radius: 4px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    align-self: flex-start;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-btn:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: transparent;
  }
  /* .ai-btn defined globally in theme.css */

  .inline-add {
    padding: 6px 0;
  }

  .inline-add input {
    width: 100%;
    font-size: 0.85rem;
    padding: 6px 10px;
  }

  /* Freeform card button wrapper */
  .card-btn {
    display: block;
    width: 100%;
    background: transparent;
    border: none;
    padding: 0;
    cursor: pointer;
    text-align: left;
    border-radius: 4px;
    transition: outline 0.1s;
  }

  .card-btn:hover {
    outline: 1px solid var(--gold-dim);
  }

  /* Action editor */
  .action-editor {
    background: var(--dark-warm);
    border: 1px solid rgba(201, 168, 76, 0.35);
    border-radius: 6px;
    padding: 12px;
    display: flex;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 4px;
  }

  .action-editor-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 8px;
  }

  .action-header-controls {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .action-name {
    font-family: var(--font-mono);
    font-size: 0.85rem;
    color: var(--gold);
    font-weight: 600;
  }

  .action-narrative {
    width: 100%;
    font-family: var(--font-body);
    font-size: 0.85rem;
    resize: vertical;
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-light);
    padding: 0.4em 0.6em;
  }

  .action-narrative:focus {
    outline: none;
    border-color: var(--gold-dim);
  }

  .action-arrows {
    display: flex;
    flex-direction: column;
    gap: 4px;
  }

  .field-label-sm {
    font-family: var(--font-title);
    font-size: 0.65rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: var(--text-dim);
    margin-bottom: 2px;
  }

  .add-arrow-btn-sm {
    font-family: var(--font-mono);
    font-size: 0.7rem;
    font-weight: 400;
    text-transform: none;
    letter-spacing: 0;
    background: transparent;
    border: 1px dashed var(--warm-gray);
    color: var(--text-dim);
    padding: 2px 8px;
    border-radius: 4px;
    width: 100%;
    text-align: left;
    cursor: pointer;
    margin-top: 2px;
    transition: border-color 0.15s, color 0.15s;
  }

  .add-arrow-btn-sm:hover {
    border-color: var(--gold-dim);
    color: var(--gold);
  }

  .delete-action-btn {
    font-size: 0.7rem;
    padding: 2px 8px;
    background: rgba(139, 58, 58, 0.2);
    border-color: rgba(139, 58, 58, 0.5);
    color: var(--red-ink);
  }

  .delete-action-btn:hover {
    background: rgba(139, 58, 58, 0.35);
  }

  .done-btn-small {
    font-size: 0.7rem;
    padding: 2px 8px;
  }

  .discovered-label {
    display: flex;
    align-items: center;
    gap: 4px;
    font-family: var(--font-body);
    font-size: 0.75rem;
    color: var(--text-dim);
    cursor: pointer;
    user-select: none;
  }

  /* Action card (collapsed view) */
  .action-card {
    margin-bottom: 4px;
  }

  .action-card-inner {
    display: flex;
    align-items: baseline;
    gap: 8px;
    width: 100%;
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 4px;
    padding: 7px 10px;
    cursor: pointer;
    text-align: left;
    transition: border-color 0.15s;
  }

  .action-card-inner:hover {
    border-color: var(--gold-dim);
  }

  .action-card-name {
    font-family: var(--font-mono);
    font-size: 0.82rem;
    color: var(--gold);
    font-weight: 600;
    flex-shrink: 0;
  }

  .action-card-narrative {
    font-size: 0.8rem;
    color: var(--text-dim);
    font-style: italic;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    flex: 1;
    min-width: 0;
  }

  .badge-discovered {
    font-family: var(--font-title);
    font-size: 0.55rem;
    font-weight: 700;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    padding: 0.1em 0.4em;
    border-radius: 2px;
    background: rgba(201, 168, 76, 0.15);
    color: var(--gold-dim);
    border: 1px solid var(--gold-dim);
    flex-shrink: 0;
  }

  .mono {
    font-family: var(--font-mono);
  }
</style>
