<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { getRoomExits, getRoomObjects } from '../lib/helpers';
  import { loadMapPositions, saveMapPositions } from '../lib/persistence';
  import PuzzleFlow from './PuzzleFlow.svelte';

  // Active sub-tab: 'map' or 'flow'
  let activeTab = $state<'map' | 'flow'>('map');

  const NODE_W = 160;
  const NODE_H = 64; // taller to fit object count

  // Rooms (state === null only = base rooms, not state variants)
  const rooms = $derived.by(() => {
    const game = store.game;
    if (!game) return [];
    return Object.values(game.rooms).filter((r) => r.state === null);
  });

  // Per-room object counts
  const roomObjectCounts = $derived.by(() => {
    const game = store.game;
    if (!game) return {} as Record<string, number>;
    const result: Record<string, number> = {};
    for (const room of rooms) {
      const objs = getRoomObjects(game, room.name);
      result[room.name] = Object.keys(objs).length;
    }
    return result;
  });

  // Rooms without a LOOK description (no interaction with verb LOOK)
  const roomsWithoutLook = $derived.by(() => {
    const game = store.game;
    if (!game) return new Set<string>();
    const hasLook = new Set<string>();
    for (const interaction of game.interactions) {
      if (interaction.verb === 'LOOK' && interaction.narrative?.trim()) {
        hasLook.add(interaction.room);
      }
    }
    return new Set(rooms.filter((r) => !hasLook.has(r.name)).map((r) => r.name));
  });

  // Edges: movement arrows and cues — now with via info
  interface Edge {
    from: string;
    to: string;
    isCue: boolean;
    via: string;
  }

  const edges = $derived.by(() => {
    const game = store.game;
    if (!game) return [] as Edge[];

    const seen = new Set<string>();
    const result: Edge[] = [];

    for (const room of rooms) {
      const exits = getRoomExits(game, room.name);
      for (const exit of exits) {
        const targetExists = rooms.some((r) => r.name === exit.targetRoom);
        if (!targetExists) continue;
        const key = `${room.name}→${exit.targetRoom}`;
        if (!seen.has(key)) {
          seen.add(key);
          result.push({ from: room.name, to: exit.targetRoom, isCue: false, via: exit.via });
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
        result.push({ from: cue.triggerRoom, to: cue.targetRoom, isCue: true, via: 'cue' });
      }
    }

    return result;
  });

  // Build a set of bidirectional edge pairs for offset calculation
  const bidirectionalPairs = $derived.by(() => {
    const pairs = new Set<string>();
    const edgeKeys = new Set(edges.map((e) => `${e.from}→${e.to}`));
    for (const edge of edges) {
      if (edgeKeys.has(`${edge.to}→${edge.from}`)) {
        // Use sorted key to avoid double-counting
        const sorted = [edge.from, edge.to].sort().join('↔');
        pairs.add(sorted);
      }
    }
    return pairs;
  });

  function isBidirectional(edge: Edge): boolean {
    const sorted = [edge.from, edge.to].sort().join('↔');
    return bidirectionalPairs.has(sorted);
  }

  // Positions state
  let positions = $state<Record<string, { x: number; y: number }>>({});

  // Auto-layout helper
  function autoLayout(roomNames: string[]): Record<string, { x: number; y: number }> {
    const result: Record<string, { x: number; y: number }> = {};
    roomNames.forEach((name, col) => {
      result[name] = {
        x: 100 + (col % 4) * 200,
        y: 100 + Math.floor(col / 4) * 140,
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

  // Compute perpendicular offset for bidirectional edges
  function getOffsetLine(
    edge: Edge,
    offsetDir: 1 | -1,
  ): { x1: number; y1: number; x2: number; y2: number } {
    const x1 = cx(edge.from);
    const y1 = cy(edge.from);
    const x2 = cx(edge.to);
    const y2 = cy(edge.to);

    const dx = x2 - x1;
    const dy = y2 - y1;
    const len = Math.sqrt(dx * dx + dy * dy) || 1;

    // Perpendicular unit vector
    const px = (-dy / len) * 8 * offsetDir;
    const py = (dx / len) * 8 * offsetDir;

    return { x1: x1 + px, y1: y1 + py, x2: x2 + px, y2: y2 + py };
  }

  // For each edge, determine which "side" it is (if bidir, first seen = +1, second = -1)
  const edgeOffsets = $derived.by(() => {
    const seen = new Map<string, 1 | -1>();
    const result: (1 | -1 | 0)[] = [];
    for (const edge of edges) {
      if (!isBidirectional(edge)) {
        result.push(0);
        continue;
      }
      const key = [edge.from, edge.to].sort().join('↔');
      if (!seen.has(key)) {
        seen.set(key, 1);
        result.push(1);
      } else {
        result.push(-1);
      }
    }
    return result;
  });

  // Midpoint of a (possibly offset) line for label placement
  function midpoint(line: { x1: number; y1: number; x2: number; y2: number }) {
    return {
      mx: (line.x1 + line.x2) / 2,
      my: (line.y1 + line.y2) / 2,
    };
  }

  const startRoom = $derived(store.game?.metadata?.start ?? null);

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

  // Format verb label for edges — shorten for readability
  function edgeVerbLabel(via: string): string {
    if (!via) return '';
    // Take just the base verb (before __)
    return via.split('__')[0];
  }
</script>

<div class="mapview-wrapper">
  <!-- Sub-tab bar -->
  <div class="tab-bar">
    <button
      class="tab-btn"
      class:active={activeTab === 'map'}
      onclick={() => (activeTab = 'map')}
    >
      Room Map
    </button>
    <button
      class="tab-btn"
      class:active={activeTab === 'flow'}
      onclick={() => (activeTab = 'flow')}
    >
      Puzzle Flow
    </button>
  </div>

  <!-- Tab content -->
  {#if activeTab === 'map'}
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

        {#each edges as edge, i (edge.from + '→' + edge.to + edge.isCue)}
          {#if positions[edge.from] && positions[edge.to]}
            {@const offset = edgeOffsets[i]}
            {@const line =
              offset === 0
                ? { x1: cx(edge.from), y1: cy(edge.from), x2: cx(edge.to), y2: cy(edge.to) }
                : getOffsetLine(edge, offset)}
            {@const { mx, my } = midpoint(line)}
            {@const verbLabel = edgeVerbLabel(edge.via)}
            {@const labelLen = verbLabel.length * 5.5 + 8}

            <line
              x1={line.x1}
              y1={line.y1}
              x2={line.x2}
              y2={line.y2}
              stroke={edge.isCue ? 'var(--parchment-dark)' : 'var(--warm-gray)'}
              stroke-width="1.5"
              stroke-dasharray={edge.isCue ? '6 4' : undefined}
              marker-end={edge.isCue ? 'url(#arrowhead-cue)' : 'url(#arrowhead)'}
              opacity="0.7"
            />

            <!-- Edge label with background rect -->
            {#if verbLabel}
              <rect
                x={mx - labelLen / 2}
                y={my - 8}
                width={labelLen}
                height={14}
                rx="2"
                fill="var(--dark)"
                opacity="0.85"
              />
              <text
                x={mx}
                y={my + 3}
                text-anchor="middle"
                font-family="var(--font-mono)"
                font-size="9"
                fill={edge.isCue ? 'var(--parchment-dark)' : 'var(--text-mid)'}
              >{verbLabel}</text>
            {/if}
          {/if}
        {/each}

        <!-- Mini legend: bottom-right -->
        <g transform="translate({svgWidth - 120}, {svgHeight - 52})">
          <rect width="116" height="48" rx="4" fill="var(--dark)" opacity="0.75" />
          <!-- Movement -->
          <line x1="8" y1="14" x2="36" y2="14" stroke="var(--warm-gray)" stroke-width="1.5" opacity="0.7" />
          <text x="42" y="18" font-size="9" font-family="var(--font-body)" fill="var(--text-dim)">movement</text>
          <!-- Cue -->
          <line x1="8" y1="32" x2="36" y2="32" stroke="var(--parchment-dark)" stroke-width="1.5" stroke-dasharray="5 3" opacity="0.7" />
          <text x="42" y="36" font-size="9" font-family="var(--font-body)" fill="var(--text-dim)">cue</text>
        </g>
      </svg>

      <!-- Room nodes -->
      {#each rooms as room (room.name)}
        {#if positions[room.name]}
          {@const objCount = roomObjectCounts[room.name] ?? 0}
          {@const noLook = roomsWithoutLook.has(room.name)}
          <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
          <div
            class="room-node"
            class:start-room={room.name === startRoom}
            class:no-look={noLook}
            class:dragging={dragging === room.name}
            role="button"
            tabindex="0"
            aria-label="Room: {room.name}. Double-click to open."
            style="left: {positions[room.name].x}px; top: {positions[room.name].y}px; width: {NODE_W}px; height: {NODE_H}px;"
            onmousedown={(e) => startDrag(room.name, e)}
            ondblclick={() => handleDoubleClick(room.name)}
            onkeydown={(e) => handleKeydown(room.name, e)}
          >
            <span class="room-label">
              {#if room.name === startRoom}<span class="star">★</span>{/if}{room.name.replace(/_/g, ' ')}
            </span>
            <span class="room-obj-count">{objCount} {objCount === 1 ? 'object' : 'objects'}</span>
          </div>
        {/if}
      {/each}

      {#if rooms.length === 0}
        <div class="empty-state">
          <p>No rooms yet — add rooms in the sidebar to see them here.</p>
        </div>
      {/if}
    </div>
  {:else}
    <PuzzleFlow />
  {/if}
</div>

<style>
  .mapview-wrapper {
    display: flex;
    flex-direction: column;
    width: 100%;
    height: 100%;
    overflow: hidden;
  }

  /* ── Sub-tab bar ───────────────────────────────────────── */
  .tab-bar {
    display: flex;
    gap: 2px;
    padding: 6px 8px 0;
    background-color: var(--dark-warm);
    border-bottom: 1px solid var(--warm-gray);
    flex-shrink: 0;
  }

  .tab-btn {
    font-family: var(--font-title);
    font-size: 0.72rem;
    font-weight: 700;
    letter-spacing: 0.06em;
    text-transform: uppercase;
    color: var(--text-dim);
    background: none;
    border: none;
    border-radius: 3px 3px 0 0;
    padding: 5px 14px;
    cursor: pointer;
    transition: color 0.15s, background-color 0.15s;
  }

  .tab-btn:hover {
    color: var(--parchment-dark);
    background-color: var(--mid-dark);
  }

  .tab-btn.active {
    color: var(--gold);
    background-color: var(--dark);
    border: 1px solid var(--warm-gray);
    border-bottom: 1px solid var(--dark);
    margin-bottom: -1px;
  }

  /* ── Map container ─────────────────────────────────────── */
  .map-container {
    position: relative;
    flex: 1;
    width: 100%;
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

  /* ── Room nodes ────────────────────────────────────────── */
  .room-node {
    position: absolute;
    background-color: var(--mid-dark);
    border: 2px solid var(--warm-gray);
    border-radius: 8px;
    cursor: grab;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    padding: 0 12px;
    gap: 3px;
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

  .room-node.no-look {
    border-color: var(--amber);
    border-style: dotted;
  }

  /* start-room overrides no-look border color but keeps dotted if both apply */
  .room-node.start-room.no-look {
    border-color: var(--gold);
    border-style: dotted;
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

  .star {
    color: var(--gold);
    margin-right: 3px;
  }

  .room-obj-count {
    font-size: 0.6rem;
    color: var(--text-dim);
    font-family: var(--font-body);
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
