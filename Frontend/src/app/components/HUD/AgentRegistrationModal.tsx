/**
 * Ruta: Frontend/src/app/components/HUD/AgentRegistrationModal.tsx
 * Descripción: Modal para registro dinámico de nuevos agentes
 * Estado: Activo
 * Autor: Claude Code
 * Última actualización: 2025-09-14
 */

'use client';

import React, { useState, useCallback } from 'react';
import { registerAgent, AgentRegistrationRequest } from '@/app/utils/orchestrator/client';
import styles from './AgentRegistrationModal.module.css';

interface AgentRegistrationModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSuccess: () => void;
  selectedRouter?: string | null;
}

export const AgentRegistrationModal: React.FC<AgentRegistrationModalProps> = ({
  isOpen,
  onClose,
  onSuccess,
  selectedRouter
}) => {
  const [formData, setFormData] = useState<AgentRegistrationRequest>({
    agent_name: '',
    display_name: '',
    description: '',
    agent_class_path: '',
    node_class_path: '',
    supported_intents: [],
    capabilities: {},
    metadata: {},
    enabled: true
  });

  const [intentsInput, setIntentsInput] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleInputChange = useCallback((field: keyof AgentRegistrationRequest, value: any) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    if (error) setError(null);
  }, [error]);

  const handleIntentsChange = useCallback((value: string) => {
    setIntentsInput(value);
    const intents = value.split(',').map(intent => intent.trim()).filter(Boolean);
    setFormData(prev => ({ ...prev, supported_intents: intents }));
  }, []);

  const validateForm = useCallback((): string | null => {
    if (!formData.agent_name.trim()) return 'Agent name is required';
    if (!formData.display_name.trim()) return 'Display name is required';
    if (!formData.description.trim()) return 'Description is required';
    if (!formData.agent_class_path.trim()) return 'Agent class path is required';
    if (!formData.node_class_path.trim()) return 'Node class path is required';
    if (formData.supported_intents.length === 0) return 'At least one intent is required';

    // Validate naming conventions
    if (!/^[a-z][a-z0-9_]*$/.test(formData.agent_name)) {
      return 'Agent name must start with lowercase letter and contain only lowercase letters, numbers, and underscores';
    }

    return null;
  }, [formData]);

  const handleSubmit = useCallback(async (e: React.FormEvent) => {
    e.preventDefault();

    const validationError = validateForm();
    if (validationError) {
      setError(validationError);
      return;
    }

    setIsSubmitting(true);
    setError(null);

    try {
      // Add version to metadata if not present
      const requestData = {
        ...formData,
        metadata: {
          version: '1.0.0',
          created_by: 'Agent Control Center',
          ...formData.metadata
        }
      };

      await registerAgent(requestData);

      // Reset form
      setFormData({
        agent_name: '',
        display_name: '',
        description: '',
        agent_class_path: '',
        node_class_path: '',
        supported_intents: [],
        capabilities: {},
        metadata: {},
        enabled: true
      });
      setIntentsInput('');

      onSuccess();
      onClose();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Registration failed');
    } finally {
      setIsSubmitting(false);
    }
  }, [formData, validateForm, onSuccess, onClose]);

  const handleClose = useCallback(() => {
    if (!isSubmitting) {
      setError(null);
      onClose();
    }
  }, [isSubmitting, onClose]);

  if (!isOpen) return null;

  return (
    <div className={styles.overlay} onClick={handleClose}>
      <div className={styles.modal} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <h2 className={styles.title}>REGISTER NEW AGENT</h2>
          {selectedRouter && (
            <div className={styles.routerInfo}>
              <span className={styles.routerLabel}>Target Router:</span>
              <span className={styles.routerName}>{selectedRouter}</span>
            </div>
          )}
          <button
            className={styles.closeButton}
            onClick={handleClose}
            disabled={isSubmitting}
          >
            ×
          </button>
        </div>

        <form className={styles.form} onSubmit={handleSubmit}>
          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Basic Information</h3>

            <div className={styles.field}>
              <label className={styles.label}>Agent Name *</label>
              <input
                type="text"
                className={styles.input}
                value={formData.agent_name}
                onChange={(e) => handleInputChange('agent_name', e.target.value)}
                placeholder="e.g. my_custom_agent"
                disabled={isSubmitting}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Display Name *</label>
              <input
                type="text"
                className={styles.input}
                value={formData.display_name}
                onChange={(e) => handleInputChange('display_name', e.target.value)}
                placeholder="e.g. My Custom Agent"
                disabled={isSubmitting}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Description *</label>
              <textarea
                className={styles.textarea}
                value={formData.description}
                onChange={(e) => handleInputChange('description', e.target.value)}
                placeholder="Describe what this agent does..."
                rows={3}
                disabled={isSubmitting}
              />
            </div>
          </div>

          <div className={styles.section}>
            <h3 className={styles.sectionTitle}>Technical Configuration</h3>

            <div className={styles.field}>
              <label className={styles.label}>Agent Class Path *</label>
              <input
                type="text"
                className={styles.input}
                value={formData.agent_class_path}
                onChange={(e) => handleInputChange('agent_class_path', e.target.value)}
                placeholder="e.g. ia_workspace.agentes.my_agent.handler.MyAgent"
                disabled={isSubmitting}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Node Class Path *</label>
              <input
                type="text"
                className={styles.input}
                value={formData.node_class_path}
                onChange={(e) => handleInputChange('node_class_path', e.target.value)}
                placeholder="e.g. src.infrastructure.langgraph.nodes.my_node.MyNode"
                disabled={isSubmitting}
              />
            </div>

            <div className={styles.field}>
              <label className={styles.label}>Supported Intents * (comma-separated)</label>
              <input
                type="text"
                className={styles.input}
                value={intentsInput}
                onChange={(e) => handleIntentsChange(e.target.value)}
                placeholder="e.g. custom_analysis, data_processing"
                disabled={isSubmitting}
              />
            </div>
          </div>

          {error && (
            <div className={styles.error}>
              <span className={styles.errorIcon}>⚠</span>
              {error}
            </div>
          )}

          <div className={styles.actions}>
            <button
              type="button"
              className={`${styles.button} ${styles.secondary}`}
              onClick={handleClose}
              disabled={isSubmitting}
            >
              CANCEL
            </button>
            <button
              type="submit"
              className={`${styles.button} ${styles.primary}`}
              disabled={isSubmitting}
            >
              {isSubmitting ? 'REGISTERING...' : 'REGISTER AGENT'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

export default AgentRegistrationModal;