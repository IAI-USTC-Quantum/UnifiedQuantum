import { useMemo, useState, type ReactNode } from "react";
import * as d3 from "d3";

export interface TopoNode {
  id: number | string;
  available?: boolean;
  t1?: number | null;
  t2?: number | null;
  freq?: number | null;
  single_gate_fidelity?: number | null;
  avg_readout_fidelity?: number | null;
  readout_fidelity_0?: number | null;
  readout_fidelity_1?: number | null;
}

export interface TopoEdge {
  u: number;
  v: number;
  fidelity?: number | null;
  gates?: { gate: string; fidelity?: number | null }[];
}

interface ChipTopologyProps {
  nodes: TopoNode[];
  edges: TopoEdge[];
  fidelity?: { avg_1q?: number | null; avg_2q?: number | null };
  width?: number | string;
  height?: number;
  compact?: boolean;
}

interface PositionedNode extends TopoNode {
  numericId: number;
  x: number;
  y: number;
}

const VIEWBOX_WIDTH = 640;
const GRID_RELAX_STEPS = 5;
const COLOR_STOP_ORANGE = 0.45;
const COLOR_STOP_GREEN = 0.78;

interface FidelityDomain {
  min: number;
  max: number;
}

function toNumericId(id: number | string): number {
  const parsed = Number(id);
  return Number.isFinite(parsed) ? parsed : 0;
}

function fmtPercent(value: number | null | undefined): string {
  return value == null ? "N/A" : `${(value * 100).toFixed(2)}%`;
}

function fmtTime(value: number | null | undefined): string {
  if (value == null) return "N/A";
  if (value >= 1000) return `${(value / 1000).toFixed(2)} ms`;
  return `${value.toFixed(2)} us`;
}

function finiteFidelity(value: number | null | undefined): number | null {
  if (value == null) return null;
  const parsed = Number(value);
  if (!Number.isFinite(parsed)) return null;
  return Math.max(0, Math.min(1, parsed));
}

function normalizeFidelity(value: number, domain: FidelityDomain): number {
  if (domain.max <= domain.min) return 1;
  return Math.max(0, Math.min(1, (value - domain.min) / (domain.max - domain.min)));
}

function fidelityColor(value: number | null | undefined, domain: FidelityDomain | null): string {
  const finite = finiteFidelity(value);
  if (finite == null || domain == null) return "#536072";
  const normalized = normalizeFidelity(finite, domain);
  if (normalized < COLOR_STOP_ORANGE) {
    return d3.interpolateRgb("#ef4444", "#f59e0b")(normalized / COLOR_STOP_ORANGE);
  }
  if (normalized < COLOR_STOP_GREEN) {
    return d3.interpolateRgb("#f59e0b", "#10b981")((normalized - COLOR_STOP_ORANGE) / (COLOR_STOP_GREEN - COLOR_STOP_ORANGE));
  }
  return d3.interpolateRgb("#10b981", "#00b4d8")((normalized - COLOR_STOP_GREEN) / (1 - COLOR_STOP_GREEN));
}

function displayedNodeFidelity(node: TopoNode, fallback1q: number | null | undefined): number | null {
  return finiteFidelity(node.single_gate_fidelity ?? fallback1q);
}

function displayedEdgeFidelity(edge: TopoEdge, fallback2q: number | null | undefined): number | null {
  return finiteFidelity(edge.fidelity ?? fallback2q);
}

function fidelityDomain(
  nodes: TopoNode[],
  edges: TopoEdge[],
  fallback1q: number | null | undefined,
  fallback2q: number | null | undefined,
): FidelityDomain | null {
  const values: number[] = [];
  for (const node of nodes) {
    const value = displayedNodeFidelity(node, fallback1q);
    if (value != null) values.push(value);
  }
  for (const edge of edges) {
    const value = displayedEdgeFidelity(edge, fallback2q);
    if (value != null) values.push(value);
  }
  if (values.length === 0) return null;
  return {
    min: Math.min(...values),
    max: Math.max(...values),
  };
}

function gridLayout(nodes: TopoNode[], width: number, height: number): PositionedNode[] {
  if (nodes.length === 0) return [];
  const aspect = width / Math.max(height, 1);
  const cols = Math.max(1, Math.ceil(Math.sqrt(nodes.length * aspect)));
  const rows = Math.max(1, Math.ceil(nodes.length / cols));
  const margin = nodes.length > 80 ? 24 : 42;
  const usableW = Math.max(1, width - margin * 2);
  const usableH = Math.max(1, height - margin * 2);

  return nodes
    .map((node) => ({ ...node, numericId: toNumericId(node.id) }))
    .sort((a, b) => a.numericId - b.numericId)
    .map((node, index) => {
      const col = index % cols;
      const row = Math.floor(index / cols);
      return {
        ...node,
        x: cols === 1 ? width / 2 : margin + (col * usableW) / (cols - 1),
        y: rows === 1 ? height / 2 : margin + (row * usableH) / (rows - 1),
      };
    });
}

function buildAdjacency(nodes: TopoNode[], edges: TopoEdge[]): Map<number, number[]> {
  const ids = new Set(nodes.map((node) => toNumericId(node.id)));
  const adj = new Map<number, Set<number>>();
  for (const id of ids) adj.set(id, new Set());
  for (const edge of edges) {
    if (!ids.has(edge.u) || !ids.has(edge.v) || edge.u === edge.v) continue;
    adj.get(edge.u)?.add(edge.v);
    adj.get(edge.v)?.add(edge.u);
  }
  return new Map([...adj.entries()].map(([id, neighbors]) => [id, [...neighbors].sort((a, b) => a - b)]));
}

function isPathLike(nodes: TopoNode[], edges: TopoEdge[]): boolean {
  if (nodes.length < 2 || edges.length === 0) return false;
  const adj = buildAdjacency(nodes, edges);
  const connectedIds = [...adj.entries()].filter(([, neighbors]) => neighbors.length > 0);
  if (connectedIds.length !== nodes.length) return false;
  const degrees = connectedIds.map(([, neighbors]) => neighbors.length);
  const endpointCount = degrees.filter((degree) => degree === 1).length;
  const edgeKeys = new Set(
    edges
      .filter((edge) => edge.u !== edge.v)
      .map((edge) => `${Math.min(edge.u, edge.v)}-${Math.max(edge.u, edge.v)}`),
  );
  return edgeKeys.size === nodes.length - 1
    && endpointCount === 2
    && degrees.every((degree) => degree <= 2);
}

function orderedPathNodes(nodes: TopoNode[], edges: TopoEdge[]): TopoNode[] {
  const byId = new Map(nodes.map((node) => [toNumericId(node.id), node]));
  const adj = buildAdjacency(nodes, edges);
  const visited = new Set<number>();
  const result: TopoNode[] = [];
  const starts = [...adj.entries()]
    .filter(([, neighbors]) => neighbors.length <= 1)
    .map(([id]) => id)
    .sort((a, b) => a - b);
  const allStarts = starts.length > 0 ? starts : [...byId.keys()].sort((a, b) => a - b);

  for (const start of allStarts) {
    if (visited.has(start)) continue;
    let current: number | undefined = start;
    let previous: number | undefined;
    while (current !== undefined && !visited.has(current)) {
      visited.add(current);
      const node = byId.get(current);
      if (node) result.push(node);
      const nextNode: number | undefined = (adj.get(current) ?? []).find((neighbor) => neighbor !== previous && !visited.has(neighbor));
      previous = current;
      current = nextNode;
    }
  }

  for (const node of nodes) {
    if (!visited.has(toNumericId(node.id))) result.push(node);
  }
  return result;
}

function snakeGridLayout(nodes: TopoNode[], edges: TopoEdge[], width: number, height: number): PositionedNode[] {
  const ordered = orderedPathNodes(nodes, edges);
  const aspect = width / Math.max(height, 1);
  const cols = Math.max(1, Math.ceil(Math.sqrt(ordered.length * aspect)));
  const rows = Math.max(1, Math.ceil(ordered.length / cols));
  const margin = ordered.length > 80 ? 24 : 42;
  const usableW = Math.max(1, width - margin * 2);
  const usableH = Math.max(1, height - margin * 2);

  return ordered.map((node, index) => {
    const row = Math.floor(index / cols);
    const rawCol = index % cols;
    const col = row % 2 === 0 ? rawCol : cols - 1 - rawCol;
    return {
      ...node,
      numericId: toNumericId(node.id),
      x: cols === 1 ? width / 2 : margin + (col * usableW) / (cols - 1),
      y: rows === 1 ? height / 2 : margin + (row * usableH) / (rows - 1),
    };
  });
}

interface Slot {
  index: number;
  col: number;
  row: number;
  x: number;
  y: number;
}

function makeSlots(count: number, width: number, height: number): Slot[] {
  const aspect = width / Math.max(height, 1);
  const cols = count <= 6
    ? Math.max(1, Math.ceil(Math.sqrt(count)))
    : Math.max(1, Math.ceil(Math.sqrt(count * aspect)));
  const rows = Math.max(1, Math.ceil(count / cols));
  const margin = count > 80 ? 24 : 42;
  const usableW = Math.max(1, width - margin * 2);
  const usableH = Math.max(1, height - margin * 2);
  const slots: Slot[] = [];
  for (let row = 0; row < rows; row += 1) {
    for (let col = 0; col < cols; col += 1) {
      slots.push({
        index: slots.length,
        col,
        row,
        x: cols === 1 ? width / 2 : margin + (col * usableW) / (cols - 1),
        y: rows === 1 ? height / 2 : margin + (row * usableH) / (rows - 1),
      });
    }
  }
  return slots;
}

function edgeCost(edges: TopoEdge[], assignment: Map<number, Slot>): number {
  let cost = 0;
  for (const edge of edges) {
    const a = assignment.get(edge.u);
    const b = assignment.get(edge.v);
    if (!a || !b) continue;
    const dx = Math.abs(a.col - b.col);
    const dy = Math.abs(a.row - b.row);
    cost += dx * dx + dy * dy + 0.35 * (dx + dy);
  }
  return cost;
}

function displacementCost(
  nodes: PositionedNode[],
  assignment: Map<number, Slot>,
  normalized: Map<number, { col: number; row: number }>,
): number {
  let cost = 0;
  for (const node of nodes) {
    const slot = assignment.get(node.numericId);
    const target = normalized.get(node.numericId);
    if (!slot || !target) continue;
    const dx = slot.col - target.col;
    const dy = slot.row - target.row;
    cost += 0.18 * (dx * dx + dy * dy);
  }
  return cost;
}

function snapToGrid(nodes: PositionedNode[], edges: TopoEdge[], width: number, height: number): PositionedNode[] {
  if (nodes.length === 0) return [];
  const slots = makeSlots(nodes.length, width, height);
  const minX = Math.min(...nodes.map((node) => node.x));
  const maxX = Math.max(...nodes.map((node) => node.x));
  const minY = Math.min(...nodes.map((node) => node.y));
  const maxY = Math.max(...nodes.map((node) => node.y));
  const maxCol = Math.max(...slots.map((slot) => slot.col));
  const maxRow = Math.max(...slots.map((slot) => slot.row));
  const normalized = new Map<number, { col: number; row: number }>();
  for (const node of nodes) {
    normalized.set(node.numericId, {
      col: maxCol === 0 ? 0 : ((node.x - minX) / Math.max(1, maxX - minX)) * maxCol,
      row: maxRow === 0 ? 0 : ((node.y - minY) / Math.max(1, maxY - minY)) * maxRow,
    });
  }

  const pairs: { id: number; slot: Slot; dist: number }[] = [];
  for (const node of nodes) {
    const target = normalized.get(node.numericId)!;
    for (const slot of slots) {
      const dx = slot.col - target.col;
      const dy = slot.row - target.row;
      pairs.push({ id: node.numericId, slot, dist: dx * dx + dy * dy });
    }
  }
  pairs.sort((a, b) => a.dist - b.dist);

  const assignment = new Map<number, Slot>();
  const usedSlots = new Set<number>();
  for (const pair of pairs) {
    if (assignment.has(pair.id) || usedSlots.has(pair.slot.index)) continue;
    assignment.set(pair.id, pair.slot);
    usedSlots.add(pair.slot.index);
    if (assignment.size === nodes.length) break;
  }

  let currentCost = edgeCost(edges, assignment) + displacementCost(nodes, assignment, normalized);
  const ids = nodes.map((node) => node.numericId);
  for (let step = 0; step < GRID_RELAX_STEPS; step += 1) {
    let improved = false;
    for (let i = 0; i < ids.length; i += 1) {
      for (let j = i + 1; j < ids.length; j += 1) {
        const a = ids[i];
        const b = ids[j];
        const slotA = assignment.get(a);
        const slotB = assignment.get(b);
        if (!slotA || !slotB) continue;
        assignment.set(a, slotB);
        assignment.set(b, slotA);
        const nextCost = edgeCost(edges, assignment) + displacementCost(nodes, assignment, normalized);
        if (nextCost + 0.001 < currentCost) {
          currentCost = nextCost;
          improved = true;
        } else {
          assignment.set(a, slotA);
          assignment.set(b, slotB);
        }
      }
    }
    if (!improved) break;
  }

  return nodes.map((node) => {
    const slot = assignment.get(node.numericId)!;
    return { ...node, x: slot.x, y: slot.y };
  });
}

function forceGridLayout(nodes: TopoNode[], edges: TopoEdge[], width: number, height: number): PositionedNode[] {
  const simNodes: PositionedNode[] = nodes.map((node) => ({
    ...node,
    numericId: toNumericId(node.id),
    x: width / 2,
    y: height / 2,
  }));
  const nodeIds = new Set(simNodes.map((node) => node.numericId));
  const simLinks = edges
    .filter((edge) => nodeIds.has(edge.u) && nodeIds.has(edge.v) && edge.u !== edge.v)
    .map((edge) => ({ source: edge.u, target: edge.v }));

  if (simLinks.length === 0) return gridLayout(nodes, width, height);

  const radius = nodes.length > 80 ? 8 : nodes.length > 32 ? 12 : 18;
  const simulation = d3
    .forceSimulation<PositionedNode>(simNodes)
    .force("link", d3.forceLink<PositionedNode, d3.SimulationLinkDatum<PositionedNode>>(simLinks).id((d) => d.numericId).distance(radius * 4))
    .force("charge", d3.forceManyBody<PositionedNode>().strength(nodes.length > 80 ? -35 : -120))
    .force("center", d3.forceCenter(width / 2, height / 2))
    .force("collision", d3.forceCollide<PositionedNode>(radius * 1.5))
    .stop();

  for (let i = 0; i < 220; i += 1) simulation.tick();

  const minX = Math.min(...simNodes.map((node) => node.x ?? 0));
  const maxX = Math.max(...simNodes.map((node) => node.x ?? 0));
  const minY = Math.min(...simNodes.map((node) => node.y ?? 0));
  const maxY = Math.max(...simNodes.map((node) => node.y ?? 0));
  const pad = 36;
  const scaleX = (width - pad * 2) / Math.max(1, maxX - minX);
  const scaleY = (height - pad * 2) / Math.max(1, maxY - minY);
  const scale = Math.min(scaleX, scaleY);

  const continuous = simNodes.map((node) => ({
    ...node,
    x: pad + ((node.x ?? width / 2) - minX) * scale,
    y: pad + ((node.y ?? height / 2) - minY) * scale,
  }));
  return snapToGrid(continuous, edges, width, height);
}

function nodeTooltip(node: TopoNode) {
  return (
    <div>
      <div className="tooltip-title">Qubit {node.id}</div>
      <div className="tooltip-row"><span>Status</span><span>{node.available === false ? "Unavailable" : "Available"}</span></div>
      <div className="tooltip-row"><span>1Q fidelity</span><span>{fmtPercent(node.single_gate_fidelity)}</span></div>
      <div className="tooltip-row"><span>Readout</span><span>{fmtPercent(node.avg_readout_fidelity)}</span></div>
      <div className="tooltip-row"><span>T1</span><span>{fmtTime(node.t1)}</span></div>
      <div className="tooltip-row"><span>T2</span><span>{fmtTime(node.t2)}</span></div>
    </div>
  );
}

function edgeTooltip(edge: TopoEdge, fallback2q: number | null | undefined) {
  const gates = edge.gates ?? [];
  return (
    <div>
      <div className="tooltip-title">Edge {edge.u} - {edge.v}</div>
      <div className="tooltip-row"><span>2Q fidelity</span><span>{fmtPercent(edge.fidelity ?? fallback2q)}</span></div>
      {gates.length > 0 && (
        <div style={{ marginTop: 6, display: "grid", gap: 2 }}>
          {gates.slice(0, 5).map((gate, index) => (
            <div key={`${gate.gate}-${index}`} className="tooltip-row">
              <span>{gate.gate}</span><span>{fmtPercent(gate.fidelity)}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

function FidelityLegend({ compact, domain }: { compact: boolean; domain: FidelityDomain }) {
  const labelValues = domain.max <= domain.min
    ? [domain.min, domain.max]
    : [
        domain.min,
        domain.min + (domain.max - domain.min) / 3,
        domain.min + ((domain.max - domain.min) * 2) / 3,
        domain.max,
      ];
  return (
    <div className={`fidelity-legend ${compact ? "compact" : ""}`} aria-label="Fidelity color scale">
      <div className="fidelity-legend-bar" />
      <div className="fidelity-legend-labels">
        {labelValues.map((value, index) => (
          <span key={`${value}-${index}`}>{fmtPercent(value)}</span>
        ))}
      </div>
    </div>
  );
}

export function ChipTopology({
  nodes,
  edges,
  fidelity,
  width = "100%",
  height = 280,
  compact = false,
}: ChipTopologyProps) {
  const [tooltip, setTooltip] = useState<{
    visible: boolean;
    x: number;
    y: number;
    content: ReactNode;
  }>({ visible: false, x: 0, y: 0, content: null });

  const layoutHeight = compact ? Math.min(height, 180) : height;
  const positions = useMemo(() => {
    const sortedNodes = [...nodes].sort((a, b) => toNumericId(a.id) - toNumericId(b.id));
    if (edges.length === 0 || sortedNodes.length > 180) {
      return gridLayout(sortedNodes, VIEWBOX_WIDTH, layoutHeight);
    }
    if (isPathLike(sortedNodes, edges)) {
      return snakeGridLayout(sortedNodes, edges, VIEWBOX_WIDTH, layoutHeight);
    }
    return forceGridLayout(sortedNodes, edges, VIEWBOX_WIDTH, layoutHeight);
  }, [nodes, edges, layoutHeight]);

  const positionMap = useMemo(() => {
    const map = new Map<number, PositionedNode>();
    for (const node of positions) map.set(node.numericId, node);
    return map;
  }, [positions]);

  const radius = compact
    ? positions.length > 80 ? 4 : positions.length > 32 ? 6 : 10
    : positions.length > 120 ? 5 : positions.length > 48 ? 8 : 13;

  const edgeStroke = compact ? 2.6 : 3.8;
  const edgeHitStroke = compact ? 12 : 16;
  const hasConnectivity = edges.length > 0;
  const colorDomain = useMemo(
    () => fidelityDomain(nodes, edges, fidelity?.avg_1q, fidelity?.avg_2q),
    [nodes, edges, fidelity?.avg_1q, fidelity?.avg_2q],
  );

  function moveTooltip(event: React.MouseEvent<SVGElement>) {
    const rect = event.currentTarget.ownerSVGElement?.getBoundingClientRect();
    if (!rect) return;
    setTooltip((current) => ({
      ...current,
      x: event.clientX - rect.left + 12,
      y: event.clientY - rect.top + 12,
    }));
  }

  function showEdgeTooltip(event: React.MouseEvent<SVGLineElement>, edge: TopoEdge) {
    setTooltip({
      visible: true,
      x: event.clientX,
      y: event.clientY,
      content: edgeTooltip(edge, fidelity?.avg_2q),
    });
    moveTooltip(event);
  }

  return (
    <div className="chip-topology" style={{ width }}>
      <div style={{ position: "relative", height: layoutHeight }}>
        <svg
          className="chip-svg"
          width={width}
          height={layoutHeight}
          viewBox={`0 0 ${VIEWBOX_WIDTH} ${layoutHeight}`}
          role="img"
          aria-label="Chip topology"
        >
          <rect x="0" y="0" width={VIEWBOX_WIDTH} height={layoutHeight} rx="10" fill="#0e1726" />

          {hasConnectivity && edges.map((edge, index) => {
            const source = positionMap.get(edge.u);
            const target = positionMap.get(edge.v);
            if (!source || !target) return null;
            return (
              <line
                key={`visible-${edge.u}-${edge.v}-${index}`}
                className="topo-edge"
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke={fidelityColor(displayedEdgeFidelity(edge, fidelity?.avg_2q), colorDomain)}
                strokeWidth={edgeStroke}
                strokeLinecap="round"
                opacity={0.9}
                pointerEvents="none"
              />
            );
          })}

          {hasConnectivity && edges.map((edge, index) => {
            const source = positionMap.get(edge.u);
            const target = positionMap.get(edge.v);
            if (!source || !target) return null;
            return (
              <line
                key={`hit-${edge.u}-${edge.v}-${index}`}
                x1={source.x}
                y1={source.y}
                x2={target.x}
                y2={target.y}
                stroke="transparent"
                strokeWidth={edgeHitStroke}
                strokeLinecap="round"
                pointerEvents="stroke"
                onMouseEnter={(event) => showEdgeTooltip(event, edge)}
                onMouseMove={moveTooltip}
                onMouseLeave={() => setTooltip((current) => ({ ...current, visible: false }))}
              />
            );
          })}

          {positions.map((node) => {
            const fill = node.available === false ? "#334155" : fidelityColor(displayedNodeFidelity(node, fidelity?.avg_1q), colorDomain);
            return (
              <g
                key={node.numericId}
                onMouseEnter={(event) => {
                  setTooltip({
                    visible: true,
                    x: event.clientX,
                    y: event.clientY,
                    content: nodeTooltip(node),
                  });
                  moveTooltip(event);
                }}
                onMouseMove={moveTooltip}
                onMouseLeave={() => setTooltip((current) => ({ ...current, visible: false }))}
              >
                <circle
                  cx={node.x}
                  cy={node.y}
                  r={radius}
                  fill={fill}
                  stroke={node.available === false ? "#64748b" : "#dbeafe"}
                  strokeWidth={compact ? 0.8 : 1.2}
                  opacity={node.available === false ? 0.55 : 0.96}
                />
                {positions.length <= 80 && (
                  <text
                    x={node.x}
                    y={node.y + 3}
                    textAnchor="middle"
                    fontSize={radius < 9 ? 7 : 9}
                    fontWeight={700}
                    fill="#07111f"
                    pointerEvents="none"
                  >
                    {node.id}
                  </text>
                )}
              </g>
            );
          })}

          {!hasConnectivity && nodes.length > 0 && (
            <text
              x={VIEWBOX_WIDTH - 16}
              y={layoutHeight - 14}
              textAnchor="end"
              fontSize="12"
              fill="#94a3b8"
            >
              calibration grid
            </text>
          )}
        </svg>

        {tooltip.visible && (
          <div className="tooltip" style={{ left: tooltip.x, top: tooltip.y }}>
            {tooltip.content}
          </div>
        )}
      </div>

      {colorDomain && (
        <FidelityLegend compact={compact} domain={colorDomain} />
      )}
    </div>
  );
}
