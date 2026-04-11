<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { EditorView, basicSetup } from 'codemirror';
  import { EditorState } from '@codemirror/state';
  import { markdown } from '@codemirror/lang-markdown';

  interface Props {
    content: string;
    onchange: (value: string) => void;
  }

  let { content, onchange }: Props = $props();

  let container: HTMLDivElement;
  let view: EditorView | null = null;
  let updating = false;

  const addventureTheme = EditorView.theme(
    {
      '&': {
        backgroundColor: 'var(--dark)',
        color: 'var(--text-light)',
        height: '100%',
        fontSize: '0.875rem',
      },
      '.cm-content': {
        caretColor: 'var(--gold)',
        fontFamily: 'var(--font-mono)',
        padding: '12px 0',
      },
      '.cm-cursor, .cm-dropCursor': {
        borderLeftColor: 'var(--gold)',
      },
      '&.cm-focused .cm-selectionBackground, .cm-selectionBackground, .cm-content ::selection':
        {
          backgroundColor: 'rgba(201,168,76,0.2)',
        },
      '.cm-activeLine': {
        backgroundColor: 'rgba(201,168,76,0.05)',
      },
      '.cm-gutters': {
        backgroundColor: 'var(--dark-warm)',
        color: 'var(--text-dim)',
        border: 'none',
        borderRight: '1px solid var(--warm-gray)',
      },
      '.cm-activeLineGutter': {
        backgroundColor: 'rgba(201,168,76,0.07)',
      },
      '.cm-lineNumbers .cm-gutterElement': {
        padding: '0 8px',
      },
      '.cm-foldGutter .cm-gutterElement': {
        padding: '0 4px',
      },
      '.cm-scroller': {
        overflow: 'auto',
        height: '100%',
      },
    },
    { dark: true },
  );

  onMount(() => {
    view = new EditorView({
      state: EditorState.create({
        doc: content,
        extensions: [
          basicSetup,
          markdown(),
          addventureTheme,
          EditorView.updateListener.of((update) => {
            if (update.docChanged && !updating) {
              onchange(update.state.doc.toString());
            }
          }),
        ],
      }),
      parent: container,
    });
  });

  onDestroy(() => {
    view?.destroy();
    view = null;
  });

  $effect(() => {
    // Sync external content changes into the editor
    if (!view) return;
    const current = view.state.doc.toString();
    if (current !== content) {
      updating = true;
      view.dispatch({
        changes: { from: 0, to: current.length, insert: content },
      });
      updating = false;
    }
  });
</script>

<div class="source-view" bind:this={container}></div>

<style>
  .source-view {
    flex: 1;
    overflow: hidden;
    display: flex;
    flex-direction: column;
    min-height: 0;
  }

  .source-view :global(.cm-editor) {
    height: 100%;
  }

  .source-view :global(.cm-editor.cm-focused) {
    outline: none;
  }
</style>
