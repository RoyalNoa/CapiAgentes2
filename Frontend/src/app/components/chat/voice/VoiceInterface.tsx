import { CSSProperties, MouseEvent, TouchEvent, useCallback, useMemo } from 'react';
import useVoiceInterface from '../hooks/useVoiceInterface';

interface VoiceInterfaceProps {
  sessionId: string;
  onMessageAppend: (message: any) => void;
}

const ACCENT_COLOR = '#00e5ff';
const CONTAINER_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  gap: '12px',
  padding: '16px',
  background: 'rgba(10, 15, 28, 0.65)',
  border: '1px solid rgba(0, 229, 255, 0.18)',
  borderRadius: '14px',
  backdropFilter: 'blur(8px)',
};

const STATUS_STYLE: CSSProperties = {
  fontSize: '13px',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  color: '#f97373',
};

const MIC_WRAPPER_STYLE: CSSProperties = {
  display: 'flex',
  flexDirection: 'column',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '10px',
};

const MIC_BUTTON_BASE: CSSProperties = {
  width: '72px',
  height: '72px',
  borderRadius: '50%',
  border: '1px solid rgba(148, 163, 184, 0.25)',
  background: 'rgba(15, 23, 42, 0.75)',
  color: '#e2e8f0',
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
  outline: 'none',
};

const MIC_BUTTON_IDLE: CSSProperties = {
  borderColor: 'rgba(0, 229, 255, 0.24)',
  boxShadow: '0 0 16px rgba(0, 229, 255, 0.18)',
  background: 'rgba(0, 42, 62, 0.55)',
};

const MIC_BUTTON_ACTIVE: CSSProperties = {
  borderColor: ACCENT_COLOR,
  boxShadow: '0 0 18px rgba(0, 229, 255, 0.35)',
  background: 'rgba(0, 229, 255, 0.16)',
};

const MIC_STATUS_STYLE: CSSProperties = {
  fontSize: '12px',
  letterSpacing: '0.12em',
  textTransform: 'uppercase',
  color: ACCENT_COLOR,
};

const TRANSCRIPT_CONTAINER_STYLE: CSSProperties = {
  border: '1px solid rgba(148, 163, 184, 0.3)',
  background: 'rgba(15, 23, 42, 0.7)',
  borderRadius: '10px',
  padding: '12px',
  display: 'flex',
  flexDirection: 'column',
  gap: '6px',
};

const TRANSCRIPT_LABEL_STYLE: CSSProperties = {
  fontSize: '11px',
  letterSpacing: '0.1em',
  textTransform: 'uppercase',
  color: '#94a3b8',
};

const TRANSCRIPT_TEXT_STYLE: CSSProperties = {
  margin: 0,
  fontSize: '14px',
  lineHeight: 1.5,
  color: '#e2e8f0',
};

const PLAYBACK_ROW_STYLE: CSSProperties = {
  display: 'flex',
  flexWrap: 'wrap',
  gap: '10px',
  alignItems: 'center',
};

const PLAYBACK_BUTTON_STYLE: CSSProperties = {
  padding: '8px 14px',
  borderRadius: '8px',
  border: '1px solid rgba(148, 163, 184, 0.4)',
  background: 'rgba(15, 23, 42, 0.7)',
  color: '#e2e8f0',
  letterSpacing: '0.08em',
  textTransform: 'uppercase',
  fontSize: '12px',
  cursor: 'pointer',
  transition: 'all 0.2s ease',
};

const PLAYBACK_BUTTON_ACTIVE: CSSProperties = {
  borderColor: ACCENT_COLOR,
  color: ACCENT_COLOR,
};

const HINT_STYLE: CSSProperties = {
  fontSize: '12px',
  color: '#a0aec0',
};

interface MicrophoneIconProps {
  active?: boolean;
}

function MicrophoneIcon({ active }: MicrophoneIconProps) {
  const fill = active ? ACCENT_COLOR : '#38bdf8';
  return (
    <svg width="30" height="30" viewBox="0 0 24 24" aria-hidden="true" focusable="false">
      <path
        d="M12 14a3 3 0 0 0 3-3V6a3 3 0 0 0-6 0v5a3 3 0 0 0 3 3z"
        fill={fill}
      />
      <path
        d="M19 11a7 7 0 0 1-14 0h2a5 5 0 0 0 10 0h2zm-7 5a1 1 0 0 1 1 1v2h-2v-2a1 1 0 0 1 1-1z"
        fill={active ? ACCENT_COLOR : 'rgba(56, 189, 248, 0.6)'}
      />
    </svg>
  );
}

export default function VoiceInterface({ sessionId, onMessageAppend }: VoiceInterfaceProps) {
  const {
    isRecording,
    isProcessing,
    isMicPressed,
    partialTranscript,
    finalTranscript,
    voiceNotice,
    autoPlayError,
    audioUrl,
    isAudioPlaying,
    isAudioMuted,
    beginVoiceRecording,
    finishVoiceRecording,
    handleToggleMute,
    handleReplay,
    handleStopPlayback,
  } = useVoiceInterface({ sessionId, onMessageAppend });

  const transcriptText = useMemo(() => {
    if (isRecording && partialTranscript) return partialTranscript;
    if (isProcessing) return partialTranscript || finalTranscript || '';
    return '';
  }, [isProcessing, isRecording, partialTranscript, finalTranscript]);

  const showTranscript = useMemo(() => {
    if (!transcriptText) return false;
    return isRecording || isProcessing;
  }, [isProcessing, isRecording, transcriptText]);

  const micActive = isMicPressed || isRecording || isProcessing;

  const handlePressStart = useCallback((event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
    event.preventDefault();
    beginVoiceRecording();
  }, [beginVoiceRecording]);

  const handlePressEnd = useCallback((event: MouseEvent<HTMLButtonElement> | TouchEvent<HTMLButtonElement>) => {
    event.preventDefault();
    finishVoiceRecording();
  }, [finishVoiceRecording]);

  const handleMouseLeave = useCallback(() => {
    finishVoiceRecording();
  }, [finishVoiceRecording]);

  return (
    <section style={CONTAINER_STYLE}>
      {voiceNotice ? <div style={STATUS_STYLE}>{voiceNotice}</div> : null}

      <div style={MIC_WRAPPER_STYLE}>
        <button
          type="button"
          style={micActive ? { ...MIC_BUTTON_BASE, ...MIC_BUTTON_ACTIVE } : { ...MIC_BUTTON_BASE, ...MIC_BUTTON_IDLE }}
          onMouseDown={handlePressStart}
          onMouseUp={handlePressEnd}
          onMouseLeave={handleMouseLeave}
          onTouchStart={handlePressStart}
          onTouchEnd={handlePressEnd}
          onTouchCancel={handlePressEnd}
          aria-pressed={isRecording}
          aria-label={isProcessing ? 'Procesando mensaje de voz' : 'Grabar mensaje de voz'}
          disabled={isProcessing && !isRecording}
          title={isProcessing ? 'Procesando mensaje de voz' : 'Mantener presionado para hablar'}
        >
          <MicrophoneIcon active={micActive} />
        </button>
        {(isRecording || isProcessing) ? (
          <span style={MIC_STATUS_STYLE}>
            {isProcessing ? 'Procesando...' : 'Grabando...'}
          </span>
        ) : null}
      </div>

      {showTranscript ? (
        <div style={TRANSCRIPT_CONTAINER_STYLE}>
          <span style={TRANSCRIPT_LABEL_STYLE}>Transcripcion</span>
          <p style={TRANSCRIPT_TEXT_STYLE}>{transcriptText}</p>
        </div>
      ) : null}

      {audioUrl ? (
        <div style={PLAYBACK_ROW_STYLE}>
          <button
            type="button"
            style={isAudioPlaying ? { ...PLAYBACK_BUTTON_STYLE, ...PLAYBACK_BUTTON_ACTIVE } : PLAYBACK_BUTTON_STYLE}
            onClick={isAudioPlaying ? handleStopPlayback : handleReplay}
          >
            {isAudioPlaying ? 'Detener' : 'Escuchar'}
          </button>
          <button
            type="button"
            style={isAudioMuted ? { ...PLAYBACK_BUTTON_STYLE, ...PLAYBACK_BUTTON_ACTIVE } : PLAYBACK_BUTTON_STYLE}
            onClick={handleToggleMute}
          >
            {isAudioMuted ? 'Activar sonido' : 'Silenciar'}
          </button>
        </div>
      ) : null}

      {autoPlayError ? <div style={HINT_STYLE}>{autoPlayError}</div> : null}
    </section>
  );
}










