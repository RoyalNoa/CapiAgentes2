import React, { useRef, useEffect, useMemo, useState } from 'react';
import { CHAT_THEME } from '../chatTheme';
import MessageBubble from './MessageBubble';
import ProcessingView from './ProcessingView';
import HolographicGrid from '../effects/HolographicGrid';

interface TaskStep {
  id: string;
  text: string;
  status: 'pending' | 'running' | 'complete' | 'error';
  timestamp?: number;
}

interface ProcessingMessage {
  id: string;
  agent: string;
  tasks: TaskStep[];
  startTime: number;
}

interface Message {
  id: string;
  role: 'user' | 'agent' | 'system';
  content: string;
  agent?: string;
  payload?: any;
}

interface MessageAreaProps {
  messages: Message[];
  loading: boolean;
}

export default function MessageArea({ messages, loading }: MessageAreaProps) {
  const [processingMessage, setProcessingMessage] = useState<ProcessingMessage | null>(null);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Transform messages for display
  const transformedMessages = useMemo(() =>
    messages.map((m, index) => ({
      id: `msg-${index}`,
      sender: m.role === 'user' ? 'user' : 'bot',
      text: m.payload?.respuesta || m.payload?.message || m.content,
      agent: (m as any).agent,
      timestamp: Date.now() - (messages.length - index) * 1000
    } as any)), [messages]);

  // Simulate agent task processing when loading
  useEffect(() => {
    if (loading && !processingMessage) {
      const mockTasks: TaskStep[] = [
        { id: '1', text: 'Analyzing financial data', status: 'running' },
        { id: '2', text: 'Processing branch metrics', status: 'pending' },
        { id: '3', text: 'Generating insights', status: 'pending' },
        { id: '4', text: 'Compiling response', status: 'pending' }
      ];

      setProcessingMessage({
        id: `proc-${Date.now()}`,
        agent: 'CAPI',
        tasks: mockTasks,
        startTime: Date.now()
      });

      // Simulate task progression
      const simulateProgress = async () => {
        for (let i = 0; i < mockTasks.length; i++) {
          await new Promise(resolve => setTimeout(resolve, 800 + Math.random() * 600));

          setProcessingMessage(prev => {
            if (!prev) return prev;
            const newTasks = [...prev.tasks];
            if (i > 0) newTasks[i - 1].status = 'complete';
            newTasks[i].status = 'running';
            return { ...prev, tasks: newTasks };
          });
        }
      };

      simulateProgress();
    } else if (!loading && processingMessage) {
      // Mark all tasks complete
      setProcessingMessage(prev => {
        if (!prev) return prev;
        const completedTasks = prev.tasks.map(task => ({ ...task, status: 'complete' as const }));
        return { ...prev, tasks: completedTasks };
      });

      // Remove processing message after delay
      setTimeout(() => setProcessingMessage(null), 1000);
    }
  }, [loading, processingMessage]);

  // Auto-scroll to bottom
  useEffect(() => {
    const element = messagesEndRef.current;
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'end' });
    }
  }, [transformedMessages.length]);

  return (
    <div style={{
      flex: 1,
      padding: '0',
      overflow: 'hidden',
      display: 'flex',
      flexDirection: 'column',
      background: `
        radial-gradient(ellipse at center,
          rgba(0, 15, 30, 0.8) 0%,
          rgba(0, 8, 17, 0.95) 70%,
          rgba(0, 4, 10, 0.98) 100%
        )
      `,
      position: 'relative'
    }}>
      <HolographicGrid />

      {/* Premium content area */}
      <div style={{
        flex: 1,
        overflowY: 'scroll',
        padding: '20px 24px',
        paddingRight: '16px',
        scrollbarWidth: 'thin',
        scrollbarColor: 'rgba(0, 255, 255, 0.4) transparent',
        position: 'relative',
        zIndex: 2
      }}>
        {transformedMessages.length === 0 && !processingMessage ? (
          <div style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            height: '100%',
            flexDirection: 'column',
            gap: '12px'
          }}>
            <div style={{
              width: '8px',
              height: '8px',
              backgroundColor: CHAT_THEME.colors.primary,
              borderRadius: '50%',
              boxShadow: `0 0 16px ${CHAT_THEME.colors.primary}`,
              animation: 'pulse 2s infinite'
            }} />
            <div style={{
              color: CHAT_THEME.colors.textMuted,
              fontSize: '12px',
              fontFamily: CHAT_THEME.fonts.ui,
              textAlign: 'center'
            }}>
              Ready to assist
            </div>
          </div>
        ) : (
          <>
            {transformedMessages.map((message) => (
              <MessageBubble key={message.id} message={message} />
            ))}

            <ProcessingView visible={!!processingMessage} processingMessage={processingMessage} />
          </>
        )}
        <div ref={messagesEndRef} />
      </div>
    </div>
  );
}