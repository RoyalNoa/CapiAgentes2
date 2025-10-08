#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test para capturar TODOS los eventos de agentes y ver su contenido exacto.
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime
import threading

async def test_agent_events():
    events_by_agent = {}

    async def listen_events():
        async with websockets.connect("ws://localhost:8000/ws/agents") as ws:
            print(f"[{datetime.now()}] [OK] Conectado al WebSocket de eventos\n")
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)

                    # Capturar info del agente
                    agent = data.get('agent', 'unknown')
                    event_type = data.get('type', 'unknown')

                    # Guardar evento por agente
                    if agent not in events_by_agent:
                        events_by_agent[agent] = []

                    events_by_agent[agent].append({
                        'type': event_type,
                        'data': data.get('data', {}),
                        'meta': data.get('meta', {}),
                        'timestamp': data.get('timestamp', '')
                    })

                    # Imprimir en tiempo real
                    print(f"[EVENTO] Agente: {agent} | Tipo: {event_type}")
                    if 'data' in data and data['data']:
                        print(f"  Data: {json.dumps(data['data'], indent=2)}")
                    print("-" * 60)

                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    print(f"Error: {e}")

    # Escuchar eventos en background
    event_task = asyncio.create_task(listen_events())
    await asyncio.sleep(0.5)

    # Enviar consulta de prueba
    print("\n" + "="*80)
    print("ENVIANDO CONSULTA: 'Cual es el saldo total de la sucursal de Palermo?'")
    print("="*80 + "\n")

    def send_request():
        response = requests.post(
            "http://localhost:8000/api/command",
            json={
                "instruction": "Cual es el saldo total de la sucursal de Palermo?",
                "client_id": "test_agent_events_001"
            }
        )
        return response.json()

    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, send_request)

    # Esperar por eventos
    await asyncio.sleep(2)

    # Cancelar listener
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass

    # Mostrar resumen
    print("\n" + "="*80)
    print("RESUMEN DE EVENTOS POR AGENTE")
    print("="*80)

    # Separar agentes de orquestación vs agentes de negocio
    orchestration_agents = ['router', 'intent', 'start', 'finalize', 'assemble',
                          'react', 'reasoning', 'supervisor', 'human_gate']

    business_agents = {}
    orchestration_events = {}

    for agent, events in events_by_agent.items():
        agent_lower = agent.lower()
        is_orchestration = any(orch in agent_lower for orch in orchestration_agents)

        if is_orchestration:
            orchestration_events[agent] = events
        else:
            business_agents[agent] = events

    print("\n[AGENTES DE NEGOCIO (NO ORQUESTACION)]:")
    print("-" * 40)

    for agent, events in business_agents.items():
        print(f"\nAgente: {agent}")
        print(f"  Total eventos: {len(events)}")

        for evt in events:
            print(f"  - Tipo: {evt['type']}")
            if evt['data']:
                action = evt['data'].get('action', 'N/A')
                print(f"    Action: {action}")

                # Mostrar campos adicionales importantes
                for key in ['summary', 'tone', 'text', 'result', 'message']:
                    if key in evt['data']:
                        print(f"    {key}: {evt['data'][key][:100]}...")

    print("\n[AGENTES DE ORQUESTACION]:")
    print("-" * 40)
    print(f"Total: {len(orchestration_events)} agentes")
    for agent in orchestration_events.keys():
        print(f"  - {agent}")

if __name__ == "__main__":
    asyncio.run(test_agent_events())