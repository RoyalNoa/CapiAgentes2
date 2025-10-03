const fs = require('fs');
const path = require('path');

const ROOT_DIR = path.resolve(__dirname, '..', '..');
const config = {
  width: 960,
  height: 540,
  hierarchicalSpacing: 220,
  nodeSpacing: 200,
  minSeparation: 0
};

const SYSTEM_SEQUENCE = [
  { id: 'start', name: 'Start', type: 'system', level: 0, radius: 80 },
  { id: 'intent', name: 'Intent', type: 'system', level: 1, radius: 80 },
  { id: 'reasoning', name: 'Reasoning', type: 'system', level: 2, radius: 80 },
  { id: 'router', name: 'Router', type: 'router', level: 3, radius: 72 },
  { id: 'assemble', name: 'Assemble', type: 'system', level: 4, radius: 80 },
  { id: 'finalize', name: 'Finalize', type: 'system', level: 5, radius: 80 }
];

const clamp = (value, min, max) => Math.min(max, Math.max(min, value));
const isFiniteNumber = value => typeof value === 'number' && Number.isFinite(value);

function loadAgentDefinitions() {
  const agentsPath = path.join(ROOT_DIR, 'Backend', 'ia_workspace', 'data', 'agents_registry.json');
  const raw = JSON.parse(fs.readFileSync(agentsPath, 'utf8'));
  return Object.values(raw ?? {}).map(entry => ({
    id: entry.agent_name ?? entry.name ?? entry.id ?? 'unknown',
    name: entry.display_name ?? entry.agent_name ?? entry.name ?? 'Agent',
    type: 'agent',
    enabled: entry.enabled !== false,
    status: (entry.status ?? 'idle').toLowerCase(),
    level: SYSTEM_SEQUENCE.length + 1,
    mass: 1,
    radius: 60,
    charge: 1,
    weight: 1
  }));
}

function buildNodeList() {
  const agents = loadAgentDefinitions();
  const systemNodes = SYSTEM_SEQUENCE.map(node => ({
    id: node.id,
    name: node.name,
    type: node.type,
    level: node.level,
    enabled: true,
    status: 'idle',
    mass: node.type === 'router' ? 3 : 2,
    radius: node.radius,
    charge: node.type === 'router' ? 2 : 1,
    weight: 1
  }));

  return [...systemNodes, ...agents];
}

function computeLayout(nodes) {
  const safeWidth = config.width > 0 ? config.width : 960;
  const safeHeight = config.height > 0 ? config.height : 540;
  const horizontalMargin = 120;
  const topRowY = safeHeight * 0.25;
  const bottomRowY = safeHeight * 0.7;
  const agentBaseline = safeHeight * 0.95;

  const systemNodes = nodes.filter(node => node.type !== 'agent');
  const agents = nodes.filter(node => node.type === 'agent');

  const topRowCount = Math.ceil(systemNodes.length / 2);
  const bottomRowCount = systemNodes.length - topRowCount;

  const topAreaWidth = safeWidth - horizontalMargin * 2;
  const bottomAreaWidth = safeWidth - horizontalMargin * 2;
  const topStep = topRowCount > 0 ? topAreaWidth / topRowCount : topAreaWidth;
  const bottomStep = bottomRowCount > 0 ? bottomAreaWidth / bottomRowCount : bottomAreaWidth;
  const agentRawWidth = safeWidth - horizontalMargin * 2;
  const agentPositions = [];
  if (agents.length === 1) {
    agentPositions.push(horizontalMargin + agentRawWidth / 2);
  } else if (agents.length === 2) {
    const edgeOffset = 0;
    agentPositions.push(horizontalMargin + edgeOffset);
    agentPositions.push(safeWidth - horizontalMargin - edgeOffset);
  } else if (agents.length > 2) {
    const agentStep = agentRawWidth / (agents.length - 1);
    for (let idx = 0; idx < agents.length; idx += 1) {
      agentPositions.push(horizontalMargin + idx * agentStep);
    }
  }

  let topIndex = 0;
  let bottomIndex = 0;
  const agentIndexMap = new Map();
  agents.forEach((node, idx) => agentIndexMap.set(node.id, idx));

  return nodes.map(node => {
    const computedRadius = node.radius ?? (node.type === 'router' ? 72 : node.type === 'system' ? 80 : 60);
    const safeRadius = Number.isFinite(computedRadius) ? computedRadius : 60;
    let x;
    let y;

    if (node.type === 'agent') {
      const agentIdx = agentIndexMap.get(node.id) ?? 0;
      const preset = agentPositions[agentIdx];
      if (preset !== undefined) {
        x = preset;
      } else {
        const fallbackStep = agentRawWidth / Math.max(agents.length, 1);
        x = horizontalMargin + (agentIdx + 0.5) * fallbackStep;
      }
      y = agentBaseline;
    } else {
      const useTopRow = topIndex < topRowCount;
      if (useTopRow) {
        const idx = topIndex;
        x = horizontalMargin + (topRowCount > 0 ? (idx + 0.5) * topStep : topAreaWidth / 2);
        y = topRowY;
        topIndex += 1;
      } else {
        const idx = bottomIndex;
        x = horizontalMargin + (bottomRowCount > 0 ? (idx + 0.5) * bottomStep : bottomAreaWidth / 2);
        y = bottomRowY;
        bottomIndex += 1;
      }
    }

    const constrainedX = clamp(x, safeRadius + 16, safeWidth - safeRadius - 16);
    const constrainedY = clamp(y, safeRadius + 16, safeHeight - safeRadius - 16);

    return {
      ...node,
      x: constrainedX,
      y: constrainedY,
    };
  });
}

function analyseLayout(nodes) {
  let minGap = Number.POSITIVE_INFINITY;
  const overlaps = [];
  for (let i = 0; i < nodes.length; i += 1) {
    for (let j = i + 1; j < nodes.length; j += 1) {
      const a = nodes[i];
      const b = nodes[j];
      if (!isFiniteNumber(a.x) || !isFiniteNumber(a.y) || !isFiniteNumber(b.x) || !isFiniteNumber(b.y)) {
        return { valid: false, reason: 'non-finite coordinate detected', pair: [a.id, b.id] };
      }
      const dx = a.x - b.x;
      const dy = a.y - b.y;
      const distance = Math.sqrt(dx * dx + dy * dy);
      const minRequired = (a.radius ?? 60) + (b.radius ?? 60) + config.minSeparation * 0.5;
      if (distance < minGap) {
        minGap = distance;
      }
      if (distance < minRequired) {
        overlaps.push({ a: a.id, b: b.id, distance, minRequired });
      }
    }
  }
  return {
    valid: overlaps.length === 0,
    overlapCount: overlaps.length,
    minDistance: minGap,
    overlaps
  };
}

function main() {
  const nodes = buildNodeList();
  const positioned = computeLayout(nodes);
  const summary = analyseLayout(positioned);
  const logEntry = {
    '@timestamp': new Date().toISOString(),
    service: 'frontend',
    logger: 'graph_layout_diagnostics',
    level: summary.valid ? 'INFO' : 'WARN',
    message: summary.valid ? 'Deterministic layout validated' : 'Layout has overlaps',
    config,
    nodeCount: positioned.length,
    minDistance: summary.minDistance,
    overlapCount: summary.overlapCount,
    overlaps: summary.overlaps,
    nodes: positioned.map(node => ({ id: node.id, x: node.x, y: node.y, radius: node.radius, type: node.type }))
  };

  const logDir = path.join(ROOT_DIR, 'logs');
  if (!fs.existsSync(logDir)) {
    fs.mkdirSync(logDir, { recursive: true });
  }
  const logPath = path.join(logDir, 'graph_layout_diagnostics.jsonl');
  fs.appendFileSync(logPath, JSON.stringify(logEntry) + '\n');
  console.log(JSON.stringify(logEntry, null, 2));
}

if (require.main === module) {
  main();
}

