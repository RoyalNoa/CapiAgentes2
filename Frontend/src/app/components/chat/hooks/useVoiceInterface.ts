import { useState, useCallback, useRef, useEffect } from 'react';
import useVoiceStream, { VoiceStage, VoiceStageUpdate, VoiceTurnSummary } from '@/app/hooks/useVoiceStream';

type VoiceStageStatus = VoiceStageUpdate['status'];

const INITIAL_VOICE_STAGES: Record<VoiceStage, VoiceStageStatus> = {
  transcription: 'pending',
  orchestration: 'pending',
  synthesis: 'pending',
};

interface UseVoiceInterfaceOptions {
  sessionId: string;
  onMessageAppend: (message: any) => void;
}

export default function useVoiceInterface({ sessionId, onMessageAppend }: UseVoiceInterfaceOptions) {
  const [, setVoiceStages] = useState<Record<VoiceStage, VoiceStageStatus>>(INITIAL_VOICE_STAGES);
  const [voiceStageTimeline, setVoiceStageTimeline] = useState<Array<{ stage: VoiceStage; status: VoiceStageStatus; at: number }>>([]);
  const [voiceNotice, setVoiceNotice] = useState<string | null>(null);
  const [autoPlayError, setAutoPlayError] = useState<string | null>(null);
  const [isMicPressed, setIsMicPressed] = useState(false);
  const [isAudioMuted, setIsAudioMuted] = useState(false);
  const [isAudioPlaying, setIsAudioPlaying] = useState(false);

  const audioRef = useRef<HTMLAudioElement | null>(null);
  const activeVoiceTurnRef = useRef<string | null>(null);
  const publishedUserTurnsRef = useRef<Set<string>>(new Set<string>());
  const publishedAgentTurnsRef = useRef<Set<string>>(new Set<string>());

  const pushStageUpdate = useCallback((update: VoiceStageUpdate) => {
    setVoiceStages((prev) => ({ ...prev, [update.stage]: update.status }));
    setVoiceStageTimeline((prev) => {
      const last = prev[prev.length - 1];
      if (last && last.stage === update.stage && last.status === update.status) {
        return prev;
      }
      const next = [...prev, { ...update, at: Date.now() }];
      return next.length > 16 ? next.slice(next.length - 16) : next;
    });
  }, []);

  const handleVoiceStageUpdate = useCallback((update: VoiceStageUpdate) => {
    pushStageUpdate(update);
    if (update.status === 'error') {
      setVoiceNotice('Detectamos un problema en el pipeline de voz');
    } else if (voiceNotice) {
      setVoiceNotice(null);
    }
  }, [pushStageUpdate, voiceNotice]);

  const handleVoiceTurnComplete = useCallback((summary: VoiceTurnSummary) => {
    pushStageUpdate({ stage: 'synthesis', status: 'complete' });
    setVoiceStages({
      transcription: 'complete',
      orchestration: 'complete',
      synthesis: 'complete',
    });
    setVoiceNotice(null);

    const currentTurn = activeVoiceTurnRef.current ?? `voice-${Date.now()}`;
    if (!activeVoiceTurnRef.current) {
      activeVoiceTurnRef.current = currentTurn;
    }

    const finalTranscriptValue = (summary.transcript || '').trim();
    if (finalTranscriptValue && !publishedUserTurnsRef.current.has(currentTurn)) {
      onMessageAppend({
        role: 'user',
        content: finalTranscriptValue,
        metadata: { modality: 'voice', turn: currentTurn },
      });
      publishedUserTurnsRef.current.add(currentTurn);
    }

    const agentReply = (summary.responseText || '').trim();
    if (agentReply && !publishedAgentTurnsRef.current.has(currentTurn)) {
      const stageLog = voiceStageTimeline.map((entry) => ({
        stage: entry.stage,
        status: entry.status,
      }));
      onMessageAppend({
        role: 'agent',
        content: agentReply,
        metadata: {
          modality: 'voice',
          turn: currentTurn,
          stageLog,
        },
      });
      publishedAgentTurnsRef.current.add(currentTurn);
    }

    activeVoiceTurnRef.current = null;
  }, [onMessageAppend, pushStageUpdate, voiceStageTimeline]);

  const {
    isRecording,
    isProcessing,
    partialTranscript,
    finalTranscript,
    responseText,
    audioUrl,
    startRecording,
    stopRecording,
    reset: resetVoiceStream,
    error: voiceError,
  } = useVoiceStream({
    sessionId,
    onStageUpdate: handleVoiceStageUpdate,
    onTurnCompleted: handleVoiceTurnComplete,
  });

  const beginVoiceRecording = useCallback(() => {
    if (isRecording || isProcessing) {
      return;
    }
    const turnId = `voice-${Date.now()}`;
    activeVoiceTurnRef.current = turnId;
    publishedUserTurnsRef.current = new Set<string>();
    publishedAgentTurnsRef.current = new Set<string>();
    setVoiceStages(INITIAL_VOICE_STAGES);
    setVoiceStageTimeline([]);
    setVoiceNotice(null);
    setAutoPlayError(null);
    setIsMicPressed(true);
    resetVoiceStream();
    void startRecording().catch((err) => {
      console.error('No se pudo iniciar la captura de audio', err);
      setVoiceNotice('No pudimos iniciar la captura de audio');
      setIsMicPressed(false);
    });
  }, [isProcessing, isRecording, resetVoiceStream, startRecording]);

  const finishVoiceRecording = useCallback(() => {
    if (!isRecording) {
      setIsMicPressed(false);
      return;
    }
    setIsMicPressed(false);
    void stopRecording().catch((err) => {
      console.error('No se pudo detener la captura de audio', err);
      setVoiceNotice('No pudimos cerrar la captura de audio');
    });
  }, [isRecording, stopRecording]);

  const handleToggleMute = useCallback(() => {
    setIsAudioMuted((prev) => {
      const next = !prev;
      const audio = audioRef.current;
      if (audio) {
        audio.muted = next;
        audio.volume = next ? 0 : 1;
      }
      return next;
    });
  }, []);

  const handleReplay = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.currentTime = 0;
    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === 'function') {
      playPromise.catch((err) => {
        console.error('No pudimos reproducir el audio', err);
        setAutoPlayError('Activa el sonido para escuchar la respuesta');
      });
    }
    setAutoPlayError(null);
    setIsAudioPlaying(true);
  }, []);

  const handleStopPlayback = useCallback(() => {
    const audio = audioRef.current;
    if (!audio) return;
    audio.pause();
    audio.currentTime = 0;
    setIsAudioPlaying(false);
  }, []);

  useEffect(() => {
    if (voiceError) {
      setVoiceNotice(voiceError);
    }
  }, [voiceError]);

  useEffect(() => {
    if (!audioUrl) {
      if (audioRef.current) {
        audioRef.current.pause();
      }
      audioRef.current = null;
      setIsAudioPlaying(false);
      return;
    }
    const audio = new Audio(audioUrl);
    audioRef.current = audio;
    audio.loop = false;
    audio.muted = isAudioMuted;
    audio.volume = isAudioMuted ? 0 : 1;

    const onPlay = () => {
      setIsAudioPlaying(true);
      setAutoPlayError(null);
    };
    const onEnd = () => setIsAudioPlaying(false);
    const onPause = () => setIsAudioPlaying(false);

    audio.addEventListener('play', onPlay);
    audio.addEventListener('ended', onEnd);
    audio.addEventListener('pause', onPause);

    const playPromise = audio.play();
    if (playPromise && typeof playPromise.catch === 'function') {
      playPromise.catch((err) => {
        console.error('Autoplay bloqueado', err);
        setAutoPlayError('Presiona reproducir para escuchar la respuesta');
        setIsAudioPlaying(false);
      });
    }

    return () => {
      audio.removeEventListener('play', onPlay);
      audio.removeEventListener('ended', onEnd);
      audio.removeEventListener('pause', onPause);
      audio.pause();
      audioRef.current = null;
    };
  }, [audioUrl, isAudioMuted]);

  useEffect(() => () => {
    if (audioRef.current) {
      audioRef.current.pause();
      audioRef.current = null;
    }
  }, []);

  return {
    isRecording,
    isProcessing,
    isMicPressed,
    partialTranscript,
    finalTranscript,
    responseText,
    voiceNotice,
    autoPlayError,
    audioUrl,
    isAudioMuted,
    isAudioPlaying,
    beginVoiceRecording,
    finishVoiceRecording,
    handleToggleMute,
    handleReplay,
    handleStopPlayback,
  };
}
