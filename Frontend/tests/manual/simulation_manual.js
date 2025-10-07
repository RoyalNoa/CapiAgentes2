// Test de simulación para CapiAgentes
// Este script prueba que los eventos del backend tengan contenido

const API_BASE = 'http://localhost:8000';
const WS_BASE = 'ws://localhost:8000';

// Colores para la consola
const colors = {
    reset: '\x1b[0m',
    red: '\x1b[31m',
    green: '\x1b[32m',
    yellow: '\x1b[33m',
    blue: '\x1b[36m',
    magenta: '\x1b[35m'
};

function log(message, color = 'reset') {
    console.log(`${colors[color]}${message}${colors.reset}`);
}

// Test WebSocket de agentes
async function testAgentWebSocket() {
    return new Promise((resolve, reject) => {
        log('\n=== PRUEBA WEBSOCKET DE AGENTES ===', 'blue');

        const ws = new WebSocket(`${WS_BASE}/ws/agents`);
        const events = [];
        let timeout;

        ws.on('open', () => {
            log('✅ WebSocket conectado', 'green');

            // Solicitar historial
            ws.send(JSON.stringify({
                type: 'get_history',
                limit: 20
            }));

            // Timeout para cerrar después de 5 segundos
            timeout = setTimeout(() => {
                ws.close();
                resolve(events);
            }, 5000);
        });

        ws.on('message', (data) => {
            try {
                const event = JSON.parse(data);
                events.push(event);

                // Verificar contenido
                if (event.type === 'agent_start' || event.type === 'agent_end') {
                    const hasContent = event.meta?.content || event.data?.content;
                    if (hasContent) {
                        log(`✅ ${event.type}: ${event.agent} - "${hasContent}"`, 'green');
                    } else {
                        log(`❌ ${event.type}: ${event.agent} - SIN CONTENIDO`, 'red');
                    }
                }
            } catch (error) {
                log(`Error parsing: ${error.message}`, 'red');
            }
        });

        ws.on('error', (error) => {
            log(`❌ Error WebSocket: ${error}`, 'red');
            clearTimeout(timeout);
            reject(error);
        });

        ws.on('close', () => {
            log('WebSocket cerrado', 'yellow');
            clearTimeout(timeout);
        });
    });
}

// Test comando al backend
async function testCommand(instruction) {
    log(`\n=== ENVIANDO COMANDO: "${instruction}" ===`, 'blue');

    try {
        const response = await fetch(`${API_BASE}/api/command`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ instruction })
        });

        const data = await response.json();

        if (data.response?.metadata?.completed_nodes) {
            log(`Nodos: ${data.response.metadata.completed_nodes.join(' → ')}`, 'magenta');
        }

        log(`Respuesta: ${JSON.stringify(data.response?.respuesta).substring(0, 100)}...`, 'green');

        return data;
    } catch (error) {
        log(`❌ Error: ${error.message}`, 'red');
        return null;
    }
}

// Test completo con WebSocket escuchando
async function testCompleteFlow() {
    log('\n🚀 INICIANDO PRUEBA COMPLETA END-TO-END', 'blue');

    const WebSocket = require('ws');
    global.WebSocket = WebSocket;

    // Conectar WebSocket primero
    const ws = new WebSocket(`${WS_BASE}/ws/agents`);
    const events = [];

    await new Promise((resolve) => {
        ws.on('open', () => {
            log('✅ WebSocket listo para escuchar eventos', 'green');
            resolve();
        });
    });

    // Escuchar eventos
    ws.on('message', (data) => {
        try {
            const event = JSON.parse(data);

            if (event.type === 'agent_start' || event.type === 'agent_end') {
                events.push(event);
                const content = event.meta?.content || event.data?.content;

                if (content) {
                    log(`📊 [${events.length}] ${event.type}: ${event.agent} - "${content}"`, 'green');
                } else {
                    log(`⚠️  [${events.length}] ${event.type}: ${event.agent} - SIN CONTENIDO`, 'red');
                }
            } else if (event.type === 'node_transition') {
                log(`🔄 Transición: ${event.from} → ${event.to}`, 'yellow');
            }
        } catch (error) {
            // Ignorar errores de parsing
        }
    });

    // Hacer consulta
    await testCommand("Muestra un resumen de los datos financieros");

    // Esperar eventos
    await new Promise(resolve => setTimeout(resolve, 3000));

    // Análisis final
    log('\n📈 RESUMEN DE LA PRUEBA:', 'blue');
    log(`   Total eventos capturados: ${events.length}`, 'magenta');

    const eventsWithContent = events.filter(e => e.meta?.content || e.data?.content);
    log(`   Eventos con contenido: ${eventsWithContent.length}`,
        eventsWithContent.length > 0 ? 'green' : 'red');

    const agents = [...new Set(events.map(e => e.agent).filter(Boolean))];
    log(`   Agentes involucrados: ${agents.join(', ')}`, 'magenta');

    // Verificación crítica
    if (eventsWithContent.length === 0) {
        log('\n❌ PROBLEMA DETECTADO:', 'red');
        log('   Los eventos NO tienen contenido descriptivo en meta.content', 'red');
        log('   Necesitamos modificar base.py para agregar contenido real', 'yellow');
        log('   Líneas 153-190 y 183-212 en base.py', 'yellow');
    } else {
        log('\n✅ ÉXITO: Los eventos tienen contenido descriptivo', 'green');
        log('   La simulación en el frontend debería funcionar correctamente', 'green');
    }

    ws.close();

    return {
        totalEvents: events.length,
        eventsWithContent: eventsWithContent.length,
        agents: agents,
        success: eventsWithContent.length > 0
    };
}

// Ejecutar si se llama directamente
if (require.main === module) {
    testCompleteFlow()
        .then(result => {
            log('\n🏁 Prueba completada', 'blue');
            process.exit(result.success ? 0 : 1);
        })
        .catch(error => {
            log(`\n❌ Error fatal: ${error}`, 'red');
            process.exit(1);
        });
}

module.exports = { testCompleteFlow, testCommand, testAgentWebSocket };