<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getRoomExits } from '../lib/helpers';
  import { loadMapPositions, saveMapPositions } from '../lib/persistence';

  const NODE_W = 160;
  const NODE_H = 50;

  // Rooms (state === null only = base rooms, not state variants)
  const rooms = $derived.by(() => {
    const game = store.game;
    if (!game) return [];
    return Object.values(game.rooms).filter((r) => r.state === null);
  });

  // Edges: movement arrows and cues
  interface Edge {
    from: string;
    to: string;
    isCue: boolean;
  }

  const edges = $derived.by(() => {
    const game = store.game;
    if (!game) return [] as Edge[];

    const seen = new Set<string>();
    const result: Edge[] = [];

    for (const room of rooms) {
      const exits = getRoomExits(game, room.name);
      for (const exit of exits) {
        // Only draw edges to rooms that exist in our rooms list
        const targetExists = rooms.some((r) => r.name === exit.targetRoom);
        if (!targetExists) continue;
        const key = `${room.name}→${exit.targetRoom}`;
        if (!seen.has(key)) {
          seen.add(key);
          result.push({ from: room.name, to: exit.targetRoom, isCue: false });
        }
      }
    }

    // Cues
    for (const cue of game.cues) {
      const targetExists = rooms.some((r) => r.name === cue.targetRoom);
      const triggerExists = rooms.some((r) => r.name === cue.triggerRoom);
      if (!targetExists || !triggerExists) continue;
      const key = `${cue.triggerRoom}⇢${cue.targetRoom}`;
      if (!seen.has(key)) {
        seen.add(key);
        result.push({ from: cue.triggerRoom, to: cue.targetRoom, isCue: true });
      }
    }

    return result;
  });

  // Positions state
  let positions = $state<Record<string, { x: number; y: number }>>({});

  // Auto-layout helper
  function autoLayout(roomNames: string[]): Record<string, { x: number; y: number }> {
    const result: Record<string, { x: number; y: number }> = {};
    roomNames.forEach((name, col) => {
      result[name] = {
        x: 100 + (col % 4) * 200,
        y: 100 + Math.floor(col / 4) * 120,
      };
    });
    return result;
  }

  // Load positions when project changes
  $effect(() => {
    const project = store.project;
    if (!project) {
      positions = {};
      return;
    }
    const saved = loadMapPositions(project.id);
    const merged: Record<string, { x: number; y: number }> = { ...saved };

    // Auto-layout any rooms without saved positions
    const unsaved = rooms.filter((r) => !merged[r.name]).map((r) => r.name);
    if (unsaved.length > 0) {
      const autoPositions = autoLayout(unsaved);
      for (const name of unsaved) {
        merged[name] = autoPositions[name];
      }
    }

    positions = merged;
  });

  // Drag state
  let dragging: string | null = $state(null);
  let dragOffsetX = $state(0);
  let dragOffsetY = $state(0);

  function startDrag(roomName: string, e: MouseEvent) {
    e.preventDefault();
    dragging = roomName;
    const pos = positions[roomName] ?? { x: 0, y: 0 };
    dragOffsetX = e.clientX - pos.x;
    dragOffsetY = e.clientY - pos.y;
  }

  function onMouseMove(e: MouseEvent) {
    if (!dragging) return;
    positions = {
      ...positions,
      [dragging]: {
        x: e.clientX - dragOffsetX,
        y: e.clientY - dragOffsetY,
      },
    };
  }

  function onMouseUp() {
    if (!dragging) return;
    const project = store.project;
    if (project) {
      saveMapPositions(project.id, positions);
    }
    dragging = null;
  }

  function handleDoubleClick(roomName: string) {
    store.showRoom(roomName);
  }

  function handleKeydown(roomName: string, e: KeyboardEvent) {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      store.showRoom(roomName);
    }
  }

  // SVG line helpers — center of a node
  function cx(name: string): number {
    return (positions[name]?.x ?? 0) + NODE_W / 2;
  }
  function cy(name: string): number {
    return (positions[name]?.y ?? 0) + NODE_H / 2;
  }

  const startRoom = $derived(store.game?.metadata?.start ?? null);

  // Compute SVG canvas size from max positions
  const svgWidth = $derived.by(() => {
    let max = 800;
    for (const pos of Object.values(positions)) {
      const right = pos.x + NODE_W + 40;
      if (right > max) max = right;
    }
    return max;
  });

  const svgHeight = $derived.by(() => {
    let max = 600;
    for (const pos of Object.values(positions)) {
      const bottom = pos.y + NODE_H + 40;
      if (bottom > max) max = bottom;
    }
    return max;
  });
</script>

<!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
<div
  class="map-container"
  role="application"
  aria-label="Room map"
  onmousemove={onMouseMove}
  onmouseup={onMouseUp}
>
  <!-- SVG layer for edges -->
  <svg
    class="map-svg"
    width={svgWidth}
    height={svgHeight}
    aria-hidden="true"
  >
    <defs>
      <marker
        id="arrowhead"
        markerWidth="8"
        markerHeight="6"
        refX="8"
        refY="3"
        orient="auto"
      >
        <polygon points="0 0, 8 3, 0 6" fill="var(--warm-gray)" />
      </marker>
      <marker
        id="arrowhead-cue"
        markerWidth="8"
        markerHeight="6"
        refX="8"
        refY="3"
        orient="auto"
      >
        <polygon points="0 0, 8 3, 0 6" fill="var(--parchment-dark)" />
      </marker>
    </defs>

    {#each edges as edge (edge.from + '→' + edge.to + edge.isCue)}
      {#if positions[edge.from] && positions[edge.to]}
        <line
          x1={cx(edge.from)}
          y1={cy(edge.from)}
          x2={cx(edge.to)}
          y2={cy(edge.to)}
          stroke={edge.isCue ? 'var(--parchment-dark)' : 'var(--warm-gray)'}
          stroke-width="1.5"
          stroke-dasharray={edge.isCue ? '6 4' : undefined}
          marker-end={edge.isCue ? 'url(#arrowhead-cue)' : 'url(#arrowhead)'}
          opacity="0.7"
        />
      {/if}
    {/each}
  </svg>

  <!-- Room nodes -->
  {#each rooms as room (room.name)}
    {#if positions[room.name]}
      <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
      <div
        class="room-node"
        class:start-room={room.name === startRoom}
        class:dragging={dragging === room.name}
        role="button"
        tabindex="0"
        aria-label="Room: {room.name}. Double-click to open."
        style="left: {positions[room.name].x}px; top: {positions[room.name].y}px; width: {NODE_W}px; height: {NODE_H}px;"
        onmousedown={(e) => startDrag(room.name, e)}
        ondblclick={() => handleDoubleClick(room.name)}
        onkeydown={(e) => handleKeydown(room.name, e)}
      >
        <span class="room-label">{room.name.replace(/_/g, ' ')}</span>
      </div>
    {/if}
  {/each}

  {#if rooms.length === 0}
    <div class="empty-state">
      <p>No rooms yet — add rooms in the sidebar to see them here.</p>
    </div>
  {/if}
</div>

<style>
  .map-container {
    position: relative;
    width: 100%;
    height: 100%;
    overflow: auto;
    background-color: var(--dark);
    user-select: none;
  }

  .map-svg {
    position: absolute;
    top: 0;
    left: 0;
    pointer-events: none;
  }

  .room-node {
    position: absolute;
    background-color: var(--mid-dark);
    border: 2px solid var(--warm-gray);
    border-radius: 8px;
    cursor: grab;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 0 12px;
    transition: border-color 0.15s, box-shadow 0.15s;
  }

  .room-node:hover {
    border-color: var(--parchment-dark);
    box-shadow: 0 0 8px rgba(180, 160, 120, 0.2);
  }

  .room-node:focus-visible {
    outline: 2px solid var(--gold);
    outline-offset: 2px;
  }

  .room-node.start-room {
    border-color: var(--gold);
  }

  .room-node.dragging {
    cursor: grabbing;
    border-color: var(--gold-dim);
    box-shadow: 0 4px 16px rgba(0, 0, 0, 0.5);
    z-index: 10;
  }

  .room-label {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--parchment-light);
    text-align: center;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
    max-width: 100%;
  }

  .empty-state {
    position: absolute;
    inset: 0;
    display: flex;
    align-items: center;
    justify-content: center;
    color: var(--text-dim);
    font-style: italic;
  }
</style>
