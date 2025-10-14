import fs from 'node:fs/promises';
import path from 'node:path';
import os from 'node:os';
import { setTimeout as delay } from 'node:timers/promises';
import { createRequire } from 'node:module';
import { pathToFileURL } from 'node:url';

const require = createRequire(import.meta.url);
const FRONTEND_DIR = path.resolve('Frontend');
const FRONTEND_SRC = path.join(FRONTEND_DIR, 'src');
const esbuild = require(path.join(FRONTEND_DIR, 'node_modules/esbuild'));

const aliasPlugin = {
  name: 'alias',
  setup(build) {
    build.onResolve({ filter: /^@\/(.*)$/ }, args => ({
      path: path.join(FRONTEND_SRC, args.path.slice(2))
    }));
  }
};

async function bundleChatHelpers(tempDir) {
    const outfile = path.join(tempDir, 'chatHelpers.mjs');
    await esbuild.build({
        entryPoints: [path.join(FRONTEND_DIR, 'src/app/utils/chatHelpers.ts')],
        bundle: true,
        format: 'esm',
        platform: 'node',
        target: ['node20'],
        outfile,
        absWorkingDir: FRONTEND_DIR,
        plugins: [aliasPlugin],
        define: {
            'process.env.NODE_ENV': '"production"'
        },
        banner: {
            js: 'import { createRequire } from "module"; const require = createRequire(import.meta.url);'
        },
        logLevel: 'error'
    });
    return outfile;
}

function waitForOpen(ws) {
    return new Promise((resolve, reject) => {
        ws.addEventListener('open', resolve, { once: true });
        ws.addEventListener('error', reject, { once: true });
    });
}

function collectAgentEvents(ws, sessionId) {
    const transitions = [];
    const rawEvents = [];

    ws.addEventListener('message', event => {
        try {
            const data = JSON.parse(event.data.toString());
            const payloadSession = data.session_id ?? data.data?.session_id ?? data.meta?.session_id;
            if (sessionId && payloadSession !== sessionId) {
                return;
            }
            rawEvents.push(data);
            if (data.type === 'node_transition') {
                const fromNode = data.data?.from ?? data.from;
                const toNode = data.data?.to ?? data.to;
                if (fromNode && toNode) {
                    transitions.push({
                        from: fromNode,
                        to: toNode,
                        timestamp: data.timestamp,
                        action: data.data?.action ?? data.action
                    });
                }
            }
        } catch (error) {
            // ignore malformed messages
        }
    });

    return { transitions, rawEvents };
}

async function run() {
    const sessionId = `codex-e2e-palermo-${Date.now()}`;
    const question = '¿cuál es el saldo total de la sucursal de Palermo?';

    const agentWs = new WebSocket('ws://localhost:8000/ws/agents');
    const orchestratorWs = new WebSocket('ws://localhost:8000/ws');

    const { transitions, rawEvents } = collectAgentEvents(agentWs, sessionId);

    await Promise.all([waitForOpen(agentWs), waitForOpen(orchestratorWs)]);

    orchestratorWs.send(JSON.stringify({ instruction: question, client_id: sessionId }));

    const orchestratorMessages = [];
    const finalResponse = await new Promise((resolve, reject) => {
        const timeout = setTimeout(() => reject(new Error('timeout awaiting orchestrator response')), 60000);
        orchestratorWs.addEventListener('message', event => {
            try {
                const data = JSON.parse(event.data.toString());
                orchestratorMessages.push(data);
                if (data?.response) {
                    clearTimeout(timeout);
                    resolve(data);
                }
            } catch (error) {
                // ignore and continue
            }
        });
        orchestratorWs.addEventListener('error', reject, { once: true });
    });

    await delay(1500);

    orchestratorWs.close();
    agentWs.close();

    const tempDir = await fs.mkdtemp(path.join(os.tmpdir(), 'capi-e2e-'));
    try {
        const bundlePath = await bundleChatHelpers(tempDir);
        const moduleUrl = pathToFileURL(bundlePath).href;
        const { buildAgentTaskEvents } = await import(moduleUrl);

        const responsePayload = finalResponse.response ?? {};
        const responseMetadata = responsePayload.response_metadata ?? responsePayload.metadata?.response_metadata ?? {};
        const sharedArtifacts = responseMetadata.shared_artifacts ?? responsePayload.shared_artifacts ?? responsePayload.data?.shared_artifacts ?? {};
        const reasoningPlan = (responsePayload.metadata?.reasoning_plan ?? responsePayload.data?.reasoning_plan ?? responseMetadata.reasoning_plan ?? responsePayload.reasoning_plan) ?? {};
        const planSteps = Array.isArray(reasoningPlan.steps) ? reasoningPlan.steps : [];

        const finalMessage = {
            payload: {
                response_metadata: {
                    ...responseMetadata,
                    shared_artifacts: sharedArtifacts,
                    reasoning_plan: reasoningPlan
                },
                data: {
                    reasoning_plan: reasoningPlan,
                    shared_artifacts: sharedArtifacts
                }
            }
        };

        const simulatedEvents = buildAgentTaskEvents({
            agentEvents: [],
            planSteps,
            finalMessage
        });

        const eventSummary = simulatedEvents.map(evt => ({
            agent: evt.agent,
            label: evt.friendlyName ?? evt.agent,
            text: evt.primaryText
        }));

        const nodePath = transitions
            .filter(evt => evt.from && evt.to)
            .map(evt => evt.to);

        const uniqueNodePath = [];
        for (const node of nodePath) {
            if (!uniqueNodePath.includes(node)) {
                uniqueNodePath.push(node);
            }
        }

        const orchestrationNodes = new Set(['start', 'input', 'intent', 'react', 'reasoning', 'supervisor', 'router', 'human_gate', 'assemble', 'finalize', 'response']);
        const executionNodes = uniqueNodePath.filter(node => !orchestrationNodes.has(node));

        const result = {
            sessionId,
            question,
            orchestratorAgent: finalResponse.agent,
            responseMessage: responsePayload.respuesta ?? responsePayload.message ?? null,
            sharedArtifacts,
            reasoningPlan: reasoningPlan.steps ? reasoningPlan.steps.map(step => ({ id: step.id, agent: step.agent, title: step.title })) : [],
            executionNodes,
            simulatedEvents: eventSummary,
            raw: {
                orchestratorMessages,
                agentTransitions: transitions
            }
        };

        const outputPath = path.resolve('logs', `e2e_palermo_${Date.now()}.json`);
        await fs.writeFile(outputPath, JSON.stringify(result, null, 2), 'utf-8');

        console.log('E2E Palermo run completed. Summary:');
        console.log(JSON.stringify({
            sessionId,
            question,
            executionNodes,
            simulatedEvents: eventSummary
        }, null, 2));
        console.log(`Detailed log saved to ${outputPath}`);
    } finally {
        await fs.rm(tempDir, { recursive: true, force: true });
    }
}

run().catch(error => {
    console.error('E2E Palermo run failed:', error);
    process.exit(1);
});
