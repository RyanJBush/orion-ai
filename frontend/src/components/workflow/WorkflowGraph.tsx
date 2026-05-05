import type { ApiExecutionStep } from '../../services/api'

/** Status → fill colour mapping for graph nodes */
const STATUS_FILL: Record<string, string> = {
  completed: '#dcfce7',
  running: '#e0f2fe',
  failed: '#fee2e2',
  pending: '#f8fafc',
  paused: '#fef3c7',
  retrying: '#fef3c7',
  blocked: '#fde68a',
  canceled: '#fee2e2',
  queued: '#eef2ff',
  planning: '#f8fafc',
}

const STATUS_STROKE: Record<string, string> = {
  completed: '#16a34a',
  running: '#0369a1',
  failed: '#b91c1c',
  pending: '#94a3b8',
  paused: '#92400e',
  retrying: '#92400e',
  blocked: '#78350f',
  canceled: '#991b1b',
  queued: '#4338ca',
  planning: '#334155',
}

const NODE_WIDTH = 150
const NODE_HEIGHT = 56
const H_GAP = 40    // horizontal gap between columns
const V_GAP = 32    // vertical gap between rows in same column
const PADDING = 24

interface GraphNode {
  step: ApiExecutionStep
  col: number  // 0-indexed topological column
  row: number  // 0-indexed position within column
  x: number
  y: number
  cx: number  // centre x
  cy: number  // centre y
}

/**
 * Lay out steps in columns determined by the longest dependency chain depth.
 * Steps with no dependencies go in column 0; each step's column = max(dep columns) + 1.
 */
function layoutNodes(steps: ApiExecutionStep[]): { nodes: GraphNode[]; svgWidth: number; svgHeight: number } {
  if (steps.length === 0) return { nodes: [], svgWidth: 0, svgHeight: 0 }

  // Build column (depth) for each step
  const colByStepId: Record<string, number> = {}
  const sorted = [...steps].sort((a, b) => a.step_order - b.step_order)

  for (const step of sorted) {
    if (step.dependencies.length === 0) {
      colByStepId[step.step_id] = 0
    } else {
      const maxDepCol = Math.max(...step.dependencies.map((d) => colByStepId[d] ?? 0))
      colByStepId[step.step_id] = maxDepCol + 1
    }
  }

  // Group steps by column
  const columns: Record<number, ApiExecutionStep[]> = {}
  for (const step of sorted) {
    const col = colByStepId[step.step_id] ?? 0
    columns[col] = columns[col] ?? []
    columns[col].push(step)
  }

  const numCols = Math.max(...Object.keys(columns).map(Number)) + 1
  const maxRowsInAnyCol = Math.max(...Object.values(columns).map((c) => c.length))

  const svgWidth = PADDING * 2 + numCols * NODE_WIDTH + (numCols - 1) * H_GAP
  const svgHeight = PADDING * 2 + maxRowsInAnyCol * NODE_HEIGHT + (maxRowsInAnyCol - 1) * V_GAP

  const nodes: GraphNode[] = []
  for (const [colStr, colSteps] of Object.entries(columns)) {
    const col = Number(colStr)
    const colX = PADDING + col * (NODE_WIDTH + H_GAP)
    const colHeight = colSteps.length * NODE_HEIGHT + (colSteps.length - 1) * V_GAP
    const colTopOffset = (svgHeight - PADDING * 2 - colHeight) / 2 + PADDING

    colSteps.forEach((step, rowIdx) => {
      const x = colX
      const y = colTopOffset + rowIdx * (NODE_HEIGHT + V_GAP)
      nodes.push({
        step,
        col,
        row: rowIdx,
        x,
        y,
        cx: x + NODE_WIDTH / 2,
        cy: y + NODE_HEIGHT / 2,
      })
    })
  }

  return { nodes, svgWidth, svgHeight }
}

interface WorkflowGraphProps {
  steps: ApiExecutionStep[]
  selectedStepId: number | null
  onSelectStep: (stepId: number) => void
}

export function WorkflowGraph({ steps, selectedStepId, onSelectStep }: WorkflowGraphProps) {
  const { nodes, svgWidth, svgHeight } = layoutNodes(steps)

  // Build a lookup: step_id → node
  const nodeByStepId: Record<string, GraphNode> = {}
  for (const node of nodes) {
    nodeByStepId[node.step.step_id] = node
  }

  return (
    <div className="workflow-graph-container">
      <svg
        width={svgWidth}
        height={svgHeight}
        viewBox={`0 0 ${svgWidth} ${svgHeight}`}
        aria-label="Workflow execution graph"
        style={{ display: 'block', minWidth: svgWidth, overflow: 'visible' }}
      >
        <defs>
          <marker id="arrowhead" markerWidth="8" markerHeight="6" refX="8" refY="3" orient="auto">
            <polygon points="0 0, 8 3, 0 6" fill="#94a3b8" />
          </marker>
        </defs>

        {/* Edges — draw before nodes so nodes render on top */}
        {nodes.map((node) =>
          node.step.dependencies.map((depId) => {
            const depNode = nodeByStepId[depId]
            if (!depNode) return null
            // Connect right edge of dep node to left edge of current node
            const x1 = depNode.x + NODE_WIDTH
            const y1 = depNode.cy
            const x2 = node.x
            const y2 = node.cy
            // Cubic bezier for a smooth curve
            const mx = (x1 + x2) / 2
            return (
              <path
                key={`${depId}->${node.step.step_id}`}
                d={`M ${x1} ${y1} C ${mx} ${y1}, ${mx} ${y2}, ${x2} ${y2}`}
                fill="none"
                stroke="#94a3b8"
                strokeWidth="1.5"
                markerEnd="url(#arrowhead)"
              />
            )
          }),
        )}

        {/* Nodes */}
        {nodes.map((node) => {
          const fill = STATUS_FILL[node.step.status] ?? '#f8fafc'
          const stroke = STATUS_STROKE[node.step.status] ?? '#94a3b8'
          const isSelected = selectedStepId === node.step.id
          return (
            <g
              key={node.step.id}
              style={{ cursor: 'pointer' }}
              onClick={() => onSelectStep(node.step.id)}
              role="button"
              tabIndex={0}
              aria-label={`Step ${node.step.step_id}: ${node.step.action} — ${node.step.status}`}
              onKeyDown={(e) => e.key === 'Enter' && onSelectStep(node.step.id)}
            >
              <rect
                x={node.x}
                y={node.y}
                width={NODE_WIDTH}
                height={NODE_HEIGHT}
                rx={8}
                fill={fill}
                stroke={isSelected ? '#2563eb' : stroke}
                strokeWidth={isSelected ? 2.5 : 1.5}
                filter={isSelected ? 'drop-shadow(0 0 4px rgba(37,99,235,0.4))' : undefined}
              />
              {/* Step ID */}
              <text
                x={node.cx}
                y={node.y + 18}
                textAnchor="middle"
                fontSize={11}
                fontWeight="600"
                fill={STATUS_STROKE[node.step.status] ?? '#334155'}
              >
                {node.step.step_id}
              </text>
              {/* Action */}
              <text
                x={node.cx}
                y={node.y + 32}
                textAnchor="middle"
                fontSize={11}
                fill="#334155"
              >
                {node.step.action}
              </text>
              {/* Worker */}
              <text
                x={node.cx}
                y={node.y + 48}
                textAnchor="middle"
                fontSize={9.5}
                fill="#64748b"
              >
                {node.step.worker_name}
              </text>
            </g>
          )
        })}
      </svg>
    </div>
  )
}
