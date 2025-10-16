import React from 'react';
import Image from 'next/image';
import { UserIcon } from '@heroicons/react/24/outline';
import styles from './MessageBubble.module.css';
import { getFriendlyAgentName, isOrchestrationAgent } from '@/app/utils/chatHelpers';

interface MessageBubbleProps {
  message: {
    id: string;
    sender: 'user' | 'bot';
    text: string;
    agent?: string;
    timestamp: number;
  };
}

export default function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.sender === 'user';

  const formatTime = (timestamp: number) => {
    return new Date(timestamp).toLocaleTimeString('es-ES', {
      hour: '2-digit',
      minute: '2-digit'
    });
  };

  // Obtener nombre descriptivo del agente
  const agentName = message.agent ? getFriendlyAgentName(message.agent) : 'Sistema';
  const normalizedAgent = (message.agent ?? '').toLowerCase();
  const isOrchestrator = Boolean(
    (message.agent && isOrchestrationAgent(message.agent)) ||
      normalizedAgent.includes('orquest') ||
      agentName.toLowerCase().includes('orquest')
  );
  // Primera letra para fallback avatars
  const avatarLetter = agentName.charAt(0).toUpperCase();

  return (
    <div className={`${styles.container} ${styles.entering}`}>
      {/* Header con avatar y timestamp */}
      <div className={`${styles.header} ${isUser ? styles.headerUser : styles.headerBot}`}>
        {!isUser && (
          <>
            <div className={`${styles.avatar} ${styles.avatarBot}`}>
              {isOrchestrator ? (
                <Image
                  src="/capi-comilon.png"
                  alt="Orquestador"
                  width={25}
                  height={25}
                  className={styles.avatarImage}
                />
              ) : (
                <span className={styles.avatarFallback}>{avatarLetter}</span>
              )}
            </div>
            <span className={styles.senderName}>
              {agentName}
            </span>
          </>
        )}

        <div className={`${styles.timestamp} ${isUser ? styles.timestampUser : styles.timestampBot}`}>
          {formatTime(message.timestamp)}
        </div>

        {isUser && (
          <>
            <span className={styles.senderName}>
              You
            </span>
            <div className={`${styles.avatar} ${styles.avatarUser}`}>
              <UserIcon className={styles.avatarIcon} aria-hidden="true" />
            </div>
          </>
        )}
      </div>

      {/* Contenido del mensaje */}
      <div className={`${styles.messageWrapper} ${isUser ? styles.messageWrapperUser : styles.messageWrapperBot}`}>
        <div className={`${styles.bubble} ${isUser ? styles.bubbleUser : styles.bubbleBot}`}>
          {/* Accent corner decorativo */}
          <div className={`${styles.cornerAccent} ${isUser ? styles.cornerAccentUser : styles.cornerAccentBot}`} />

          {message.text}
        </div>
      </div>
    </div>
  );
}