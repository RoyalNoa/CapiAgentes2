import React, { useMemo, useState } from 'react';
import { CHAT_THEME } from '../chatTheme';

interface PendingAction {
  id: string;
  label: string;
  payload?: any;
  interrupt_id?: string | null;
  raw?: any;
}

interface PendingActionsProps {
  pendingActions: PendingAction[];
  approvalReason: string | null;
  onSubmitAction: (params: { actionId: string; approved: boolean }) => Promise<void>;
  loading: boolean;
}

export default function PendingActions({
  pendingActions,
  approvalReason,
  onSubmitAction,
  loading
}: PendingActionsProps) {
  const [actionSubmitting, setActionSubmitting] = useState(false);

  const currentPendingAction = useMemo(() => pendingActions[0] ?? null, [pendingActions]);

  const pendingActionDetails = useMemo(() => {
    if (!currentPendingAction) return null;
    const payload = currentPendingAction.payload ?? {};
    const fileCandidate = payload.artifact_filename ?? payload.filename ?? payload.relative_path ?? payload.path;
    const branchCandidate = payload.branch_name ?? payload.branch;
    const summaryCandidate = typeof payload.summary === 'string' && payload.summary.trim() ? payload.summary : null;
    const hypothesisCandidate = typeof payload.hypothesis === 'string' && payload.hypothesis.trim() ? payload.hypothesis : null;
    return {
      fileName: typeof fileCandidate === 'string' && fileCandidate.trim() ? fileCandidate : null,
      branchName: typeof branchCandidate === 'string' && branchCandidate.trim() ? branchCandidate : null,
      summary: summaryCandidate ?? hypothesisCandidate,
    };
  }, [currentPendingAction]);

  const isDecisionDisabled = actionSubmitting || loading;

  const handleActionDecision = async (approved: boolean) => {
    if (!currentPendingAction) {
      return;
    }

    try {
      setActionSubmitting(true);
      await onSubmitAction({ actionId: currentPendingAction.id, approved });
    } catch (error) {
      console.error('No se pudo registrar la decisión humana', error);
    } finally {
      setActionSubmitting(false);
    }
  };

  if (!currentPendingAction) return null;

  return (
    <div
      style={{
        margin: '12px 20px 0',
        padding: '14px 16px',
        borderRadius: '8px',
        border: `1px solid ${CHAT_THEME.colors.primary}40`,
        background: 'linear-gradient(135deg, rgba(0, 255, 255, 0.08), rgba(0, 255, 255, 0.03))',
        boxShadow: '0 6px 18px rgba(0, 0, 0, 0.35)',
        display: 'flex',
        flexDirection: 'column',
        gap: '10px'
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <div
          style={{
            width: '6px',
            height: '6px',
            borderRadius: '50%',
            background: CHAT_THEME.colors.primary,
            boxShadow: `0 0 10px ${CHAT_THEME.colors.primary}80`,
            animation: 'pulse 2s infinite'
          }}
        />
        <span
          style={{
            fontSize: '11px',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            fontFamily: CHAT_THEME.fonts.heading,
            color: CHAT_THEME.colors.primaryAlt
          }}
        >
          Acción requerida
        </span>
        <span
          style={{
            marginLeft: 'auto',
            fontSize: '10px',
            color: CHAT_THEME.colors.textMuted,
            fontFamily: CHAT_THEME.fonts.ui
          }}
        >
          {currentPendingAction.label}
        </span>
      </div>

      <div
        style={{
          fontSize: '11px',
          color: CHAT_THEME.colors.text,
          fontFamily: CHAT_THEME.fonts.ui,
          lineHeight: '1.4'
        }}
      >
        {approvalReason || '¿Deseas ejecutar la acción sugerida?'}
      </div>

      {pendingActionDetails?.fileName && (
        <div
          style={{
            fontSize: '10px',
            color: CHAT_THEME.colors.textMuted,
            fontFamily: CHAT_THEME.fonts.ui
          }}
        >
          Archivo sugerido:
          <span style={{ color: CHAT_THEME.colors.primaryAlt, marginLeft: '4px' }}>{pendingActionDetails.fileName}</span>
        </div>
      )}

      {pendingActionDetails?.branchName && (
        <div
          style={{
            fontSize: '10px',
            color: CHAT_THEME.colors.textMuted,
            fontFamily: CHAT_THEME.fonts.ui
          }}
        >
          Sucursal:
          <span style={{ color: CHAT_THEME.colors.text, marginLeft: '4px' }}>{pendingActionDetails.branchName}</span>
        </div>
      )}

      {pendingActionDetails?.summary && (
        <div
          style={{
            fontSize: '10px',
            color: CHAT_THEME.colors.text,
            fontFamily: CHAT_THEME.fonts.ui,
            lineHeight: '1.5'
          }}
        >
          {pendingActionDetails.summary}
        </div>
      )}

      <div style={{ display: 'flex', gap: '12px', justifyContent: 'flex-end' }}>
        <button
          onClick={() => handleActionDecision(true)}
          disabled={isDecisionDisabled}
          style={{
            padding: '6px 14px',
            borderRadius: '4px',
            border: `1px solid ${CHAT_THEME.colors.primary}60`,
            background: `linear-gradient(135deg, ${CHAT_THEME.colors.primary}30, ${CHAT_THEME.colors.primary}10)`,
            color: CHAT_THEME.colors.primary,
            fontSize: '11px',
            fontFamily: CHAT_THEME.fonts.ui,
            cursor: isDecisionDisabled ? 'not-allowed' : 'pointer',
            opacity: isDecisionDisabled ? 0.6 : 1,
            transition: 'all 0.2s ease'
          }}
        >
          Sí, guardar
        </button>
        <button
          onClick={() => handleActionDecision(false)}
          disabled={isDecisionDisabled}
          style={{
            padding: '6px 14px',
            borderRadius: '4px',
            border: '1px solid rgba(255, 107, 107, 0.5)',
            background: 'rgba(255, 107, 107, 0.12)',
            color: '#ff6b6b',
            fontSize: '11px',
            fontFamily: CHAT_THEME.fonts.ui,
            cursor: isDecisionDisabled ? 'not-allowed' : 'pointer',
            opacity: isDecisionDisabled ? 0.6 : 1,
            transition: 'all 0.2s ease'
          }}
        >
          No, gracias
        </button>
      </div>

      {(actionSubmitting || loading) && (
        <div style={{ textAlign: 'right', fontSize: '9px', color: CHAT_THEME.colors.textMuted }}>
          Registrando decisión...
        </div>
      )}
    </div>
  );
}