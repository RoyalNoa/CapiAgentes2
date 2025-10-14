import { useCallback, useEffect, useMemo, useRef, useState } from 'react';

const TARGET_SAMPLE_RATE = 16000;
const CHUNK_MS = 250;

type VoiceStage = 'transcription' | 'orchestration' | 'synthesis';
type VoiceStageStatus = 'pending' | 'running' | 'complete' | 'error';

interface VoiceStageUpdate {
  stage: VoiceStage;
  status: VoiceStageStatus;
}

interface VoiceTurnSummary {
  transcript: string;
  responseText: string;
  audioUrl: string | null;
  audioBase64: string | null;
  mimeType: string | null;
}

interface VoiceStreamOptions {
  sessionId: string;
  userId?: string;
  language?: string;
  onTurnCompleted?: (payload: VoiceTurnSummary) => void;
  onStageUpdate?: (update: VoiceStageUpdate) => void;
}


interface VoiceTranscriptEvent {
  text: string;
  isFinal: boolean;
}

interface VoiceMessageRoutingContext {
  onTranscript?: (event: VoiceTranscriptEvent) => void;
  onResponse?: (payload: any) => void;
  onTurnComplete?: () => void;
  onWarning?: (message?: string) => Promise<void> | void;
  onError?: (message?: string) => void;
  onStage?: (update: VoiceStageUpdate) => void;
}

export async function processVoiceStreamMessage(payload: any, ctx: VoiceMessageRoutingContext): Promise<void> {
  if (!payload || typeof payload !== 'object') {
    return;
  }
  const messageType = payload.type;
  switch (messageType) {
    case 'session_ack':
      return;
    case 'transcript': {
      const text = typeof payload.text === 'string' ? payload.text : '';
      const isFinal = Boolean(payload.is_final);
      ctx.onTranscript?.({ text, isFinal });
      ctx.onStage?.({ stage: 'transcription', status: isFinal ? 'complete' : 'running' });
      if (isFinal) {
        ctx.onStage?.({ stage: 'orchestration', status: 'running' });
      }
      return;
    }
    case 'response':
      ctx.onStage?.({ stage: 'orchestration', status: 'complete' });
      ctx.onStage?.({ stage: 'synthesis', status: 'running' });
      ctx.onResponse?.(payload);
      return;
    case 'turn_complete':
      ctx.onStage?.({ stage: 'synthesis', status: 'complete' });
      ctx.onTurnComplete?.();
      return;
    case 'warning':
      ctx.onStage?.({ stage: 'transcription', status: 'error' });
      ctx.onStage?.({ stage: 'orchestration', status: 'error' });
      ctx.onStage?.({ stage: 'synthesis', status: 'error' });
      if (ctx.onWarning) {
        await ctx.onWarning(typeof payload.message === 'string' ? payload.message : undefined);
      }
      return;
    case 'error':
      ctx.onStage?.({ stage: 'transcription', status: 'error' });
      ctx.onStage?.({ stage: 'orchestration', status: 'error' });
      ctx.onStage?.({ stage: 'synthesis', status: 'error' });
      ctx.onError?.(typeof payload.message === 'string' ? payload.message : undefined);
      return;
    default:
      return;
  }
}

interface VoiceStreamState {
  isRecording: boolean;
  isProcessing: boolean;
  partialTranscript: string;
  finalTranscript: string;
  responseText: string;
  error: string | null;
  audioUrl: string | null;
  startRecording: () => Promise<void>;
  stopRecording: () => Promise<void>;
  reset: () => void;
}

function resolveApiBase(): string {
  const fallback = process.env.NEXT_PUBLIC_API_BASE || 'http://localhost:8000';
  if (typeof window === 'undefined') {
    return fallback;
  }

  try {
    const candidate = new URL(fallback, window.location.origin);
    const browserHost = window.location.hostname;
    if (candidate.hostname === 'backend' || candidate.hostname === 'localhost') {
      candidate.hostname = browserHost;
    }
    if (!candidate.port) {
      candidate.port = window.location.port === '3000' ? '8000' : window.location.port;
    }
    return candidate.toString().replace(/\/$/, '');
  } catch {
    const protocol = window.location.protocol;
    const host = window.location.hostname;
    const port = window.location.port === '3000' ? '8000' : window.location.port;
    return `${protocol}//${host}${port ? `:${port}` : ''}`;
  }
}

function resolveWsUrl(): string {
  const base = resolveApiBase();
  const normalized = base.endsWith('/') ? base.slice(0, -1) : base;
  const wsBase = normalized.startsWith('https')
    ? normalized.replace(/^https:/i, 'wss:')
    : normalized.replace(/^http:/i, 'ws:');
  return `${wsBase}/api/voice/stream`;
}

const describeMediaError = (error: any): string => {
  const name = typeof error?.name === 'string' ? error.name : '';
  const message = typeof error?.message === 'string' ? error.message : '';

  if (name === 'NotAllowedError' || /permission/i.test(message)) {
    return 'No pudimos acceder al micrófono. Revisa los permisos del navegador.';
  }
  if (name === 'NotFoundError' || /found/i.test(message)) {
    return 'No encontramos un micrófono disponible. Conecta o habilita un dispositivo de audio.';
  }
  if (name === 'NotReadableError') {
    return 'El dispositivo de audio está en uso por otra aplicación.';
  }
  if (name === 'SecurityError' || /secure context/i.test(message)) {
    return 'La captura de voz requiere ejecutar la app en un contexto seguro (HTTPS).';
  }
  if (name === 'SecurityError' || message === 'secure_context_required') {
    return 'Activa HTTPS (por ejemplo https://localhost) para usar el micrófono.';
  }
  if (message === 'media_devices_unavailable') {
    return 'Este navegador no expone la API de audio necesaria para grabar voz.';
  }

  return message || 'No pudimos iniciar la captura de audio';
};

function mergeChannels(buffer: AudioBuffer): Float32Array {
  if (buffer.numberOfChannels === 1) {
    return new Float32Array(buffer.getChannelData(0));
  }
  const length = buffer.length;
  const result = new Float32Array(length);
  for (let channel = 0; channel < buffer.numberOfChannels; channel += 1) {
    const channelData = buffer.getChannelData(channel);
    for (let i = 0; i < length; i += 1) {
      result[i] += channelData[i];
    }
  }
  for (let i = 0; i < length; i += 1) {
    result[i] /= buffer.numberOfChannels;
  }
  return result;
}

function resampleTo(targetRate: number, source: Float32Array, sourceRate: number): Float32Array {
  if (sourceRate === targetRate) {
    return source;
  }
  const sampleRatio = sourceRate / targetRate;
  const newLength = Math.round(source.length / sampleRatio);
  const resampled = new Float32Array(newLength);
  for (let i = 0; i < newLength; i += 1) {
    const position = i * sampleRatio;
    const index = Math.floor(position);
    const nextIndex = Math.min(index + 1, source.length - 1);
    const weight = position - index;
    const sample = source[index] * (1 - weight) + source[nextIndex] * weight;
    resampled[i] = sample;
  }
  return resampled;
}

function floatTo16BitPCM(floatBuffer: Float32Array): ArrayBuffer {
  const buffer = new ArrayBuffer(floatBuffer.length * 2);
  const view = new DataView(buffer);
  for (let i = 0; i < floatBuffer.length; i += 1) {
    let s = floatBuffer[i];
    s = Math.max(-1, Math.min(1, s));
    view.setInt16(i * 2, s < 0 ? s * 0x8000 : s * 0x7fff, true);
  }
  return buffer;
}

export default function useVoiceStream(options: VoiceStreamOptions): VoiceStreamState {
  const { sessionId, userId = 'voice-client', language = 'es-ES', onTurnCompleted, onStageUpdate } = options;
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessing, setIsProcessing] = useState(false);
  const [partialTranscript, setPartialTranscript] = useState('');
  const [finalTranscript, setFinalTranscript] = useState('');
  const [responseText, setResponseText] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [audioUrl, setAudioUrl] = useState<string | null>(null);

  const wsRef = useRef<WebSocket | null>(null);
  const mediaStreamRef = useRef<MediaStream | null>(null);
  const audioContextRef = useRef<AudioContext | null>(null);
  const sourceNodeRef = useRef<MediaStreamAudioSourceNode | null>(null);
  const processorNodeRef = useRef<ScriptProcessorNode | null>(null);
  const gainNodeRef = useRef<GainNode | null>(null);
  const cleanupUrlRef = useRef<string | null>(null);

  const reset = useCallback(() => {
    setPartialTranscript('');
    setFinalTranscript('');
    setResponseText('');
    setError(null);
    if (cleanupUrlRef.current) {
      URL.revokeObjectURL(cleanupUrlRef.current);
      cleanupUrlRef.current = null;
    }
    setAudioUrl(null);
  }, []);

  const closeWs = useCallback(() => {
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.close(1000, 'voice-complete');
    }
    wsRef.current = null;
  }, []);

  const stopMedia = useCallback(async () => {
    const processor = processorNodeRef.current;
    if (processor) {
      processor.disconnect();
      processor.onaudioprocess = null;
      processorNodeRef.current = null;
    }

    const source = sourceNodeRef.current;
    if (source) {
      source.disconnect();
      sourceNodeRef.current = null;
    }

    const gainNode = gainNodeRef.current;
    if (gainNode) {
      gainNode.disconnect();
      gainNodeRef.current = null;
    }

    const stream = mediaStreamRef.current;
    if (stream) {
      stream.getTracks().forEach(track => track.stop());
      mediaStreamRef.current = null;
    }

    const audioContext = audioContextRef.current;
    if (audioContext) {
      try {
        if (audioContext.state !== 'closed') {
          await audioContext.close();
        }
      } catch (closeError) {
        console.error('Audio context close failed', closeError);
      }
      audioContextRef.current = null;
    }
  }, []);

  const stopRecording = useCallback(async () => {
    if (!isRecording) return;
    const ws = wsRef.current;
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify({ event: 'stop' }));
    }
    await stopMedia();
    setIsRecording(false);
    setIsProcessing(true);
  }, [isRecording, stopMedia]);

  const handleWsMessage = useCallback(async (event: MessageEvent) => {
    try {
      const payload = JSON.parse(event.data);
      await processVoiceStreamMessage(payload, {
        onTranscript: ({ text, isFinal }) => {
          if (isFinal) {
            setFinalTranscript(prev => (prev ? `${prev} ${text}`.trim() : text));
          } else {
            setPartialTranscript(text || '');
          }
        },
        onResponse: (messagePayload) => {
          setPartialTranscript('');
          setFinalTranscript(messagePayload.transcript || '');
          setResponseText(messagePayload.response_text || '');
          let objectUrl: string | null = null;
          const remoteUrl = messagePayload.audio?.url ?? null;
          if (messagePayload.audio?.base64) {
            const binary = atob(messagePayload.audio.base64);
            const buffer = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i += 1) {
              buffer[i] = binary.charCodeAt(i);
            }
            const blob = new Blob([buffer.buffer], { type: messagePayload.audio.mime_type || 'audio/mpeg' });
            objectUrl = URL.createObjectURL(blob);
            if (cleanupUrlRef.current) {
              URL.revokeObjectURL(cleanupUrlRef.current);
            }
            cleanupUrlRef.current = objectUrl;
            setAudioUrl(objectUrl);
          } else if (remoteUrl) {
            setAudioUrl(remoteUrl);
          } else {
            setAudioUrl(null);
          }
          if (onTurnCompleted) {
            onTurnCompleted({
              transcript: messagePayload.transcript || '',
              responseText: messagePayload.response_text || '',
              audioUrl: remoteUrl ?? objectUrl,
              audioBase64: messagePayload.audio?.base64 ?? null,
              mimeType: messagePayload.audio?.mime_type ?? null,
            });
          }
        },
        onTurnComplete: () => {
          setIsProcessing(false);
          closeWs();
        },
        onWarning: async (message) => {
          setError(message || 'Advertencia en el flujo de voz');
          setIsProcessing(false);
          await stopRecording();
        },
        onError: (message) => {
          setError(message || 'Error en el flujo de voz');
          setIsProcessing(false);
          closeWs();
        },
        onStage: onStageUpdate,
      });
    } catch (err) {
      console.error('Voice stream decoding error', err);
    }
  }, [closeWs, onTurnCompleted, onStageUpdate, stopRecording]);

  const startRecording = useCallback(async () => {
    if (isRecording || isProcessing) return;
    try {
      if (typeof window !== 'undefined' && !window.isSecureContext) {
        throw new Error('secure_context_required');
      }
      if (typeof navigator === 'undefined' || !navigator.mediaDevices?.getUserMedia) {
        throw new Error('media_devices_unavailable');
      }
      reset();
      setIsProcessing(false);
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          sampleRate: TARGET_SAMPLE_RATE,
          channelCount: 1,
          echoCancellation: false,
          noiseSuppression: false,
        },
      });
      mediaStreamRef.current = stream;

      onStageUpdate?.({ stage: 'transcription', status: 'running' });
      onStageUpdate?.({ stage: 'orchestration', status: 'pending' });
      onStageUpdate?.({ stage: 'synthesis', status: 'pending' });

      const audioContext = new AudioContext();
      if (audioContext.state === 'suspended') {
        await audioContext.resume().catch(() => undefined);
      }
      audioContextRef.current = audioContext;

      const ws = new WebSocket(resolveWsUrl());
      wsRef.current = ws;

      ws.addEventListener('message', handleWsMessage);
      ws.addEventListener('close', () => {
        wsRef.current = null;
        setIsProcessing(false);
        setIsRecording(false);
      });
      ws.addEventListener('error', () => {
        setError('No se pudo conectar con el servicio de voz');
        setIsProcessing(false);
        setIsRecording(false);
      });

      await new Promise<void>((resolve, reject) => {
        ws.addEventListener('open', () => resolve());
        ws.addEventListener('error', reject);
      });

      ws.send(JSON.stringify({
        event: 'start',
        session_id: sessionId,
        user_id: userId,
        language,
        sample_rate: TARGET_SAMPLE_RATE,
      }));

      const sourceNode = audioContext.createMediaStreamSource(stream);
      sourceNodeRef.current = sourceNode;

      const processor = audioContext.createScriptProcessor(4096, 1, 1);
      processorNodeRef.current = processor;

      const gainNode = audioContext.createGain();
      gainNode.gain.value = 0;
      gainNodeRef.current = gainNode;

      processor.onaudioprocess = (event: AudioProcessingEvent) => {
        const socket = wsRef.current;
        if (!socket || socket.readyState !== WebSocket.OPEN) {
          return;
        }
        try {
          const inputBuffer = event.inputBuffer;
          const merged = mergeChannels(inputBuffer);
          const resampled = resampleTo(
            TARGET_SAMPLE_RATE,
            merged,
            inputBuffer.sampleRate || audioContext.sampleRate,
          );
          const pcmBuffer = floatTo16BitPCM(resampled);
          socket.send(pcmBuffer);
        } catch (processErr) {
          console.error('Error processing audio chunk', processErr);
        }
      };

      sourceNode.connect(processor);
      processor.connect(gainNode);
      gainNode.connect(audioContext.destination);

      setIsRecording(true);
      setError(null);
    } catch (err: any) {
      console.error('Voice recording error', err);
      setError(describeMediaError(err));
      setIsRecording(false);
      onStageUpdate?.({ stage: 'transcription', status: 'error' });
      onStageUpdate?.({ stage: 'orchestration', status: 'error' });
      onStageUpdate?.({ stage: 'synthesis', status: 'error' });
      await stopMedia();
      closeWs();
    }
  }, [closeWs, handleWsMessage, isProcessing, isRecording, language, reset, sessionId, stopMedia, userId]);

  useEffect(() => {
    return () => {
      closeWs();
      void stopMedia();
      if (cleanupUrlRef.current) {
        URL.revokeObjectURL(cleanupUrlRef.current);
      }
    };
  }, [closeWs, stopMedia]);

  return useMemo(() => ({
    isRecording,
    isProcessing,
    partialTranscript,
    finalTranscript,
    responseText,
    error,
    audioUrl,
    startRecording,
    stopRecording,
    reset,
  }), [isRecording, isProcessing, partialTranscript, finalTranscript, responseText, error, audioUrl, startRecording, stopRecording, reset]);
}

export type { VoiceTurnSummary, VoiceStageUpdate };
