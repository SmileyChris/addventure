<script lang="ts">
  import { store } from '../lib/store.svelte';
  import { classifyArrow } from '../lib/helpers';
  import type { Arrow, Interaction } from '../lib/types';

  // Node dimensions
  const NODE_W = 130;
  const NODE_H = 36;
  const COL_GAP = 60; // horizontal gap between columns
  const ROW_GAP = 24; // vertical gap between nodes in same column
  const GROUP_GAP = 48; // vertical gap between object groups
  const PADDING = { x: 20, y: 20 };

  // ── Data model ──────────────────────────────────────────

  interface TransitionEdge {
    from: string; // state name (e.g. "DOOR" or "DOOR__OPEN")
    to: string; // state name or "trash" / "player"
    verb: string;
    target: string; // the target in the interaction (could be the subject)
  }

  interface ObjectGroup {
    base: string;
    room: string;
    states: string[]; // all state node IDs (base + variants)
    edges: TransitionEdge[];
    // layout columns: column index → state names
    columns: string[][];
  }

  // ── Compute object groups from game data ────────────────

  const objectGroups = $derived.by((): ObjectGroup[] => {
    const game = store.game;
    if (!game) return [];

    // Collect all transitions from interactions
    // Key: base object name (before __)
    const groupMap = new Map<
      string,
      { room: string; states: Set<string>; edges: TransitionEdge[] }
    >();

    function ensureGroup(base: string, room: string) {
      if (!groupMap.has(base)) {
        groupMap.set(base, { room, states: new Set([base]), edges: [] });
      }
      // Add base state always
      groupMap.get(base)!.states.add(base);
    }

    function addState(base: string, stateName: string, room: string) {
      ensureGroup(base, room);
      groupMap.get(base)!.states.add(stateName);
    }

    for (const interaction of game.interactions) {
      const verb = interaction.verb;
      const allArrows = [...interaction.arrows, ...interaction.sealedArrows];

      for (const arrow of allArrows) {
        const type = classifyArrow(arrow);

        if (type === 'transform') {
          // subject → subject__STATE or STATE__X → STATE__Y
          const subjectBase = arrow.subject.split('__')[0];
          const destBase = arrow.destination.split('__')[0];
          // Only track if they share a base name
          if (subjectBase === destBase) {
            const room = interaction.room;
            addState(subjectBase, arrow.subject, room);
            addState(subjectBase, arrow.destination, room);
            groupMap.get(subjectBase)!.edges.push({
              from: arrow.subject,
              to: arrow.destination,
              verb,
              target: arrow.subject,
            });
          }
        } else if (type === 'destroy') {
          const base = arrow.subject.split('__')[0];
          // Only add if subject is an actual object (not 'player', 'room', etc.)
          if (
            base &&
            base !== 'player' &&
            base !== 'room' &&
            base !== 'trash' &&
            !base.startsWith('>')
          ) {
            const room = interaction.room;
            addState(base, arrow.subject, room);
            groupMap.get(base)!.edges.push({
              from: arrow.subject,
              to: 'trash',
              verb,
              target: arrow.subject,
            });
          }
        } else if (type === 'pickup') {
          const base = arrow.subject.split('__')[0];
          if (
            base &&
            base !== 'player' &&
            base !== 'room' &&
            base !== 'trash' &&
            !base.startsWith('>')
          ) {
            const room = interaction.room;
            addState(base, arrow.subject, room);
            groupMap.get(base)!.edges.push({
              from: arrow.subject,
              to: 'player',
              verb,
              target: arrow.subject,
            });
          }
        } else if (type === 'reveal') {
          // subject appears in room — mark as "room" terminal if not yet in game
          const base = arrow.subject.split('__')[0];
          if (
            base &&
            base !== 'player' &&
            base !== 'room' &&
            base !== 'trash' &&
            !base.startsWith('>')
          ) {
            const room = interaction.room;
            addState(base, arrow.subject, room);
            groupMap.get(base)!.edges.push({
              from: 'room',
              to: arrow.subject,
              verb,
              target: arrow.subject,
            });
          }
        }
      }
    }

    // Filter groups: only show those with actual state transitions (edges)
    const groups: ObjectGroup[] = [];

    for (const [base, data] of groupMap.entries()) {
      if (data.edges.length === 0) continue;

      const states = Array.from(data.states);
      const edges = data.edges;

      // ── Auto-layout: BFS column assignment ──────────────
      // Column 0 = base state (or states with no incoming edges)
      const incoming = new Set(edges.map((e) => e.to));
      const outgoing = new Set(edges.map((e) => e.from));

      // Roots = states in the group that have no incoming transitions
      const roots = states.filter((s) => !incoming.has(s) && outgoing.has(s));
      // If no clear root, use base name
      const startNodes = roots.length > 0 ? roots : [base];

      const colOf = new Map<string, number>();
      const queue: string[] = [...startNodes];
      startNodes.forEach((s) => colOf.set(s, 0));

      // BFS
      while (queue.length > 0) {
        const curr = queue.shift()!;
        const currCol = colOf.get(curr) ?? 0;
        for (const edge of edges) {
          if (edge.from !== curr) continue;
          const dest = edge.to;
          if (dest === 'trash' || dest === 'player' || dest === 'room') continue;
          if (!colOf.has(dest) || colOf.get(dest)! < currCol + 1) {
            colOf.set(dest, currCol + 1);
            if (!colOf.has(dest)) queue.push(dest);
            else queue.push(dest); // re-push to propagate
          }
        }
      }

      // Terminal nodes — assign to the max column + 1
      const maxCol = colOf.size > 0 ? Math.max(...colOf.values()) : 0;
      const terminalCol = maxCol + 1;

      // Assign any unvisited states
      for (const s of states) {
        if (!colOf.has(s)) colOf.set(s, 0);
      }

      // Build columns array
      const numCols = terminalCol + 1;
      const columns: string[][] = Array.from({ length: numCols }, () => []);
      for (const [s, c] of colOf.entries()) {
        columns[c].push(s);
      }

      // Add terminal columns for trash/player if referenced
      const hasTerm = (t: string) => edges.some((e) => e.to === t);
      if (hasTerm('trash')) columns[terminalCol].push('trash');
      if (hasTerm('player')) columns[terminalCol].push('player');
      if (hasTerm('room')) columns[0].unshift('room');

      // Remove empty columns
      const nonEmptyCols = columns.filter((c) => c.length > 0);

      groups.push({
        base,
        room: data.room,
        states,
        edges,
        columns: nonEmptyCols,
      });
    }

    return groups;
  });

  // ── Layout calculation ────────────────────────────────────

  interface LayoutNode {
    id: string;
    x: number;
    y: number;
    type: 'base' | 'state' | 'trash' | 'player' | 'room';
  }

  interface LayoutGroup {
    group: ObjectGroup;
    nodes: Map<string, LayoutNode>;
    totalHeight: number;
    totalWidth: number;
  }

  function layoutGroup(group: ObjectGroup, offsetY: number): LayoutGroup {
    const nodes = new Map<string, LayoutNode>();

    let totalWidth = 0;
    let maxColHeight = 0;

    for (let ci = 0; ci < group.columns.length; ci++) {
      const col = group.columns[ci];
      const colX = PADDING.x + ci * (NODE_W + COL_GAP);
      totalWidth = Math.max(totalWidth, colX + NODE_W);

      for (let ri = 0; ri < col.length; ri++) {
        const id = col[ri];
        const y = PADDING.y + offsetY + ri * (NODE_H + ROW_GAP);
        const x = colX;

        let type: LayoutNode['type'] = 'state';
        if (id === group.base) type = 'base';
        else if (id === 'trash') type = 'trash';
        else if (id === 'player') type = 'player';
        else if (id === 'room') type = 'room';

        nodes.set(id, { id, x, y, type });
        maxColHeight = Math.max(maxColHeight, y + NODE_H);
      }
    }

    return {
      group,
      nodes,
      totalHeight: maxColHeight - offsetY - PADDING.y,
      totalWidth,
    };
  }

  const layouts = $derived.by(() => {
    let offsetY = 0;
    const result: LayoutGroup[] = [];

    for (const group of objectGroups) {
      const layout = layoutGroup(group, offsetY);
      result.push(layout);
      offsetY += layout.totalHeight + GROUP_GAP;
    }

    return result;
  });

  const svgWidth = $derived.by(() => {
    let max = 400;
    for (const layout of layouts) {
      max = Math.max(max, layout.totalWidth + PADDING.x);
    }
    return max;
  });

  const svgHeight = $derived.by(() => {
    let max = 200;
    for (const layout of layouts) {
      for (const node of layout.nodes.values()) {
        max = Math.max(max, node.y + NODE_H + PADDING.y);
      }
    }
    return max;
  });

  // ── Edge path calculation ─────────────────────────────────

  function edgePath(
    nodes: Map<string, LayoutNode>,
    from: string,
    to: string,
  ): string | null {
    const a = nodes.get(from);
    const b = nodes.get(to);
    if (!a || !b) return null;

    const x1 = a.x + NODE_W;
    const y1 = a.y + NODE_H / 2;
    const x2 = b.x;
    const y2 = b.y + NODE_H / 2;

    // Simple cubic bezier
    const cx1 = x1 + (x2 - x1) * 0.5;
    const cy1 = y1;
    const cx2 = x1 + (x2 - x1) * 0.5;
    const cy2 = y2;

    return `M ${x1} ${y1} C ${cx1} ${cy1}, ${cx2} ${cy2}, ${x2} ${y2}`;
  }

  function edgeMidpoint(
    nodes: Map<string, LayoutNode>,
    from: string,
    to: string,
  ): { mx: number; my: number } | null {
    const a = nodes.get(from);
    const b = nodes.get(to);
    if (!a || !b) return null;
    return {
      mx: (a.x + NODE_W + b.x) / 2,
      my: (a.y + b.y) / 2 + NODE_H / 2,
    };
  }

  // ── Interaction ───────────────────────────────────────────

  function handleNodeClick(group: ObjectGroup, nodeId: string) {
    // Navigate to the room containing this object
    if (group.room) {
      store.showRoom(group.room);
    }
  }

  // ── State label formatting ────────────────────────────────

  function stateLabel(id: string): string {
    if (id === 'trash') return '✕ trash';
    if (id === 'player') return '↑ inventory';
    if (id === 'room') return '· room';
    // Replace __ with › for readability
    return id.replace('__', ' › ');
  }

  function verbEdgeLabel(edge: TransitionEdge): string {
    return edge.verb.split('__')[0];
  }
</script>

<div class="puzzle-flow">
  {#if objectGroups.length === 0}
    <div class="empty-state">
      <p>No state transitions found.</p>
      <p class="hint">Add arrows like <code>- DOOR → DOOR__OPEN</code> in your room interactions to see the puzzle flow here.</p>
    </div>
  {:else}
    <div class="flow-scroll">
      <svg
        width={svgWidth}
        height={svgHeight}
        aria-label="Puzzle state flow diagram"
      >
        <defs>
          <marker
            id="pf-arrow"
            markerWidth="7"
            markerHeight="5"
            refX="7"
            refY="2.5"
            orient="auto"
          >
            <polygon points="0 0, 7 2.5, 0 5" fill="var(--warm-gray)" />
          </marker>
          <marker
            id="pf-arrow-trash"
            markerWidth="7"
            markerHeight="5"
            refX="7"
            refY="2.5"
            orient="auto"
          >
            <polygon points="0 0, 7 2.5, 0 5" fill="var(--red-ink)" />
          </marker>
          <marker
            id="pf-arrow-player"
            markerWidth="7"
            markerHeight="5"
            refX="7"
            refY="2.5"
            orient="auto"
          >
            <polygon points="0 0, 7 2.5, 0 5" fill="var(--amber)" />
          </marker>
        </defs>

        {#each layouts as layout (layout.group.base + layout.group.room)}
          <!-- Group header -->
          {@const headerY = (() => {
            let minY = Infinity;
            for (const n of layout.nodes.values()) minY = Math.min(minY, n.y);
            return minY;
          })()}
          <text
            x={PADDING.x}
            y={headerY - 8}
            font-family="var(--font-mono)"
            font-size="10"
            font-weight="bold"
            fill="var(--parchment-dark)"
          >{layout.group.base} <tspan fill="var(--text-dim)" font-weight="normal">· {layout.group.room.replace(/_/g, ' ')}</tspan></text>

          <!-- Edges -->
          {#each layout.group.edges as edge, ei}
            {@const path = edgePath(layout.nodes, edge.from, edge.to)}
            {@const mid = edgeMidpoint(layout.nodes, edge.from, edge.to)}
            {@const isTrash = edge.to === 'trash'}
            {@const isPlayer = edge.to === 'player'}
            {@const label = verbEdgeLabel(edge)}
            {@const labelLen = label.length * 5 + 8}
            {#if path}
              <path
                d={path}
                fill="none"
                stroke={isTrash ? 'var(--red-ink)' : isPlayer ? 'var(--amber)' : 'var(--warm-gray)'}
                stroke-width="1.5"
                opacity="0.7"
                marker-end={isTrash
                  ? 'url(#pf-arrow-trash)'
                  : isPlayer
                    ? 'url(#pf-arrow-player)'
                    : 'url(#pf-arrow)'}
              />
              {#if mid && label}
                <rect
                  x={mid.mx - labelLen / 2}
                  y={mid.my - 8}
                  width={labelLen}
                  height={13}
                  rx="2"
                  fill="var(--dark)"
                  opacity="0.9"
                />
                <text
                  x={mid.mx}
                  y={mid.my + 3}
                  text-anchor="middle"
                  font-family="var(--font-mono)"
                  font-size="8"
                  fill={isTrash ? 'var(--red-ink)' : isPlayer ? 'var(--amber)' : 'var(--text-mid)'}
                >{label}</text>
              {/if}
            {/if}
          {/each}

          <!-- Nodes -->
          {#each [...layout.nodes.values()] as node (node.id)}
            {@const isBase = node.type === 'base'}
            {@const isTrash = node.type === 'trash'}
            {@const isPlayer = node.type === 'player'}
            {@const isRoomNode = node.type === 'room'}

            <!-- svelte-ignore a11y_no_noninteractive_element_interactions -->
            <!-- svelte-ignore a11y_no_noninteractive_tabindex -->
            <g
              class="state-node"
              class:clickable={!isTrash && !isPlayer && !isRoomNode}
              transform="translate({node.x}, {node.y})"
              role={(!isTrash && !isPlayer && !isRoomNode) ? 'button' : undefined}
              tabindex={(!isTrash && !isPlayer && !isRoomNode) ? 0 : undefined}
              aria-label={(!isTrash && !isPlayer && !isRoomNode)
                ? `State: ${node.id} — click to navigate`
                : undefined}
              onclick={() => {
                if (!isTrash && !isPlayer && !isRoomNode) {
                  handleNodeClick(layout.group, node.id);
                }
              }}
              onkeydown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  if (!isTrash && !isPlayer && !isRoomNode) {
                    handleNodeClick(layout.group, node.id);
                  }
                }
              }}
            >
              <rect
                width={NODE_W}
                height={NODE_H}
                rx="5"
                fill="var(--mid-dark)"
                stroke={isBase
                  ? 'var(--parchment-dark)'
                  : isTrash
                    ? 'var(--red-ink)'
                    : isPlayer
                      ? 'var(--amber)'
                      : isRoomNode
                        ? 'var(--green-ink)'
                        : 'var(--warm-gray)'}
                stroke-width={isBase ? 1.5 : 1}
                stroke-dasharray={isTrash ? '4 2' : undefined}
              />
              <text
                x={NODE_W / 2}
                y={NODE_H / 2 + 4}
                text-anchor="middle"
                font-family="var(--font-mono)"
                font-size="9"
                fill={isBase
                  ? 'var(--parchment-light)'
                  : isTrash
                    ? 'var(--red-ink)'
                    : isPlayer
                      ? 'var(--amber)'
                      : isRoomNode
                        ? 'var(--green-ink)'
                        : 'var(--text-mid)'}
              >{stateLabel(node.id)}</text>
            </g>
          {/each}
        {/each}
      </svg>
    </div>
  {/if}
</div>

<style>
  .puzzle-flow {
    flex: 1;
    width: 100%;
    height: 100%;
    background-color: var(--dark);
    overflow: hidden;
    display: flex;
    flex-direction: column;
  }

  .flow-scroll {
    flex: 1;
    overflow: auto;
    padding: 12px;
  }

  .state-node {
    cursor: default;
  }

  .state-node.clickable {
    cursor: pointer;
  }

  .state-node.clickable:hover rect {
    stroke: var(--parchment-dark);
  }

  .state-node:focus-visible rect {
    stroke: var(--gold);
    stroke-width: 2;
  }

  .empty-state {
    flex: 1;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    gap: 8px;
    color: var(--text-dim);
    font-style: italic;
    padding: 40px;
    text-align: center;
  }

  .empty-state .hint {
    font-size: 0.8rem;
    max-width: 380px;
  }

  .empty-state code {
    font-family: var(--font-mono);
    font-size: 0.75rem;
    color: var(--parchment-dark);
    background: var(--mid-dark);
    padding: 1px 5px;
    border-radius: 3px;
    font-style: normal;
  }
</style>
