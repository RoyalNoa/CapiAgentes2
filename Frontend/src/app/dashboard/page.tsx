/**
 * Dashboard Executive Page - Panel de control con estética inspirada en Agentes.
 */

'use client';

import React, {
  useCallback,
  useEffect,
  useMemo,
  useState,
} from 'react';
import { format } from 'date-fns';
import { es } from 'date-fns/locale';

import { CashFlowChart } from '../components/dashboard/CashFlowChart';
import { DenominationDistribution } from '../components/dashboard/DenominationDistribution';
import { dashboardService, DashboardData } from '../services/dashboardService';
import {
  SucursalSaldo,
  DispositivoSaldo,
  fetchSucursalSaldos,
  fetchDispositivoSaldos,
  updateSucursalSaldo,
  updateDispositivoSaldo,
  deleteSucursalSaldo,
  deleteDispositivoSaldo,
} from '../services/saldosService';
import {
  CashPolicy,
  fetchCashPolicies,
  updateCashPolicy,
} from '../services/cashPoliciesService';

import styles from './Dashboard.module.css';

type EditableSucursal = SucursalSaldo & {
  __saving?: boolean;
};

type EditableDispositivo = DispositivoSaldo & {
  __saving?: boolean;
};

interface EditableCashPolicy extends CashPolicy {
  __saving?: boolean;
  __error?: string | null;
}

type SortDirection = 'asc' | 'desc';

type ToastMessage = {
  id: string;
  text: string;
};

type SucursalColumnKey = keyof SucursalSaldo;
type DispositivoColumnKey = keyof DispositivoSaldo;

interface ColumnConfig<T extends string> {
  key: T;
  label: string;
  type?: 'text' | 'number' | 'datetime';
  step?: string;
  editable?: boolean;
  sortable?: boolean;
}

const editableSucursalFields: ReadonlyArray<SucursalColumnKey> = [
  'saldo_total_sucursal',
  'caja_teorica_sucursal',
];

const editableDispositivoFields: ReadonlyArray<DispositivoColumnKey> = [
  'saldo_total',
  'caja_teorica',
];

const editablePolicyFields: ReadonlyArray<keyof CashPolicy> = [
  'max_surplus_pct',
  'max_deficit_pct',
  'min_buffer_amount',
  'daily_withdrawal_limit',
  'daily_deposit_limit',
  'reload_lead_hours',
  'sla_hours',
  'truck_fixed_cost',
  'truck_variable_cost_per_kg',
  'notes',
];

const sucursalColumns: ColumnConfig<SucursalColumnKey>[] = [
  { key: 'sucursal_id', label: 'ID Sucursal' },
  { key: 'sucursal_numero', label: 'Número', type: 'number' },
  { key: 'sucursal_nombre', label: 'Nombre' },
  { key: 'saldo_total_sucursal', label: 'Saldo Total', type: 'number', step: '0.01', editable: true },
  { key: 'caja_teorica_sucursal', label: 'Caja Teórica', type: 'number', step: '0.01', editable: true },
  { key: 'total_atm', label: 'Total ATM', type: 'number', step: '0.01', sortable: false },
  { key: 'total_ats', label: 'Total ATS', type: 'number', step: '0.01', sortable: false },
  { key: 'total_tesoro', label: 'Total Tesoro', type: 'number', step: '0.01', sortable: false },
  { key: 'total_cajas_ventanilla', label: 'Cajas Ventanilla', type: 'number', step: '0.01', sortable: false },
  { key: 'total_buzon_depositos', label: 'Buzón Depósitos', type: 'number', step: '0.01', sortable: false },
  { key: 'direccion_sucursal', label: 'Dirección' },
  { key: 'latitud', label: 'Latitud', type: 'number', step: '0.000001', sortable: false },
  { key: 'longitud', label: 'Longitud', type: 'number', step: '0.000001', sortable: false },
  { key: 'observacion', label: 'Observación', sortable: false },
  { key: 'medido_en', label: 'Medido en', type: 'datetime' },
];

const dispositivoColumns: ColumnConfig<DispositivoColumnKey>[] = [
  { key: 'sucursal_id', label: 'Sucursal ID' },
  { key: 'dispositivo_id', label: 'Dispositivo ID' },
  { key: 'tipo_dispositivo', label: 'Tipo' },
  { key: 'saldo_total', label: 'Saldo Total', type: 'number', step: '0.01', editable: true },
  { key: 'caja_teorica', label: 'Caja Teórica', type: 'number', step: '0.01', editable: true },
  { key: 'cant_d1', label: 'Cant D1', type: 'number', sortable: false },
  { key: 'cant_d2', label: 'Cant D2', type: 'number', sortable: false },
  { key: 'cant_d3', label: 'Cant D3', type: 'number', sortable: false },
  { key: 'cant_d4', label: 'Cant D4', type: 'number', sortable: false },
  { key: 'direccion', label: 'Dirección' },
  { key: 'latitud', label: 'Latitud', type: 'number', step: '0.000001', sortable: false },
  { key: 'longitud', label: 'Longitud', type: 'number', step: '0.000001', sortable: false },
  { key: 'observacion', label: 'Observación', sortable: false },
  { key: 'medido_en', label: 'Medido en', type: 'datetime' },
];

const policyColumns: Array<{ key: keyof CashPolicy; label: string; type: 'number' | 'text'; step?: string }> = [
  { key: 'max_surplus_pct', label: 'Exceso permitido', type: 'number', step: '0.01' },
  { key: 'max_deficit_pct', label: 'Déficit permitido', type: 'number', step: '0.01' },
  { key: 'min_buffer_amount', label: 'Colchón mínimo', type: 'number', step: '1' },
  { key: 'daily_withdrawal_limit', label: 'Límite retiro diario', type: 'number', step: '1' },
  { key: 'daily_deposit_limit', label: 'Límite depósito diario', type: 'number', step: '1' },
  { key: 'reload_lead_hours', label: 'Horas anticipación', type: 'number', step: '1' },
  { key: 'sla_hours', label: 'SLA objetivo (hs)', type: 'number', step: '1' },
  { key: 'truck_fixed_cost', label: 'Costo fijo camión', type: 'number', step: '1' },
  { key: 'truck_variable_cost_per_kg', label: 'Tarifa por kg', type: 'number', step: '1' },
  { key: 'notes', label: 'Notas', type: 'text' },
];

const numberFormatter = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 2,
  minimumFractionDigits: 0,
});

const formatDateTimeDisplay = (value?: string | null) => {
  if (!value) return '-';
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return '-';
  try {
    return format(date, 'dd/MM/yy HH:mm', { locale: es });
  } catch (error) {
    return date.toLocaleString('es-AR');
  }
};

const formatCellValue = (value: unknown, type?: 'text' | 'number' | 'datetime') => {
  if (value === null || value === undefined || value === '') {
    return '-';
  }
  if (type === 'number') {
    const numeric = typeof value === 'number' ? value : Number(value);
    if (!Number.isFinite(numeric)) {
      return String(value);
    }
    return numberFormatter.format(numeric);
  }
  if (type === 'datetime') {
    return formatDateTimeDisplay(String(value));
  }
  return String(value);
};

const sortData = <T extends Record<string, unknown>, K extends string>(
  rows: T[],
  sort: { column: K | null; direction: SortDirection },
  columns: ColumnConfig<K>[],
): T[] => {
  const columnKey = sort.column;
  if (!columnKey) return rows;
  const column = columns.find((item) => item.key === columnKey);
  if (!column || column.sortable === false) return rows;

  const sorted = [...rows];
  sorted.sort((a, b) => {
    const aValue = a[columnKey];
    const bValue = b[columnKey];
    const isANullish = aValue === null || aValue === undefined || aValue === '';
    const isBNullish = bValue === null || bValue === undefined || bValue === '';
    if (isANullish && isBNullish) return 0;
    if (isANullish) return 1;
    if (isBNullish) return -1;

    let comparison = 0;
    if (column.type === 'number') {
      const aNumber = typeof aValue === 'number' ? aValue : Number(aValue);
      const bNumber = typeof bValue === 'number' ? bValue : Number(bValue);
      comparison = (Number.isFinite(aNumber) ? aNumber : 0) - (Number.isFinite(bNumber) ? bNumber : 0);
    } else if (column.type === 'datetime') {
      const aTime = new Date(String(aValue)).getTime();
      const bTime = new Date(String(bValue)).getTime();
      comparison = (Number.isFinite(aTime) ? aTime : 0) - (Number.isFinite(bTime) ? bTime : 0);
    } else {
      comparison = String(aValue).localeCompare(String(bValue));
    }

    if (comparison === 0) return 0;
    return sort.direction === 'asc' ? comparison : -comparison;
  });

  return sorted;
};

const ExecutiveDashboard: React.FC = () => {
  const [data, setData] = useState<DashboardData | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [error, setError] = useState<string | null>(null);

  const [sucursalRows, setSucursalRows] = useState<EditableSucursal[]>([]);
  const [dispositivoRows, setDispositivoRows] = useState<EditableDispositivo[]>([]);
  const [tablesLoading, setTablesLoading] = useState(true);
  const [tablesError, setTablesError] = useState<string | null>(null);

  const [sucursalSort, setSucursalSort] = useState<{ column: SucursalColumnKey | null; direction: SortDirection }>({
    column: null,
    direction: 'asc',
  });
  const [dispositivoSort, setDispositivoSort] = useState<{ column: DispositivoColumnKey | null; direction: SortDirection }>({
    column: null,
    direction: 'asc',
  });

  const [cashPolicies, setCashPolicies] = useState<EditableCashPolicy[]>([]);
  const [cashPoliciesLoading, setCashPoliciesLoading] = useState(true);
  const [cashPoliciesError, setCashPoliciesError] = useState<string | null>(null);

  const [toasts, setToasts] = useState<ToastMessage[]>([]);

  const pushToast = useCallback((text: string) => {
    const id = crypto.randomUUID();
    setToasts((prev) => [...prev, { id, text }]);
    setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 4000);
  }, []);

  const loadDashboardData = useCallback(async (showLoading = true) => {
    try {
      if (showLoading) setIsLoading(true);
      setError(null);
      const dashboardData = await dashboardService.getDashboardData();
      setData(dashboardData);
      setLastUpdated(new Date());
    } catch (err) {
      console.error('Error loading dashboard:', err);
      setError('Error al cargar los datos del dashboard');
      pushToast('Error al cargar los datos del dashboard');
    } finally {
      setIsLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    void loadDashboardData();
  }, [loadDashboardData]);

  const loadSaldos = useCallback(async () => {
    setTablesLoading(true);
    setTablesError(null);
    try {
      const [sucursales, dispositivos] = await Promise.all([
        fetchSucursalSaldos(),
        fetchDispositivoSaldos(),
      ]);
      setSucursalRows(sucursales.map((row) => ({ ...row, __saving: false })));
      setDispositivoRows(dispositivos.map((row) => ({ ...row, __saving: false })));
    } catch (err) {
      console.error('Error cargando saldos:', err);
      setTablesError('No se pudieron cargar los saldos');
      pushToast('No se pudieron cargar los saldos');
    } finally {
      setTablesLoading(false);
    }
  }, [pushToast]);

  const loadCashPolicies = useCallback(async () => {
    try {
      setCashPoliciesLoading(true);
      setCashPoliciesError(null);
      const policies = await fetchCashPolicies();
      setCashPolicies(policies.map((policy) => ({ ...policy, __saving: false, __error: null })));
    } catch (err) {
      console.error('Error cargando políticas de efectivo:', err);
      setCashPoliciesError('No se pudieron cargar las políticas de efectivo');
      pushToast('No se pudieron cargar las políticas de efectivo');
    } finally {
      setCashPoliciesLoading(false);
    }
  }, [pushToast]);

  useEffect(() => {
    void loadSaldos();
  }, [loadSaldos]);

  useEffect(() => {
    void loadCashPolicies();
  }, [loadCashPolicies]);

  const handleSucursalSort = useCallback((column: SucursalColumnKey) => {
    const columnConfig = sucursalColumns.find((col) => col.key === column);
    if (columnConfig?.sortable === false) return;
    setSucursalSort((prev) => ({
      column,
      direction: prev.column === column && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  const handleDispositivoSort = useCallback((column: DispositivoColumnKey) => {
    const columnConfig = dispositivoColumns.find((col) => col.key === column);
    if (columnConfig?.sortable === false) return;
    setDispositivoSort((prev) => ({
      column,
      direction: prev.column === column && prev.direction === 'asc' ? 'desc' : 'asc',
    }));
  }, []);

  const sortedSucursalRows = useMemo(
    () => sortData(sucursalRows, sucursalSort, sucursalColumns),
    [sucursalRows, sucursalSort],
  );

  const sortedDispositivoRows = useMemo(
    () => sortData(dispositivoRows, dispositivoSort, dispositivoColumns),
    [dispositivoRows, dispositivoSort],
  );

  const updateSucursalField = useCallback((rowId: string, field: SucursalColumnKey, rawValue: string) => {
    if (!editableSucursalFields.includes(field)) return;
    setTablesError(null);
    setSucursalRows((prev) =>
      prev.map((row) => {
        if (row.sucursal_id !== rowId) return row;
        let value: unknown = rawValue;
        if (rawValue === '') {
          value = null;
        } else if (field === 'saldo_total_sucursal' || field === 'caja_teorica_sucursal') {
          value = Number.parseFloat(rawValue);
        }
        return { ...row, [field]: value };
      }),
    );
  }, []);

  const updateDispositivoField = useCallback((rowId: number, field: DispositivoColumnKey, rawValue: string) => {
    if (!editableDispositivoFields.includes(field)) return;
    setTablesError(null);
    setDispositivoRows((prev) =>
      prev.map((row) => {
        if (row.id !== rowId) return row;
        let value: unknown = rawValue;
        if (rawValue === '') {
          value = null;
        } else if (field === 'saldo_total' || field === 'caja_teorica') {
          value = Number.parseFloat(rawValue);
        }
        return { ...row, [field]: value };
      }),
    );
  }, []);

  const updateCashPolicyField = useCallback((channel: string, field: keyof CashPolicy, rawValue: string) => {
    if (!editablePolicyFields.includes(field)) return;
    setCashPolicies((prev) =>
      prev.map((policy) => {
        if (policy.channel !== channel) return policy;
        let value: unknown = rawValue;
        if (rawValue === '') {
          value = null;
        } else if (field !== 'notes') {
          const parsed = Number.parseFloat(rawValue);
          value = Number.isFinite(parsed) ? parsed : policy[field];
        }
        return { ...policy, [field]: value, __error: null };
      }),
    );
  }, []);

  const saveCashPolicy = useCallback(async (policy: EditableCashPolicy) => {
    setCashPolicies((prev) =>
      prev.map((item) => (item.channel === policy.channel ? { ...item, __saving: true, __error: null } : item)),
    );
    try {
      const payload: Record<string, unknown> = {};
      editablePolicyFields.forEach((field) => {
        const value = policy[field];
        if (typeof value === 'string') {
          const trimmed = value.trim();
          payload[field] = trimmed === '' ? null : trimmed;
        } else {
          payload[field] = value ?? null;
        }
      });
      const updated = await updateCashPolicy(policy.channel, payload);
      setCashPolicies((prev) =>
        prev.map((item) =>
          item.channel === policy.channel ? { ...updated, __saving: false, __error: null } : item,
        ),
      );
      pushToast('Política de efectivo actualizada');
    } catch (err) {
      console.error('Error guardando política de efectivo:', err);
      const message = err instanceof Error ? err.message : 'Error al guardar la política';
      setCashPolicies((prev) =>
        prev.map((item) =>
          item.channel === policy.channel ? { ...item, __saving: false, __error: message } : item,
        ),
      );
      pushToast('No se pudo guardar la política de efectivo');
    }
  }, [pushToast]);

  const saveSucursalRow = useCallback(async (row: EditableSucursal) => {
    setSucursalRows((prev) => prev.map((item) =>
      item.sucursal_id === row.sucursal_id ? { ...item, __saving: true } : item,
    ));
    try {
      const payload: Partial<SucursalSaldo> = {
        saldo_total_sucursal: row.saldo_total_sucursal,
        caja_teorica_sucursal: row.caja_teorica_sucursal,
      };
      await updateSucursalSaldo(row.sucursal_id, payload);
      pushToast('Sucursal actualizada');
    } catch (err) {
      console.error('Error guardando sucursal:', err);
      pushToast('No se pudo guardar la sucursal');
    } finally {
      setSucursalRows((prev) => prev.map((item) =>
        item.sucursal_id === row.sucursal_id ? { ...item, __saving: false } : item,
      ));
    }
  }, [pushToast]);

  const saveDispositivoRow = useCallback(async (row: EditableDispositivo) => {
    setDispositivoRows((prev) => prev.map((item) =>
      item.id === row.id ? { ...item, __saving: true } : item,
    ));
    try {
      const payload: Partial<DispositivoSaldo> = {
        saldo_total: row.saldo_total,
        caja_teorica: row.caja_teorica,
      };
      await updateDispositivoSaldo(row.id, payload);
      pushToast('Dispositivo actualizado');
    } catch (err) {
      console.error('Error guardando dispositivo:', err);
      pushToast('No se pudo guardar el dispositivo');
    } finally {
      setDispositivoRows((prev) => prev.map((item) =>
        item.id === row.id ? { ...item, __saving: false } : item,
      ));
    }
  }, [pushToast]);

  const removeSucursal = useCallback(async (row: EditableSucursal) => {
    try {
      await deleteSucursalSaldo(row.sucursal_id);
      setSucursalRows((prev) => prev.filter((item) => item.sucursal_id !== row.sucursal_id));
      pushToast('Sucursal eliminada');
    } catch (err) {
      console.error('Error eliminando sucursal:', err);
      pushToast('No se pudo eliminar la sucursal');
    }
  }, [pushToast]);

  const removeDispositivo = useCallback(async (row: EditableDispositivo) => {
    try {
      await deleteDispositivoSaldo(row.id);
      setDispositivoRows((prev) => prev.filter((item) => item.id !== row.id));
      pushToast('Dispositivo eliminado');
    } catch (err) {
      console.error('Error eliminando dispositivo:', err);
      pushToast('No se pudo eliminar el dispositivo');
    }
  }, [pushToast]);

  return (
    <div className={styles.dashboardPage}>
      <div className={styles.toastStack}>
        {toasts.map((toast) => (
          <div key={toast.id} className={`${styles.toast} ${styles.toastError}`}>
            {toast.text}
          </div>
        ))}
      </div>

      <section className={styles.summaryBoard}>
        <article className={styles.summaryTile}>
          <span className={styles.metricLabel}>Efectivo Total</span>
          <span className={styles.metricValue}>
            {data ? dashboardService.formatCurrency(data.metrics.totalCash) : '-'}
          </span>
          <span className={`${styles.metricDelta} ${styles.metricDeltaPositive}`}>
            ▲ 12.5%
          </span>
        </article>
        <article className={styles.summaryTile}>
          <span className={styles.metricLabel}>Flujo Neto</span>
          <span className={styles.metricValue}>
            {data ? dashboardService.formatCurrency(data.metrics.netFlow) : '-'}
          </span>
          <span className={`${styles.metricDelta} ${styles.metricDeltaPositive}`}>
            ▲ 8.2%
          </span>
        </article>
        <article className={styles.summaryTile}>
          <span className={styles.metricLabel}>Sucursales Activas</span>
          <span className={styles.metricValue}>{data?.metrics.activeBranches ?? '-'}</span>
          <span className={styles.metricDelta}>Total operando</span>
        </article>
        <article className={styles.summaryTile}>
          <span className={styles.metricLabel}>Alertas Críticas</span>
          <span className={styles.metricValue}>{data?.metrics.criticalAlerts ?? '-'}</span>
          <span className={styles.metricDelta}>Estado general</span>
        </article>
      </section>

      <section className={styles.panelGrid}>
        <section className={`${styles.graphSection} ${styles.graphSectionWide}`}>
          <header className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Flujo de Caja</h3>
              <p className={styles.sectionSubtitle}>Ingresos vs Egresos (7 días)</p>
            </div>
            <button
              type="button"
              className={styles.primaryButton}
              onClick={() => void loadDashboardData(true)}
              disabled={isLoading}
            >
              {isLoading ? '...' : 'Refrescar'}
            </button>
          </header>
          <div className={styles.sectionSeparator} />
          <div className={styles.sectionContent}>
            {isLoading && !data && <div className={styles.loadingOverlay}>Cargando...</div>}
            <CashFlowChart data={data?.cashFlow || []} isLoading={isLoading} />
          </div>
        </section>

        <section className={`${styles.graphSection} ${styles.graphSectionNarrow}`}>
          <header className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Distribución Denominaciones</h3>
              <p className={styles.sectionSubtitle}>Composición por tipo</p>
            </div>
          </header>
          <div className={styles.sectionSeparator} />
          <div className={styles.sectionContent}>
            {isLoading && !data && <div className={styles.loadingOverlay}>Cargando...</div>}
            <DenominationDistribution data={data?.denominations || []} isLoading={isLoading} />
          </div>
        </section>
      </section>

      <section className={styles.tablesGrid}>
        <section className={`${styles.graphSection} ${styles.tablesLeft}`}>
          <header className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Tablas de saldos</h3>
              <p className={styles.sectionSubtitle}>Saldos por sucursal</p>
            </div>
            <div className={styles.sectionActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => void loadSaldos()}
                disabled={tablesLoading}
              >
                {tablesLoading ? '...' : 'Recargar'}
              </button>
            </div>
          </header>
          <div className={styles.sectionSeparator} />
          <div className={styles.tableWrapper}>
            <div className={styles.tableScroll}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    {sucursalColumns.map((column) => {
                      const isSorted = sucursalSort.column === column.key;
                      const sortable = column.sortable ?? true;
                      const headerClass = column.type === 'number' ? styles.numericCell : undefined;
                      return (
                        <th key={String(column.key)} className={headerClass}>
                          {sortable ? (
                            <button
                              type="button"
                              className={styles.sortableHeaderButton}
                              onClick={() => handleSucursalSort(column.key)}
                            >
                              <span>{column.label}</span>
                              {isSorted && (
                                <span className={styles.sortIcon}>
                                  {sucursalSort.direction === 'asc' ? '▲' : '▼'}
                                </span>
                              )}
                            </button>
                          ) : (
                            <span>{column.label}</span>
                          )}
                        </th>
                      );
                    })}
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedSucursalRows.map((row) => (
                    <tr key={row.sucursal_id}>
                      {sucursalColumns.map((column) => {
                        const rawValue = row[column.key];
                        const isEditable = (column.editable ?? false) && editableSucursalFields.includes(column.key);
                        const cellClass = column.type === 'number' ? styles.numericCell : undefined;
                        return (
                          <td key={`${row.sucursal_id}-${String(column.key)}`} className={cellClass}>
                            {isEditable ? (
                              <input
                                type="number"
                                inputMode="decimal"
                                step={column.step}
                                className={styles.numericInput}
                                value={rawValue ?? ''}
                                onChange={(event) => updateSucursalField(row.sucursal_id, column.key, event.target.value)}
                                disabled={row.__saving}
                              />
                            ) : (
                              <span className={styles.cellText}>{formatCellValue(rawValue, column.type)}</span>
                            )}
                          </td>
                        );
                      })}
                      <td>
                        <div className={styles.tableActionGroup}>
                          <button
                            type="button"
                            className={styles.primaryButton}
                            onClick={() => void saveSucursalRow(row)}
                            disabled={row.__saving}
                          >
                            {row.__saving ? 'Guardando...' : 'Guardar'}
                          </button>
                          <button
                            type="button"
                            className={styles.dangerButton}
                            onClick={() => void removeSucursal(row)}
                            disabled={row.__saving}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!tablesLoading && sortedSucursalRows.length === 0 && (
                    <tr>
                      <td colSpan={sucursalColumns.length + 1}>Sin registros de sucursales</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

        <section className={`${styles.graphSection} ${styles.tablesRight}`}>
          <header className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Saldos de dispositivos</h3>
              <p className={styles.sectionSubtitle}>Últimos registros de ATM/ATS/Tesoro</p>
            </div>
            <div className={styles.sectionActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => void loadSaldos()}
                disabled={tablesLoading}
              >
                {tablesLoading ? '...' : 'Recargar'}
              </button>
            </div>
          </header>
          <div className={styles.sectionSeparator} />
          <div className={styles.tableWrapper}>
            <div className={styles.tableScroll}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    {dispositivoColumns.map((column) => {
                      const isSorted = dispositivoSort.column === column.key;
                      const sortable = column.sortable ?? true;
                      const headerClass = column.type === 'number' ? styles.numericCell : undefined;
                      return (
                        <th key={String(column.key)} className={headerClass}>
                          {sortable ? (
                            <button
                              type="button"
                              className={styles.sortableHeaderButton}
                              onClick={() => handleDispositivoSort(column.key)}
                            >
                              <span>{column.label}</span>
                              {isSorted && (
                                <span className={styles.sortIcon}>
                                  {dispositivoSort.direction === 'asc' ? '▲' : '▼'}
                                </span>
                              )}
                            </button>
                          ) : (
                            <span>{column.label}</span>
                          )}
                        </th>
                      );
                    })}
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {sortedDispositivoRows.map((row) => (
                    <tr key={row.id}>
                      {dispositivoColumns.map((column) => {
                        const rawValue = row[column.key];
                        const isEditable = (column.editable ?? false) && editableDispositivoFields.includes(column.key);
                        const cellClass = column.type === 'number' ? styles.numericCell : undefined;
                        return (
                          <td key={`${row.id}-${String(column.key)}`} className={cellClass}>
                            {isEditable ? (
                              <input
                                type="number"
                                inputMode="decimal"
                                step={column.step}
                                className={styles.numericInput}
                                value={rawValue ?? ''}
                                onChange={(event) => updateDispositivoField(row.id, column.key, event.target.value)}
                                disabled={row.__saving}
                              />
                            ) : (
                              <span className={styles.cellText}>{formatCellValue(rawValue, column.type)}</span>
                            )}
                          </td>
                        );
                      })}
                      <td>
                        <div className={styles.tableActionGroup}>
                          <button
                            type="button"
                            className={styles.primaryButton}
                            onClick={() => void saveDispositivoRow(row)}
                            disabled={row.__saving}
                          >
                            {row.__saving ? 'Guardando...' : 'Guardar'}
                          </button>
                          <button
                            type="button"
                            className={styles.dangerButton}
                            onClick={() => void removeDispositivo(row)}
                            disabled={row.__saving}
                          >
                            Eliminar
                          </button>
                        </div>
                      </td>
                    </tr>
                  ))}
                  {!tablesLoading && sortedDispositivoRows.length === 0 && (
                    <tr>
                      <td colSpan={dispositivoColumns.length + 1}>Sin registros de dispositivos</td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>
      </section>

        <section className={styles.graphSection} style={{ gridColumn: 'span 12' }}>
          <header className={styles.sectionHeader}>
            <div>
              <h3 className={styles.sectionTitle}>Políticas de efectivo</h3>
              <p className={styles.sectionSubtitle}>Límites y costos para movimientos de caja</p>
            </div>
            <div className={styles.sectionActions}>
              <button
                type="button"
                className={styles.secondaryButton}
                onClick={() => void loadCashPolicies()}
                disabled={cashPoliciesLoading}
              >
                {cashPoliciesLoading ? '...' : 'Recargar'}
              </button>
            </div>
          </header>
          <div className={styles.sectionSeparator} />
          {cashPoliciesError && <div className={styles.tablesError}>{cashPoliciesError}</div>}
          <div className={styles.tableWrapper}>
            <div className={styles.tableScroll}>
              <table className={styles.dataTable}>
                <thead>
                  <tr>
                    <th>Canal</th>
                    {policyColumns.map((column) => (
                      <th key={String(column.key)}>{column.label}</th>
                    ))}
                    <th>Acciones</th>
                  </tr>
                </thead>
                <tbody>
                  {cashPoliciesLoading ? (
                    <tr>
                      <td colSpan={policyColumns.length + 2}>Cargando políticas...</td>
                    </tr>
                  ) : cashPolicies.length === 0 ? (
                    <tr>
                      <td colSpan={policyColumns.length + 2}>Sin políticas configuradas</td>
                    </tr>
                  ) : (
                    cashPolicies.map((policy) => (
                      <tr key={policy.channel}>
                        <td>{policy.channel}</td>
                        {policyColumns.map((column) => {
                          const rawValue = policy[column.key] as number | string | null | undefined;
                          const inputKey = `${policy.channel}-${String(column.key)}`;
                          const isDisabled = policy.__saving || cashPoliciesLoading;
                          if (column.type === 'text') {
                            return (
                              <td key={inputKey}>
                                <input
                                  type="text"
                                  className={styles.tableInput}
                                  value={(rawValue as string | null | undefined) ?? ''}
                                  onChange={(event) =>
                                    updateCashPolicyField(policy.channel, column.key, event.target.value)
                                  }
                                  disabled={isDisabled}
                                />
                              </td>
                            );
                          }
                          return (
                            <td key={inputKey} className={styles.numericCell}>
                              <input
                                type="number"
                                inputMode="decimal"
                                step={column.step}
                                className={styles.numericInput}
                                value={rawValue ?? ''}
                                onChange={(event) =>
                                  updateCashPolicyField(policy.channel, column.key, event.target.value)
                                }
                                disabled={isDisabled}
                              />
                            </td>
                          );
                        })}
                        <td>
                          <div className={styles.tableActionGroup}>
                            <button
                              type="button"
                              className={styles.primaryButton}
                              onClick={() => void saveCashPolicy(policy)}
                              disabled={policy.__saving || cashPoliciesLoading}
                              title={policy.__error ?? undefined}
                            >
                              {policy.__saving ? 'Guardando...' : 'Guardar'}
                            </button>
                          </div>
                          {policy.updated_at && (
                            <p className={styles.sectionSubtitle}>Actualizado: {formatDateTimeDisplay(policy.updated_at)}</p>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </section>

      <footer className={styles.footer}>
        <div className={styles.footerBox}>
          <span className={styles.footerLabel}>Sistema</span>
          <span className={styles.statusBadge}>Operativo</span>
        </div>
        <div className={styles.footerBox}>
          <span className={styles.footerLabel}>Última actualización</span>
          <span className={styles.footerValue} suppressHydrationWarning>
            {lastUpdated ? format(lastUpdated, 'HH:mm:ss', { locale: es }) : '-'}
          </span>
        </div>
        <div className={styles.footerBox}>
          <span className={styles.footerLabel}>Manual</span>
          <span className={styles.footerValue}>Auto 5m</span>
        </div>
        <div className={styles.footerBox}>
          <span className={styles.footerLabel}>Acción</span>
          <button
            type="button"
            className={styles.primaryButton}
            onClick={() => void loadDashboardData(true)}
            disabled={isLoading}
          >
            {isLoading ? '...' : 'Actualizar'}
          </button>
        </div>
      </footer>
    </div>
  );
};

export default ExecutiveDashboard;
