#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test específico para verificar eventos de consulta de saldo.
"""
import asyncio
import websockets
import json
import requests
from datetime import datetime
import threading

async def test_saldo_palermo():
    # Primero conectamos al WebSocket de eventos
    events = []

    async def listen_events():
        async with websockets.connect("ws://localhost:8000/ws/agents") as ws:
            print(f"[{datetime.now()}] [OK] Conectado al WebSocket de eventos")
            while True:
                try:
                    msg = await ws.recv()
                    data = json.loads(msg)
                    if data.get('type') in ['agent_start', 'agent_end']:
                        agent = data.get('agent', 'unknown')
                        action = data.get('data', {}).get('action', 'unknown')
                        print(f"[{datetime.now()}] >> Evento: {data['type']} - Agente: {agent} - Accion: {action}")
                        events.append(data)
                except websockets.exceptions.ConnectionClosed:
                    break
                except Exception as e:
                    print(f"Error procesando evento: {e}")

    # Escuchar eventos en background
    event_task = asyncio.create_task(listen_events())

    # Esperar un momento para asegurar conexión
    await asyncio.sleep(0.5)

    # Enviar la consulta en thread separado
    print(f"\n[{datetime.now()}] >> Enviando consulta: '¿Cuál es el saldo total de la sucursal de Palermo?'\n")

    def send_request():
        response = requests.post(
            "http://localhost:8000/api/command",
            json={
                "instruction": "¿Cuál es el saldo total de la sucursal de Palermo?",
                "client_id": "test_saldo_001"
            }
        )
        print(f"\n[{datetime.now()}] [OK] Respuesta recibida")
        return response.json()

    # Ejecutar request en thread separado para no bloquear el evento loop
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(None, send_request)

    # Esperar un poco más por eventos tardíos
    await asyncio.sleep(1)

    # Cancelar listener
    event_task.cancel()
    try:
        await event_task
    except asyncio.CancelledError:
        pass

    # Analizar eventos capturados
    print("\n" + "="*80)
    print("RESUMEN DE EVENTOS CAPTURADOS:")
    print("="*80)

    agents_seen = set()
    actions_seen = set()

    for event in events:
        agent = event.get('agent', 'unknown')
        action = event.get('data', {}).get('action', 'unknown')
        agents_seen.add(agent)
        actions_seen.add(f"{agent}:{action}")

    print(f"\n[Stats] Total de eventos: {len(events)}")
    print(f"[Agents] Agentes únicos: {', '.join(sorted(agents_seen))}")
    print(f"\n[List] Acciones por agente:")

    for agent in sorted(agents_seen):
        agent_actions = [a.split(':')[1] for a in actions_seen if a.startswith(f"{agent}:")]
        print(f"  - {agent}: {', '.join(agent_actions)}")

    # Verificar si se emitieron eventos esperados
    print("\n" + "="*80)
    print("VERIFICACIÓN DE EVENTOS ESPERADOS:")
    print("="*80)

    expected_agents = ['capi_datab', 'capi_elcajas', 'datab', 'elcajas']
    found_expected = any(agent in agents_seen for agent in expected_agents)

    if found_expected:
        print("[OK] Se detectaron eventos de agentes de saldo/cajas")
    else:
        print("[!]  NO se detectaron eventos de agentes de saldo/cajas")
        print(f"   Agentes esperados: {', '.join(expected_agents)}")
        print(f"   Agentes encontrados: {', '.join(agents_seen)}")

if __name__ == "__main__":
    asyncio.run(test_saldo_palermo())