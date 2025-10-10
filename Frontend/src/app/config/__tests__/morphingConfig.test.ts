import { describe, it, expect } from 'vitest';
import {
  ORCHESTRATOR_SEQUENCE,
  NODE_PHRASES,
  AGENT_PHRASES,
  ANIMATION_CONFIG,
  getNodePhrase,
  getAgentPhrase,
  getOrchestratorSequence,
  getMorphingPhrasesForAction
} from '../morphingConfig';

describe('morphingConfig', () => {
  describe('ORCHESTRATOR_SEQUENCE', () => {
    it('should have the correct sequence order', () => {
      expect(ORCHESTRATOR_SEQUENCE).toEqual([
        'Identificando objetivo...',
        'Evaluando contexto...',
        'Razonando...',
        'Diseñando estrategia...',
        'Coordinando agentes...'
      ]);
    });

    it('should have exactly 5 phrases', () => {
      expect(ORCHESTRATOR_SEQUENCE).toHaveLength(5);
    });
  });

  describe('NODE_PHRASES', () => {
    it('should have phrases for all node types', () => {
      const expectedNodes = [
        'start', 'intent', 'react', 'reasoning',
        'supervisor', 'router', 'humanGate', 'assemble', 'finalize'
      ];

      expectedNodes.forEach(node => {
        expect(NODE_PHRASES[node as keyof typeof NODE_PHRASES]).toBeDefined();
        expect(NODE_PHRASES[node as keyof typeof NODE_PHRASES].length).toBeGreaterThan(0);
      });
    });

    it('should have at least 5 phrases per node', () => {
      Object.values(NODE_PHRASES).forEach(phrases => {
        expect(phrases.length).toBeGreaterThanOrEqual(5);
      });
    });
  });

  describe('AGENT_PHRASES', () => {
    it('should have phrases for all agent types', () => {
      const expectedAgents = [
        'capidatab', 'capielcajas', 'capidesktop', 'capinoticias',
        'summary', 'branch', 'anomaly', 'capi_gus'
      ];

      expectedAgents.forEach(agent => {
        expect(AGENT_PHRASES[agent as keyof typeof AGENT_PHRASES]).toBeDefined();
        expect(AGENT_PHRASES[agent as keyof typeof AGENT_PHRASES].length).toBeGreaterThan(0);
      });
    });

    it('should have exactly 5 phrases per agent', () => {
      Object.values(AGENT_PHRASES).forEach(phrases => {
        expect(phrases).toHaveLength(5);
      });
    });
  });

  describe('ANIMATION_CONFIG', () => {
    it('should have correct animation timings', () => {
      expect(ANIMATION_CONFIG.wordDuration).toBe(1000);
      expect(ANIMATION_CONFIG.shimmerPasses).toBe(2);
      expect(ANIMATION_CONFIG.timings.betweenWords).toBe(2000);
      expect(ANIMATION_CONFIG.timings.betweenEvents).toBe(300);
    });

    it('should have correct colors', () => {
      expect(ANIMATION_CONFIG.colors.initial).toBe('#ff9a00');
      expect(ANIMATION_CONFIG.colors.final).toBe('#00e5ff');
    });
  });

  describe('getNodePhrase', () => {
    it('should return a phrase from the specified node', () => {
      const phrase = getNodePhrase('intent');
      expect(NODE_PHRASES.intent).toContain(phrase);
    });

    it('should return different phrases on multiple calls (probabilistic)', () => {
      const phrases = new Set();
      // Try 50 times to get at least 2 different phrases
      for (let i = 0; i < 50; i++) {
        phrases.add(getNodePhrase('intent'));
      }
      // With 7 phrases available, we should get at least 2 different ones
      expect(phrases.size).toBeGreaterThan(1);
    });
  });

  describe('getAgentPhrase', () => {
    it('should return a phrase for known agents', () => {
      const phrase = getAgentPhrase('capidatab');
      expect(AGENT_PHRASES.capidatab).toContain(phrase);
    });

    it('should normalize agent names', () => {
      const phrase1 = getAgentPhrase('capi-datab');
      const phrase2 = getAgentPhrase('Capi_DataB');
      expect(AGENT_PHRASES.capidatab).toContain(phrase1);
      expect(AGENT_PHRASES.capidatab).toContain(phrase2);
    });

    it('should return fallback for unknown agents', () => {
      const phrase = getAgentPhrase('unknown-agent');
      expect(phrase).toBe('Procesando...');
    });
  });

  describe('getOrchestratorSequence', () => {
    it('should return standard sequence when not randomized', () => {
      const sequence = getOrchestratorSequence(false);
      expect(sequence).toEqual(ORCHESTRATOR_SEQUENCE);
    });

    it('should return sequence of same length when randomized', () => {
      const sequence = getOrchestratorSequence(true);
      expect(sequence).toHaveLength(5);
    });

    it('should return valid phrases when randomized', () => {
      const sequence = getOrchestratorSequence(true);

      // Check first phrase is from intent node
      expect(NODE_PHRASES.intent).toContain(sequence[0]);

      // Check second phrase is from react node
      expect(NODE_PHRASES.react).toContain(sequence[1]);

      // Check third phrase is from reasoning node
      expect(NODE_PHRASES.reasoning).toContain(sequence[2]);
    });
  });

  describe('getMorphingPhrasesForAction', () => {
    it('should map action types to correct node phrases', () => {
      const phrases = getMorphingPhrasesForAction('identify');
      expect(phrases).toEqual(NODE_PHRASES.intent);
    });

    it('should map analyze action to react node', () => {
      const phrases = getMorphingPhrasesForAction('analyze');
      expect(phrases).toEqual(NODE_PHRASES.react);
    });

    it('should return orchestrator sequence for unknown actions', () => {
      const phrases = getMorphingPhrasesForAction('unknown');
      expect(phrases).toEqual([...ORCHESTRATOR_SEQUENCE]);
    });

    it('should handle case-insensitive action types', () => {
      const phrases1 = getMorphingPhrasesForAction('IDENTIFY');
      const phrases2 = getMorphingPhrasesForAction('identify');
      expect(phrases1).toEqual(phrases2);
    });
  });
});