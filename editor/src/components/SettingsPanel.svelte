<script lang="ts">
  import { onMount } from 'svelte';
  import { store } from '../lib/store.svelte';
  import { listModels } from '../lib/ollama';
  import type { EditorSettings } from '../lib/persistence';

  interface Props {
    onclose: () => void;
  }

  let { onclose }: Props = $props();

  let localSettings = $state<EditorSettings>({ ...store.settings });
  let models = $state<string[]>([]);
  let loadingModels = $state(false);
  let connected = $state(false);

  async function fetchModels() {
    loadingModels = true;
    const result = await listModels();
    models = result;
    connected = result.length > 0;
    // If current model not in list, reset it
    if (localSettings.ollamaModel && !result.includes(localSettings.ollamaModel)) {
      localSettings.ollamaModel = result[0] ?? '';
    } else if (!localSettings.ollamaModel && result.length > 0) {
      localSettings.ollamaModel = result[0];
    }
    loadingModels = false;
  }

  onMount(() => {
    if (localSettings.ollamaEnabled) {
      fetchModels();
    }

    function handleKeydown(e: KeyboardEvent) {
      if (e.key === 'Escape') onclose();
    }
    window.addEventListener('keydown', handleKeydown);
    return () => window.removeEventListener('keydown', handleKeydown);
  });

  function handleOverlayClick(e: MouseEvent) {
    if (e.target === e.currentTarget) onclose();
  }

  function handleToggleOllama(e: Event) {
    localSettings.ollamaEnabled = (e.target as HTMLInputElement).checked;
    if (localSettings.ollamaEnabled && models.length === 0) {
      fetchModels();
    }
  }

  function handleModelChange(e: Event) {
    localSettings.ollamaModel = (e.target as HTMLSelectElement).value;
  }

  function handleSave() {
    store.updateSettings({ ...localSettings });
    onclose();
  }
</script>

<!-- svelte-ignore a11y_click_events_have_key_events -->
<!-- svelte-ignore a11y_no_static_element_interactions -->
<div class="overlay" onclick={handleOverlayClick}>
  <div class="panel" role="dialog" aria-modal="true" aria-label="Settings">
    <h2>Settings</h2>

    <section class="settings-section">
      <h3 class="section-heading">AI Generation (Ollama)</h3>

      <label class="checkbox-row">
        <input
          type="checkbox"
          checked={localSettings.ollamaEnabled}
          onchange={handleToggleOllama}
        />
        <span>Enable AI-powered descriptions</span>
      </label>

      {#if localSettings.ollamaEnabled}
        <div class="model-section">
          <div class="connection-status">
            <span class="status-dot" class:connected class:disconnected={!connected}></span>
            <span class="status-text">{connected ? 'Connected' : 'Not connected'}</span>
          </div>

          {#if loadingModels}
            <p class="hint">Loading models…</p>
          {:else if models.length === 0}
            <p class="hint">Ollama not running or no models installed</p>
          {:else}
            <div class="model-row">
              <label class="model-label" for="model-select">Model</label>
              <select
                id="model-select"
                value={localSettings.ollamaModel}
                onchange={handleModelChange}
              >
                {#each models as model (model)}
                  <option value={model}>{model}</option>
                {/each}
              </select>
            </div>
          {/if}

          <button class="refresh-btn" onclick={fetchModels} disabled={loadingModels}>
            {loadingModels ? 'Refreshing…' : 'Refresh'}
          </button>

          <label class="checkbox-row sub-option">
            <input
              type="checkbox"
              checked={localSettings.ollamaThinking}
              onchange={(e) => localSettings.ollamaThinking = (e.target as HTMLInputElement).checked}
            />
            <span>Enable thinking mode <span class="hint-inline">(slower, better quality — for models that support it)</span></span>
          </label>
        </div>
      {/if}
    </section>

    <div class="panel-actions">
      <button class="cancel-btn" onclick={onclose}>Cancel</button>
      <button class="save-btn" onclick={handleSave}>Save</button>
    </div>
  </div>
</div>

<style>
  .overlay {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
  }

  .panel {
    background: var(--dark-warm);
    border: 1px solid var(--warm-gray);
    border-radius: 12px;
    padding: 24px;
    width: 100%;
    max-width: 500px;
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  h2 {
    font-family: var(--font-title);
    font-size: 1.1rem;
    font-weight: 900;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--gold);
    margin: 0;
  }

  .settings-section {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .section-heading {
    font-family: var(--font-title);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.1em;
    text-transform: uppercase;
    color: var(--text-mid);
    margin: 0;
  }

  .checkbox-row {
    display: flex;
    align-items: center;
    gap: 8px;
    cursor: pointer;
    font-family: var(--font-body);
    font-size: 0.9rem;
    color: var(--text-light);
  }

  .checkbox-row input[type='checkbox'] {
    accent-color: var(--gold);
    width: 15px;
    height: 15px;
    cursor: pointer;
  }

  .model-section {
    display: flex;
    flex-direction: column;
    gap: 10px;
    padding-left: 23px;
  }

  .connection-status {
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .status-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    flex-shrink: 0;
  }

  .status-dot.connected {
    background: var(--green-ink);
  }

  .status-dot.disconnected {
    background: var(--red-ink);
  }

  .status-text {
    font-family: var(--font-body);
    font-size: 0.8rem;
    color: var(--text-dim);
  }

  .hint {
    font-family: var(--font-body);
    font-size: 0.82rem;
    color: var(--text-dim);
    font-style: italic;
    margin: 0;
  }

  .model-row {
    display: flex;
    align-items: center;
    gap: 10px;
  }

  .model-label {
    font-family: var(--font-title);
    font-size: 0.68rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    flex-shrink: 0;
  }

  select {
    flex: 1;
    background: var(--mid-dark);
    border: 1px solid var(--warm-gray);
    border-radius: 3px;
    color: var(--text-light);
    font-family: var(--font-body);
    font-size: 0.85rem;
    padding: 0.3em 0.5em;
  }

  select:focus {
    outline: none;
    border-color: var(--gold-dim);
  }

  .sub-option {
    margin-top: 4px;
    font-size: 0.85rem;
  }

  .hint-inline {
    color: var(--text-dim);
    font-size: 0.78rem;
  }

  .refresh-btn {
    font-size: 0.75rem;
    padding: 0.3em 0.7em;
    background: var(--dark-warm);
    border-color: var(--warm-gray);
    color: var(--text-mid);
    align-self: flex-start;
  }

  .refresh-btn:hover:not(:disabled) {
    border-color: var(--gold-dim);
    color: var(--gold);
    background: var(--dark-warm);
  }

  .refresh-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .panel-actions {
    display: flex;
    justify-content: flex-end;
    gap: 8px;
  }

  .cancel-btn {
    font-size: 0.82rem;
    padding: 0.4em 1em;
    background: transparent;
    border-color: var(--warm-gray);
    color: var(--text-mid);
  }

  .cancel-btn:hover {
    border-color: var(--text-mid);
    color: var(--text-light);
    background: transparent;
  }

  .save-btn {
    font-size: 0.82rem;
    padding: 0.4em 1.2em;
    background: var(--gold-dim);
    border-color: var(--gold-dim);
    color: var(--parchment-light);
  }

  .save-btn:hover {
    background: var(--gold);
    border-color: var(--gold);
    color: var(--black);
  }
</style>
