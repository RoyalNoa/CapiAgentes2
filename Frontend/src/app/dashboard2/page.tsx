'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  fetchSucursalSaldos,
  SucursalSaldo,
} from '@/app/services/saldosService';
import {
  CashComparisonRow,
  ComparisonView,
  SucursalCashComparison,
} from '@/app/components/dashboard/SucursalCashComparison';
import styles from './styles.module.css';

export default function Dashboard2Page() {
  const [sucursales, setSucursales] = useState<SucursalSaldo[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [activeWorkspace, setActiveWorkspace] = useState('cash-insights');
  const [activeAction, setActiveAction] = useState<ComparisonView>('compare');

  useEffect(() => {
    const load = async () => {
      try {
        setIsLoading(true);
        setError(null);
        const rows = await fetchSucursalSaldos();
        setSucursales(rows);
      } catch (err) {
        console.error('No se pudo cargar el dashboard 2:', err);
        setError('No se pudieron obtener los saldos de las sucursales.');
      } finally {
        setIsLoading(false);
      }
    };

    void load();
  }, []);

  const comparisonRows = useMemo<CashComparisonRow[]>(() => {
    return sucursales.map((item) => ({
      id: item.sucursal_id,
      name: item.sucursal_nombre || `Sucursal ${item.sucursal_numero}`,
      saldoTotal: item.saldo_total_sucursal ?? 0,
      cajaTeorica: item.caja_teorica_sucursal ?? 0,
    }));
  }, [sucursales]);

  const workspaceOptions = useMemo(
    () => [
      { value: 'cash-insights', label: 'Efectivo y disponibilidad' },
      { value: 'risk-monitor', label: 'Monitor de riesgo', disabled: true },
      { value: 'fx-desk', label: 'Mesa de cambios', disabled: true },
    ],
    [],
  );

  const actionOptions = useMemo(
    () => [
  { value: 'compare', label: 'Comparador de sucursales' },
  { value: 'radar', label: 'Radar de sucursales' },
  { value: 'alerts', label: 'Alertas de efectivo', disabled: true },
  { value: 'forecast', label: 'Proyección diaria', disabled: true },
    ],
    [],
  );

  return (
    <main className={styles.stage}>
      <video className={styles.backdrop} autoPlay muted loop playsInline>
        <source src="/videoplayback (1).webm" type="video/webm" />
        Tu navegador no soporta video HTML5.
      </video>
      <div className={styles.scrim} aria-hidden="true" />

      <div className={styles.overlay}>
        <section className={styles.panel}>
          <div className={styles.menuBar}>
            <div className={styles.actionMenus}>
              <div className={styles.selectGroup}>
                <span className={styles.selectLabel}>Espacio</span>
                <select
                  className={styles.selectControl}
                  value={activeWorkspace}
                  onChange={(event) => setActiveWorkspace(event.target.value)}
                >
                  {workspaceOptions.map((option) => (
                    <option key={option.value} value={option.value} disabled={option.disabled}>
                      {option.label}
                      {option.disabled ? ' · Próximamente' : ''}
                    </option>
                  ))}
                </select>
              </div>

              <div className={styles.selectGroup}>
                <span className={styles.selectLabel}>Acciones</span>
                <select
                  className={styles.selectControl}
                  value={activeAction}
                  onChange={(event) => setActiveAction(event.target.value as ComparisonView)}
                >
                  {actionOptions.map((option) => (
                    <option key={option.value} value={option.value} disabled={option.disabled}>
                      {option.label}
                      {option.disabled ? ' · Próximamente' : ''}
                    </option>
                  ))}
                </select>
              </div>
            </div>
          </div>

          {error ? (
            <div className={styles.errorCard}>
              <span className={styles.errorAccent} aria-hidden="true" />
              <div>
                <strong>Sincronización en pausa</strong>
                <p>{error}</p>
              </div>
            </div>
          ) : null}

          {activeWorkspace !== 'cash-insights' ? (
            <div className={styles.placeholderCard}>
              <strong>Espacio en construcción</strong>
              Estamos trabajando en esta vista para integrarla al tablero de operaciones financieras.
            </div>
          ) : activeAction === 'compare' || activeAction === 'radar' ? (
            <SucursalCashComparison data={comparisonRows} isLoading={isLoading} view={activeAction} />
          ) : (
            <div className={styles.placeholderCard}>
              <strong>Funcionalidad en preparación</strong>
              Próximamente vas a poder habilitar herramientas adicionales sobre el flujo de efectivo.
            </div>
          )}
        </section>
      </div>
    </main>
  );
}
