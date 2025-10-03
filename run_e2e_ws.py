import asyncio
import json
import time

import websockets

async def run():
    uri = 'ws://localhost:8000/ws'
    async with websockets.connect(uri) as ws:
        payload = {
            'instruction': 'cual es el saldo total de la sucursal de palermo',
            'client_id': 'e2e-session-palermo-inline'
        }
        await ws.send(json.dumps(payload))
        start = time.time()
        while True:
            try:
                raw = await asyncio.wait_for(ws.recv(), timeout=40)
            except asyncio.TimeoutError:
                print('timeout waiting for websocket response')
                break
            ts = time.time() - start
            print(f"[{ts:0.2f}s] {raw}")
            try:
                data = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if isinstance(data, dict) and data.get('agent') and data.get('response'):
                break

asyncio.run(run())
