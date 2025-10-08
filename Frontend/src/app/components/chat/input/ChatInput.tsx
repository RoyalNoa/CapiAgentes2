import React, { useState, useCallback, ReactNode } from 'react';
import styles from './ChatInput.module.css';

interface ChatInputProps {
  onSend: (text: string) => Promise<void>;
  loading: boolean;
  alertContext?: {
    text: string;
    context: any;
  } | null;
  onAcceptContext?: () => void;
  onRejectContext?: () => void;
  rightSlot?: ReactNode;
}

export default function ChatInput({
  onSend,
  loading,
  alertContext,
  onAcceptContext,
  onRejectContext,
  rightSlot
}: ChatInputProps) {
  const [input, setInput] = useState('');

  const handleSend = useCallback(async () => {
    if (!input.trim() || loading) return;

    const inputToSend = input.trim();
    setInput('');

    try {
      await onSend(inputToSend);
    } catch (error: any) {
      setInput(inputToSend);
    }
  }, [input, loading, onSend]);

  const handleSendClick = useCallback(() => {
    void handleSend();
  }, [handleSend]);

  const handleInputKeyDown = useCallback((e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSend();
    }
  }, [handleSend]);

  const canSend = input.trim().length > 0 && !loading;

  return (
    <div className={`${styles.container} ${loading ? styles.loading : ''}`}>
      {/* Borde decorativo superior */}
      <div className={styles.topAccent} />

      {/* Contexto de alerta */}
      {alertContext && (
        <div className={styles.alertContext}>
          {/* Header del contexto */}
          <div className={styles.alertHeader}>
            <div className={styles.alertIndicator} />
            <span className={styles.alertLabel}>
              Alert Context Available
            </span>
            <span className={styles.alertSource}>
              From: {alertContext.context?.agent || 'System'}
            </span>
          </div>

          {/* Vista previa del contexto */}
          <div className={styles.alertPreview}>
            {alertContext.text}
          </div>

          {/* Botones de acción */}
          <div className={styles.alertControls}>
            <button
              onClick={onRejectContext}
              className={styles.alertButton}
            >
              Dismiss
            </button>
            <button
              onClick={onAcceptContext}
              className={`${styles.alertButton} ${styles.accept}`}
            >
              Use Context
            </button>
          </div>
        </div>
      )}

      {/* Contenedor del input */}
      <div className={styles.inputWrapper}>
        {/* Campo de entrada */}
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={handleInputKeyDown}
          placeholder={alertContext ? 'Modifica el contexto y envía...' : 'Escribe tu consulta...'}
          disabled={loading}
          className={styles.inputField}
        />

        {/* Botón de enviar */}
        <button
          type="button"
          onClick={handleSendClick}
          disabled={!canSend}
          className={styles.sendButton}
        >
          <SendIcon />
        </button>

        {/* Slot derecho para botones adicionales */}
        {rightSlot && (
          <div className={styles.rightSlot}>
            {rightSlot}
          </div>
        )}
      </div>
    </div>
  );
}

const SendIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    aria-hidden="true"
    focusable="false"
    fill="currentColor"
  >
    <path d="M3.172 20.828 21 12 3.172 3.172l-.003 7.657 10.059 1.171-10.056 1.171z" />
  </svg>
);