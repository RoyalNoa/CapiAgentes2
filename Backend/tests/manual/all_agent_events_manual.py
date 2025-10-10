#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test completo para capturar eventos de TODOS los tipos de agentes.
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime

async def test_all_queries():
    all_events = []

    async def listen_events():
        async with websockets.connect("ws://localhost:8000/ws/agents") as ws:
            print("[OK] Conectado al WebSocket\n")
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    all_events.append(data)

                    agent = data.get('agent', 'unknown')
                    event_type = data.get('type', 'unknown')
                    event_data = data.get('data', {})

                    # Solo mostrar agentes no-orquestación
                    orchestration = ['router', 'intent', 'start', 'finalize', 'assemble',
                                   'react', 'reasoning', 'supervisor']
                    if not any(x in agent.lower() for x in orchestration):
                        print(f"[{event_type}] {agent}")
                        if event_data:
                            action = event_data.get('action', '')
                            if action and action != 'agent_end':
                                print(f"  -> Action: {action}")

                            # Buscar texto descriptivo
                            for field in ['summary', 'text', 'message', 'result']:
                                if field in event_data and event_data[field]:
                                    text = str(event_data[field])[:80]
                                    print(f"  -> {field}: {text}")
                                    break
                        print()

                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    print(f"Error: {e}")

    # Listener en background
    event_task = asyncio.create_task(listen_events())
    await asyncio.sleep(0.5)

    queries = [
        ("Analiza los datos financieros", "test_summary"),
        ("Detectar anomalias en las transacciones", "test_anomaly"),
        ("Rendimiento de la sucursal SUC-404", "test_branch"),
        ("Hola, buenos dias!", "test_capi_gus"),
        ("Genera un archivo con el resumen en mi escritorio", "test_desktop"),
    ]

    for query, client_id in queries:
        print("="*60)
        print(f"CONSULTA: {query}")
        print("="*60)

        def send_request(q, cid):
            return requests.post(
                "http://localhost:8000/api/command",
                json={"instruction": q, "client_id": cid}
            )

        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, send_request, query, client_id)

        # Esperar entre consultas
        await asyncio.sleep(3)

    # Cancelar listener
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass

    # Análisis final
    print("\n" + "="*80)
    print("RESUMEN DE EVENTOS DE AGENTES (NO ORQUESTACION)")
    print("="*80)

    agent_summary = {}
    for event in all_events:
        agent = event.get('agent', 'unknown')
        orchestration = ['router', 'intent', 'start', 'finalize', 'assemble',
                        'react', 'reasoning', 'supervisor', 'human_gate']

        if not any(x in agent.lower() for x in orchestration):
            if agent not in agent_summary:
                agent_summary[agent] = {
                    'events': [],
                    'actions': set(),
                    'texts': []
                }

            event_type = event.get('type', '')
            event_data = event.get('data', {})

            agent_summary[agent]['events'].append(event_type)

            if 'action' in event_data:
                agent_summary[agent]['actions'].add(event_data['action'])

            # Capturar textos descriptivos
            for field in ['summary', 'text', 'message', 'result']:
                if field in event_data and event_data[field]:
                    agent_summary[agent]['texts'].append(
                        f"{field}: {str(event_data[field])[:60]}..."
                    )

    for agent, info in agent_summary.items():
        print(f"\n[AGENTE: {agent}]")
        print(f"  Eventos: {', '.join(set(info['events']))}")
        print(f"  Actions: {', '.join(info['actions'])}")
        if info['texts']:
            print("  Textos capturados:")
            for text in info['texts'][:3]:  # Solo primeros 3
                print(f"    - {text}")

if __name__ == "__main__":
    asyncio.run(test_all_queries())