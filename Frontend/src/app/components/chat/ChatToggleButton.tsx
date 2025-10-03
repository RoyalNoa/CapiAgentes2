'use client';

import React from 'react';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';
import Image from 'next/image';

export default function ChatToggleButton() {
  const { isOpen, setIsOpen, messages, loading } = useGlobalChat();

  // Don't show toggle when chat is open (it has its own close button)
  if (isOpen) return null;

  const hasUnreadMessages = messages.length > 0;

  return (
    <button
      onClick={() => setIsOpen(true)}
      style={{
        position: 'absolute',
        zIndex: 1055,
        width: '48px',
        height: '48px',
        transition: 'all 0.3s ease',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        top: '15px',
        right: '20px',
        background: 'linear-gradient(135deg, rgba(0, 40, 80, 0.95) 0%, rgba(0, 20, 60, 0.95) 100%)',
        border: '2px solid rgba(0, 255, 255, 0.4)',
        borderRadius: '8px',
        boxShadow:
          '0 0 30px rgba(0, 255, 255, 0.4), ' +
          'inset 0 0 20px rgba(0, 255, 255, 0.05), ' +
          '0 8px 32px rgba(0, 0, 0, 0.6)',
        backdropFilter: 'blur(15px)',
        fontFamily: 'Orbitron, monospace',
        cursor: 'pointer'
      }}
      aria-label="Abrir chat global"
    >
      {/* Chat icon */}
      <div style={{ position: 'relative' }}>
        <Image
          src="/gpt.svg"
          alt="Chat"
          width={24}
          height={24}
          style={{
            filter: 'brightness(0) saturate(100%) invert(67%) sepia(77%) saturate(3501%) hue-rotate(164deg) brightness(103%) contrast(101%)',
            transition: 'transform 0.3s ease'
          }}
        />

        {/* Notification indicator */}
        {hasUnreadMessages && (
          <div
            style={{
              position: 'absolute',
              top: '-4px',
              right: '-4px',
              width: '12px',
              height: '12px',
              animation: 'pulse 2s infinite',
              background: '#ff3333',
              clipPath: 'polygon(0 0, 100% 25%, 75% 100%, 25% 75%)',
              boxShadow: '0 0 15px rgba(255, 51, 51, 0.8)'
            }}
          />
        )}

        {/* Loading indicator */}
        {loading && (
          <div
            style={{
              position: 'absolute',
              bottom: '-4px',
              right: '-4px',
              width: '12px',
              height: '12px',
              animation: 'spin 1s linear infinite',
              background: 'conic-gradient(from 0deg, #00ffff, #0099cc, #00ffff)',
              clipPath: 'polygon(50% 0%, 100% 50%, 50% 100%, 0% 50%)',
              boxShadow: '0 0 10px rgba(0, 255, 255, 0.6)'
            }}
          />
        )}
      </div>

      {/* Hover effects */}
      <div
        style={{
          position: 'absolute',
          inset: '0',
          opacity: '0',
          transition: 'opacity 0.3s ease',
          background: 'radial-gradient(circle at center, rgba(0, 255, 255, 0.2) 0%, transparent 70%)',
          borderRadius: '8px',
          pointerEvents: 'none'
        }}
      />
    </button>
  );
}