import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import {
  isAgentEvent,
  getEventPayload,
  getAgentName,
  filterAgentEvents,
  filterRegularMessages,
  getActionType,
  normalizeAgentName,
  isOrchestrationAgent,
  getConditionalClass,
  getMorphingClasses,
  getEventClasses,
  getFriendlyAgentName,
  buildAgentTaskEvents,
  TimerManager
} from '../chatHelpers';
import type { Message } from '@/app/types/chat';

describe('chatHelpers', () => {
  describe('isAgentEvent', () => {
    it('should return true for agent_event type', () => {
      const payload = { type: 'agent_event' };
      expect(isAgentEvent(payload as any)).toBe(true);
    });

    it('should return true for agent_event_header type', () => {
      const payload = { type: 'agent_event_header' };
      expect(isAgentEvent(payload as any)).toBe(true);
    });

    it('should return false for other types', () => {
      const payload = { type: 'regular_message' };
      expect(isAgentEvent(payload as any)).toBe(false);
    });

    it('should return false for undefined payload', () => {
      expect(isAgentEvent(undefined)).toBe(false);
    });
  });

  describe('getEventPayload', () => {
    it('should extract payload from message', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        payload: { type: 'agent_event' }
      };
      expect(getEventPayload(msg)).toEqual({ type: 'agent_event' });
    });

    it('should return undefined for missing payload', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test'
      };
      expect(getEventPayload(msg)).toBeUndefined();
    });
  });

  describe('getAgentName', () => {
    it('should extract agent name from payload actor', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        payload: { actor: 'CapiDataB' }
      };
      expect(getAgentName(msg)).toBe('capidatab');
    });

    it('should extract agent name from message agent field', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        agent: 'Summary'
      };
      expect(getAgentName(msg)).toBe('summary');
    });

    it('should return empty string if no agent found', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test'
      };
      expect(getAgentName(msg)).toBe('');
    });
  });

  describe('normalizeAgentName', () => {
    it('should normalize agent names correctly', () => {
      expect(normalizeAgentName('Capi-DataB')).toBe('capidatab');
      expect(normalizeAgentName('El_Cajas')).toBe('elcajas');
      expect(normalizeAgentName('SUMMARY')).toBe('summary');
    });
  });

  describe('isOrchestrationAgent', () => {
    it('should identify orchestration agents', () => {
      expect(isOrchestrationAgent('orchestrator')).toBe(true);
      expect(isOrchestrationAgent('supervisor')).toBe(true);
      expect(isOrchestrationAgent('router')).toBe(true);
    });

    it('should return false for regular agents', () => {
      expect(isOrchestrationAgent('summary')).toBe(false);
      expect(isOrchestrationAgent('capidatab')).toBe(false);
    });
  });

  describe('filterAgentEvents', () => {
    it('should filter only agent events excluding orchestration', () => {
      const messages: Message[] = [
        {
          id: '1',
          sender: 'bot',
          text: 'test1',
          payload: { type: 'agent_event', actor: 'summary' }
        },
        {
          id: '2',
          sender: 'bot',
          text: 'test2',
          payload: { type: 'agent_event', actor: 'orchestrator' }
        },
        {
          id: '3',
          sender: 'user',
          text: 'test3'
        }
      ];

      const filtered = filterAgentEvents(messages);
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('1');
    });
  });

  describe('filterRegularMessages', () => {
    it('should filter only regular messages with text', () => {
      const messages: Message[] = [
        {
          id: '1',
          sender: 'bot',
          text: 'regular message',
        },
        {
          id: '2',
          sender: 'bot',
          text: 'agent event',
          payload: { type: 'agent_event' }
        },
        {
          id: '3',
          sender: 'user',
          text: ''
        }
      ];

      const filtered = filterRegularMessages(messages);
      expect(filtered).toHaveLength(1);
      expect(filtered[0].id).toBe('1');
    });
  });

  describe('getActionType', () => {
    it('should extract action from payload data', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        payload: { data: { action: 'database_query' } }
      };
      expect(getActionType(msg)).toBe('database_query');
    });

    it('should map agent names to action types', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        payload: { actor: 'capidatab' }
      };
      expect(getActionType(msg)).toBe('database_query');
    });

    it('should return default action for unknown agents', () => {
      const msg: Message = {
        id: '1',
        sender: 'bot',
        text: 'test',
        payload: { actor: 'unknown' }
      };
      expect(getActionType(msg)).toBe('agent_processing');
    });
  });

  describe('getConditionalClass', () => {
    it('should build class string from conditions', () => {
      const result = getConditionalClass('base', {
        'active': true,
        'disabled': false,
        'highlighted': true
      });
      expect(result).toBe('base active highlighted');
    });

    it('should return only base class when no conditions are true', () => {
      const result = getConditionalClass('base', {
        'active': false,
        'disabled': false
      });
      expect(result).toBe('base');
    });
  });

  describe('getMorphingClasses', () => {
    const mockStyles = {
      morphingText: 'morphing-text',
      withShimmer: 'with-shimmer',
      waitingBatch: 'waiting-batch',
      final: 'final'
    };

    it('should return shimmer class for shimmer phase', () => {
      const result = getMorphingClasses(mockStyles, 'shimmer');
      expect(result).toContain('with-shimmer');
    });

    it('should return waiting class for waiting phase', () => {
      const result = getMorphingClasses(mockStyles, 'waiting');
      expect(result).toContain('waiting-batch');
    });

    it('should return final class for final phase', () => {
      const result = getMorphingClasses(mockStyles, 'final');
      expect(result).toContain('final');
    });
  });

  describe('getEventClasses', () => {
    const mockStyles = {
      eventContainer: 'event-container',
      eventContainerActive: 'event-container-active',
      eventBullet: 'event-bullet',
      eventBulletActive: 'event-bullet-active',
      eventBulletCompleted: 'event-bullet-completed',
      eventText: 'event-text',
      eventTextActive: 'event-text-active',
      eventTextCompleted: 'event-text-completed'
    };

    it('should return classes for active event', () => {
      const { containerClass, bulletClass, textClass } = getEventClasses(mockStyles, 'active');
      expect(containerClass).toContain('event-container-active');
      expect(bulletClass).toContain('event-bullet-active');
      expect(textClass).toContain('event-text-active');
    });

    it('should return classes for completed event', () => {
      const { containerClass, bulletClass, textClass } = getEventClasses(mockStyles, 'completed');
      expect(bulletClass).toContain('event-bullet-completed');
      expect(textClass).toContain('event-text-completed');
    });

    it('should return base classes for pending event', () => {
      const { containerClass, bulletClass, textClass } = getEventClasses(mockStyles, 'pending');
      expect(containerClass).toBe('event-container');
      expect(bulletClass).toBe('event-bullet');
      expect(textClass).toBe('event-text');
    });
  });

  describe('getFriendlyAgentName', () => {
    it('should return friendly names for known agents', () => {
      expect(getFriendlyAgentName('capidatab')).toBe('Capi DataB');
      expect(getFriendlyAgentName('summary')).toBe('Capi Summary');
    });

    it('should return Sistema for empty agent', () => {
      expect(getFriendlyAgentName('')).toBe('Sistema');
    });

    it('should return formatted name for unknown agents', () => {
      expect(getFriendlyAgentName('unknown-agent')).toBe('Unknown Agent');
    });
  });


  describe('buildAgentTaskEvents', () => {
    it('should build events from agent messages when available', () => {
      const agentEvents: Message[] = [
        {
          id: 'evt-1',
          sender: 'bot',
          role: 'agent',
          content: '',
          payload: {
            type: 'agent_event',
            actor: 'capi_datab',
            event: { data: { summary: 'Consultando base de datos', detail: 'Fila 1 procesada' } }
          }
        } as Message
      ];

      const events = buildAgentTaskEvents({ agentEvents });
      expect(events).toHaveLength(1);
      expect(events[0].primaryText).toBe('Consultando base de datos');
    });

    it('should fall back to shared artifacts when agent events are missing', () => {
      const finalMessage = {
        payload: {
          response_metadata: {
            shared_artifacts: {
              capi_datab: {
                operation: {
                  operation: 'select',
                  table: 'public.test_table',
                  metadata: { branch: { branch_name: 'Palermo' } }
                },
                rowcount: 1,
                export_file: '/tmp/DataB_file.json'
              },
              capi_elcajas: {
                analysis: [{ headline: 'Palermo: deficit de 12,000 ARS' }],
                alerts: [{ summary: 'Palermo: deficit de 12,000 ARS' }],
                recommendation_files: [{ filename: 'recommendation_SUC-404.json' }]
              }
            }
          }
        }
      } as Message;

      const events = buildAgentTaskEvents({ agentEvents: [], finalMessage });
      const primaryTexts = events.map(event => event.primaryText);

      expect(primaryTexts.some(text => text.includes('Consultando'))).toBe(true);
      expect(primaryTexts.some(text => text.includes('Procesando 1 resultado'))).toBe(true);
      expect(primaryTexts.some(text => text.includes('Exportando resultados'))).toBe(true);
      expect(primaryTexts.some(text => text.includes('Generando alerta'))).toBe(true);
    });

    it('should return empty array when no data is available', () => {
      const events = buildAgentTaskEvents({ agentEvents: [], finalMessage: { payload: {} } as Message });
      expect(events).toHaveLength(0);
    });
  });

  describe('TimerManager', () => {
    let timerManager: TimerManager;

    beforeEach(() => {
      vi.useFakeTimers();
      timerManager = new TimerManager();
    });

    afterEach(() => {
      vi.restoreAllMocks();
    });

    it('should set and execute timer callback', () => {
      const callback = vi.fn();
      timerManager.set('test', callback, 1000);

      expect(callback).not.toHaveBeenCalled();
      vi.advanceTimersByTime(1000);
      expect(callback).toHaveBeenCalledTimes(1);
    });

    it('should clear existing timer when setting new one with same key', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      timerManager.set('test', callback1, 1000);
      timerManager.set('test', callback2, 500);

      vi.advanceTimersByTime(500);
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).toHaveBeenCalledTimes(1);
    });

    it('should clear specific timer', () => {
      const callback = vi.fn();
      timerManager.set('test', callback, 1000);
      timerManager.clear('test');

      vi.advanceTimersByTime(1000);
      expect(callback).not.toHaveBeenCalled();
    });

    it('should clear all timers', () => {
      const callback1 = vi.fn();
      const callback2 = vi.fn();

      timerManager.set('test1', callback1, 1000);
      timerManager.set('test2', callback2, 1500);
      timerManager.clearAll();

      vi.advanceTimersByTime(1500);
      expect(callback1).not.toHaveBeenCalled();
      expect(callback2).not.toHaveBeenCalled();
    });
  });
});



