import asyncio
import json
import os
import time
from typing import Any, Dict, List, Optional

print("[run_voice_e2e] script import ok")

import requests
from google.cloud import texttospeech_v1 as texttospeech
import websockets

VOICE_TEXT = "Hola, necesito el saldo total de la sucursal de Palermo para hoy."
SAMPLE_RATE = 16000
CHUNK_SIZE = 3200
WS_URI = os.getenv("VOICE_E2E_WS_URI", "ws://localhost:8000/api/voice/stream")
CONFIG_URL = os.getenv("VOICE_E2E_CONFIG_URL", "http://localhost:8000/api/voice/config")
SESSION_ID = os.getenv("VOICE_E2E_SESSION_ID", "voice-e2e-palermo")
USER_ID = os.getenv("VOICE_E2E_USER_ID", "voice-e2e-tester")
HEALTH_TIMEOUT = int(os.getenv("VOICE_E2E_HEALTH_TIMEOUT", "30"))
RECV_TIMEOUT = float(os.getenv("VOICE_E2E_RECV_TIMEOUT", "20"))


def wait_for_backend() -> None:
    deadline = time.time() + HEALTH_TIMEOUT
    while time.time() < deadline:
        try:
            resp = requests.get(CONFIG_URL, timeout=3)
            if resp.status_code == 200:
                print("[run_voice_e2e] backend listo")
                return
            print(f"[run_voice_e2e] backend responde {resp.status_code}, reintentando...")
        except requests.RequestException as exc:
            print(f"[run_voice_e2e] backend no disponible ({exc}); espera 1s")
        time.sleep(1)
    raise RuntimeError("Backend de voz no respondió en tiempo y forma")


def ensure_credentials() -> None:
    cred_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")
    default_path = os.path.join(os.getcwd(), "secrets", "voice-streaming-sa.json")
    if cred_path and os.path.exists(cred_path):
        print(f"[run_voice_e2e] usando credenciales {cred_path}")
        return
    if os.path.exists(default_path):
        os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = default_path
        print(f"[run_voice_e2e] GOOGLE_APPLICATION_CREDENTIALS => {default_path}")
        return
    raise RuntimeError("No se encuentran credenciales de Google. Configure GOOGLE_APPLICATION_CREDENTIALS.")


def synthesize_linearin16(text: str) -> bytes:
    print("[run_voice_e2e] sintetizando texto...")
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=text)
    voice = texttospeech.VoiceSelectionParams(
        language_code="es-ES",
        name=os.getenv("GOOGLE_TTS_VOICE", "es-ES-Wavenet-D"),
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding=texttospeech.AudioEncoding.LINEAR16,
        sample_rate_hertz=SAMPLE_RATE,
    )
    response = client.synthesize_speech(
        request=texttospeech.SynthesizeSpeechRequest(
            input=synthesis_input,
            voice=voice,
            audio_config=audio_config,
        )
    )
    audio = response.audio_content or b""
    if not audio:
        raise RuntimeError("La sintesis TTS devolvió audio vacío")
    print("[run_voice_e2e] sintetizado ok")
    return audio


def chunk_audio(audio: bytes) -> List[bytes]:
    return [audio[i : i + CHUNK_SIZE] for i in range(0, len(audio), CHUNK_SIZE)]


async def stream_voice_test() -> None:
    ensure_credentials()
    wait_for_backend()

    audio_bytes = synthesize_linearin16(VOICE_TEXT)
    chunks = chunk_audio(audio_bytes)
    print(f"Audio sintetizado: {len(audio_bytes)} bytes, {len(chunks)} chunks")

    start_time = time.perf_counter()

    try:
        async with websockets.connect(WS_URI, ping_interval=None, ping_timeout=None) as ws:
            await ws.send(
                json.dumps(
                    {
                        "event": "start",
                        "session_id": SESSION_ID,
                        "user_id": USER_ID,
                        "language": "es-ES",
                        "sample_rate": SAMPLE_RATE,
                    }
                )
            )

            try:
                ack_raw = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
            except asyncio.TimeoutError as exc:
                raise RuntimeError("Timeout esperando ACK de sesión") from exc
            print(f"ACK: {ack_raw}")

            for chunk in chunks:
                await ws.send(chunk)
            await ws.send(json.dumps({"event": "stop"}))

            transcript_segments: List[str] = []
            response_payload: Optional[Dict[str, Any]] = None
            warning_payload: Optional[Dict[str, Any]] = None

            while True:
                try:
                    message = await asyncio.wait_for(ws.recv(), timeout=RECV_TIMEOUT)
                except asyncio.TimeoutError:
                    print("[run_voice_e2e] timeout esperando mensajes finales")
                    break
                latency_ms = (time.perf_counter() - start_time) * 1000
                try:
                    payload = json.loads(message)
                except json.JSONDecodeError:
                    print("[WARN] Mensaje no JSON", message[:120])
                    continue

                msg_type = payload.get("type")
                print(f"[{latency_ms:0.0f} ms] {msg_type}: {payload}")

                if msg_type == "transcript" and payload.get("text"):
                    transcript_segments.append(payload["text"])
                elif msg_type == "response":
                    response_payload = payload
                elif msg_type == "warning":
                    warning_payload = payload
                elif msg_type == "error":
                    raise RuntimeError(f"Backend devolvió error: {payload}")
                elif msg_type == "turn_complete":
                    break

            total_latency = (time.perf_counter() - start_time) * 1000
            final_transcript = " ".join(transcript_segments).strip()

            print("\n==== RESULTADOS ====")
            print(f"Transcripción final: {final_transcript or '[vacía]'}")
            if warning_payload:
                print(f"Advertencia: {warning_payload}")
            if response_payload:
                print(f"Respuesta: {response_payload.get('response_text')}")
                audio_meta = response_payload.get("audio", {})
                print(
                    "Audio recibido: base64=%s url=%s"
                    % (bool(audio_meta.get("base64")), audio_meta.get("url"))
                )
            print(f"Latencia total: {total_latency:0.0f} ms")
    except websockets.exceptions.InvalidStatusCode as exc:
        raise RuntimeError(f"WS rechazado: status={exc.status_code}") from exc
    except Exception as exc:
        raise RuntimeError(f"Fallo en la sesión de voz: {exc}") from exc


if __name__ == "__main__":
    print("[run_voice_e2e] iniciando prueba")
    try:
        asyncio.run(stream_voice_test())
    except Exception as exc:
        print(f"[run_voice_e2e] PRUEBA FALLÓ: {exc}")
        raise
