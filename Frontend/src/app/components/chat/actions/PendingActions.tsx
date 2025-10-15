import React, { useMemo, useState } from 'react';
import styles from './PendingActions.module.css';

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
  loading,
}: PendingActionsProps) {
  const [actionSubmitting, setActionSubmitting] = useState(false);

  const currentPendingAction = useMemo(() => pendingActions[0] ?? null, [pendingActions]);

  const pendingActionDetails = useMemo(() => {
    if (!currentPendingAction) return null;
    const payload = currentPendingAction.payload ?? {};
    const fileCandidate =
      payload.artifact_filename ??
      payload.filename ??
      payload.relative_path ??
      payload.path;
    const branchCandidate = payload.branch_name ?? payload.branch;

    return {
      fileName:
        typeof fileCandidate === 'string' && fileCandidate.trim() ? fileCandidate : null,
      branchName:
        typeof branchCandidate === 'string' && branchCandidate.trim() ? branchCandidate : null,
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
      console.error('No se pudo registrar la decision humana', error);
    } finally {
      setActionSubmitting(false);
    }
  };

  if (!currentPendingAction) return null;

  return (
    <div className={styles.container}>
<<<<<<< HEAD
      <div className={styles.header}>
        <div className={styles.indicator} />
        <span className={styles.label}>
          Acción requerida
        </span>
        <span className={styles.actionType}>
          {currentPendingAction.label}
        </span>
      </div>

      <div className={styles.description}>
        {approvalReason || '¿Deseas ejecutar la acción sugerida?'}
=======
      <div className={styles.description}>
        {approvalReason || 'Deseas ejecutar la accion sugerida?'}
>>>>>>> origin/develop
      </div>

      {pendingActionDetails?.fileName && (
        <div className={styles.detail}>
          Archivo sugerido:
          <span className={styles.detailValue}>
            {pendingActionDetails.fileName}
          </span>
        </div>
      )}

      {pendingActionDetails?.branchName && (
        <div className={styles.detail}>
          Sucursal:
          <span className={styles.detailNormal}>
            {pendingActionDetails.branchName}
          </span>
        </div>
      )}

<<<<<<< HEAD
      {pendingActionDetails?.summary && (
        <div className={styles.summary}>
          {pendingActionDetails.summary}
        </div>
      )}

=======
>>>>>>> origin/develop
      <div className={styles.buttons}>
        <button
          onClick={() => handleActionDecision(true)}
          disabled={isDecisionDisabled}
          className={`${styles.button} ${styles.approveButton}`}
        >
          Si, guardar
        </button>
        <button
          onClick={() => handleActionDecision(false)}
          disabled={isDecisionDisabled}
          className={`${styles.button} ${styles.rejectButton}`}
        >
          No, gracias
        </button>
      </div>

      {(actionSubmitting || loading) && (
        <div className={styles.loading}>
<<<<<<< HEAD
          Registrando decisión...
=======
          Registrando decision...
>>>>>>> origin/develop
        </div>
      )}
    </div>
  );
}
