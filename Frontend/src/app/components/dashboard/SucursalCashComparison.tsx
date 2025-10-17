'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  ResponsiveContainer,
  BarChart,
  CartesianGrid,
  XAxis,
  YAxis,
  Tooltip,
  Legend,
  Bar,
} from 'recharts';
import type { TooltipProps } from 'recharts';

export interface CashComparisonRow {
  id: string;
  name: string;
  saldoTotal: number;
  cajaTeorica: number;
}

export type ComparisonView = 'compare' | 'radar';

interface SucursalCashComparisonProps {
  data: CashComparisonRow[];
  isLoading?: boolean;
  view?: ComparisonView;
}

const numberFormatter = new Intl.NumberFormat('es-AR', {
  style: 'currency',
  currency: 'ARS',
  maximumFractionDigits: 0,
});

const LoadingState: React.FC = () => (
  <div className="grid gap-6 animate-pulse">
    <div className="h-8 rounded-lg bg-slate-800/80" />
    <div className="h-64 rounded-3xl bg-slate-800/80" />
    <div className="h-48 rounded-3xl bg-slate-800/80" />
  </div>
);

const EmptyState: React.FC = () => (
  <div className="flex flex-col items-center justify-center gap-3 rounded-3xl border-2 border-dashed border-cyan-400/30 bg-slate-900/60 py-12 text-center text-cyan-100/80 backdrop-blur">
    <span className="text-sm font-medium">No se encontraron saldos para mostrar.</span>
    <span className="text-xs text-cyan-100/60">
      Verifica la sincronización con el backend o ajusta los filtros de tus consultas.
    </span>
  </div>
);

const tooltipFormatter: TooltipProps<number, string>['formatter'] = (value) => {
  const parsedValue = Array.isArray(value) ? Number(value[0] ?? 0) : Number(value ?? 0);
  const safeValue = Number.isFinite(parsedValue) ? parsedValue : 0;
  return numberFormatter.format(safeValue);
};

export const SucursalCashComparison: React.FC<SucursalCashComparisonProps> = ({
  data,
  isLoading = false,
  view = 'compare',
}) => {
  const [primaryId, setPrimaryId] = useState<string>('');
  const [secondaryId, setSecondaryId] = useState<string>('');

  const preparedRows = useMemo(
    () =>
      data
        .map((row) => ({
          ...row,
          saldoTotal: Number.isFinite(row.saldoTotal) ? row.saldoTotal : 0,
          cajaTeorica: Number.isFinite(row.cajaTeorica) ? row.cajaTeorica : 0,
        }))
        .map((row) => ({
          ...row,
          difference: row.saldoTotal - row.cajaTeorica,
        })),
    [data],
  );

  const orderedOptions = useMemo(
    () =>
      preparedRows
        .slice()
        .sort((a, b) => a.name.localeCompare(b.name, 'es'))
        .map((row) => ({ id: row.id, name: row.name })),
    [preparedRows],
  );

  useEffect(() => {
    if (!orderedOptions.length) {
      setPrimaryId('');
      return;
    }

    setPrimaryId((prev) => {
      if (prev && orderedOptions.some((option) => option.id === prev)) {
        return prev;
      }
      return orderedOptions[0].id;
    });
  }, [orderedOptions]);

  useEffect(() => {
    if (!orderedOptions.length) {
      setSecondaryId('');
      return;
    }

    setSecondaryId((prev) => {
      if (prev && prev !== primaryId && orderedOptions.some((option) => option.id === prev)) {
        return prev;
      }
      const fallback = orderedOptions.find((option) => option.id !== primaryId);
      return fallback ? fallback.id : '';
    });
  }, [orderedOptions, primaryId]);

  const selection = useMemo(() => {
    const ids: string[] = [];
    if (primaryId) ids.push(primaryId);
    if (secondaryId && secondaryId !== primaryId) ids.push(secondaryId);

    if (!ids.length && orderedOptions.length) {
      ids.push(orderedOptions[0].id);
      const second = orderedOptions.find((option) => option.id !== orderedOptions[0].id);
      if (second) ids.push(second.id);
    } else if (ids.length === 1) {
      const fallback = orderedOptions.find((option) => option.id !== ids[0]);
      if (fallback) ids.push(fallback.id);
    }

    return {
      ids,
      signature: ids.slice().sort().join('|'),
    };
  }, [orderedOptions, primaryId, secondaryId]);

  const selectedRows = useMemo(() => {
    if (!selection.ids.length) {
      return [];
    }

    const idsSet = new Set(selection.ids);
    const rows = preparedRows.filter((row) => idsSet.has(row.id));
    if (rows.length) {
      return rows;
    }

    return preparedRows.slice(0, Math.min(2, preparedRows.length));
  }, [preparedRows, selection.signature]);

  const chartData = useMemo(
    () =>
      selectedRows.map((row) => ({
        name: row.name,
        saldoTotal: row.saldoTotal,
        cajaTeorica: row.cajaTeorica,
        difference: row.difference,
      })),
    [selectedRows],
  );

  const totals = useMemo(
    () =>
      selectedRows.reduce(
        (acc, row) => {
          acc.saldoTotal += row.saldoTotal;
          acc.cajaTeorica += row.cajaTeorica;
          acc.difference += row.difference;
          return acc;
        },
        { saldoTotal: 0, cajaTeorica: 0, difference: 0 },
      ),
    [selectedRows],
  );

  const secondaryOptions = useMemo(
    () => orderedOptions.filter((option) => option.id !== primaryId),
    [orderedOptions, primaryId],
  );

  const secondaryValue = secondaryOptions.some((option) => option.id === secondaryId)
    ? secondaryId
    : secondaryOptions[0]?.id ?? '';

  const deepestDeficitRows = useMemo(() => {
    return preparedRows
      .filter((row) => row.difference < 0)
      .sort((a, b) => a.difference - b.difference)
      .slice(0, 5);
  }, [preparedRows]);

  const highestSaldoRows = useMemo(() => {
    return preparedRows
      .slice()
      .sort((a, b) => b.saldoTotal - a.saldoTotal)
      .slice(0, 5);
  }, [preparedRows]);

  if (isLoading) {
    return <LoadingState />;
  }

  if (!preparedRows.length) {
    return <EmptyState />;
  }

  if (view === 'radar') {
    return (
      <div className="grid gap-8 text-cyan-100">
        <section className="rounded-3xl border border-cyan-500/20 bg-slate-950/70 p-6 shadow-[0_24px_60px_rgba(5,18,36,0.55)] backdrop-blur">
          <header className="mb-5 flex flex-col gap-1 header-radar">
            <h2 className="text-lg font-semibold text-cyan-100">Radar de sucursales</h2>
            <p className="text-xs text-cyan-100/70">
              Si detectás una brecha considerable frente a la caja teórica, podés derivar al equipo de tesorería para
              tomar acciones inmediatas.
            </p>
          </header>
          <div className="grid gap-6 lg:grid-cols-2">
            <div className="rounded-2xl border border-rose-400/30 bg-rose-950/20 p-4 shadow-[0_18px_42px_rgba(67,20,33,0.45)]">
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-rose-200/80">
                Debajo de la caja teórica
              </h3>
              <p className="mt-1 text-xs text-rose-100/70">Mayores déficits respecto a la caja estimada.</p>
              {deepestDeficitRows.length ? (
                <div className="mt-4 space-y-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart
                      data={deepestDeficitRows.map((row) => ({
                        name: row.name,
                        saldo: row.saldoTotal,
                        caja: row.cajaTeorica,
                        deficit: Math.abs(row.difference),
                      }))}
                      margin={{ top: 12, right: 16, left: 0, bottom: 32 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#3f1f2b" />
                      <XAxis
                        dataKey="name"
                        angle={-25}
                        textAnchor="end"
                        height={70}
                        tick={{ fill: 'rgba(255,228,230,0.7)', fontSize: 11 }}
                      />
                      <YAxis tick={{ fill: 'rgba(254,202,202,0.8)', fontSize: 11 }} />
                      <Tooltip
                        formatter={tooltipFormatter}
                        cursor={{ fill: 'rgba(244,63,94,0.1)' }}
                        contentStyle={{
                          background: '#2b0f17',
                          borderRadius: 16,
                          border: '1px solid rgba(248,113,113,0.4)',
                          color: '#ffe4e6',
                        }}
                      />
                      <Legend
                        iconType="circle"
                        wrapperStyle={{ fontSize: 11, color: 'rgba(255,228,230,0.75)' }}
                      />
                      <Bar
                        dataKey="caja"
                        name="Caja teórica"
                        fill="rgba(248, 113, 113, 0.35)"
                        stroke="rgba(248, 113, 113, 0.6)"
                        strokeWidth={1.2}
                        radius={[6, 6, 0, 0]}
                        maxBarSize={42}
                      />
                      <Bar
                        dataKey="saldo"
                        name="Saldo actual"
                        fill="#fda4af"
                        stroke="#fb7185"
                        strokeWidth={1.2}
                        radius={[6, 6, 0, 0]}
                        maxBarSize={36}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                  <ul className="space-y-3">
                    {deepestDeficitRows.map((row, index) => (
                      <li
                        key={row.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-rose-400/25 bg-rose-900/20 px-4 py-3 text-sm text-rose-100"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs uppercase tracking-[0.16em] text-rose-200/70">#{index + 1}</span>
                          <span className="font-semibold text-rose-50">{row.name}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs uppercase tracking-[0.14em] text-rose-200/70">Diferencia</span>
                          <p className="text-sm font-semibold text-rose-100">
                            {numberFormatter.format(Math.abs(row.difference))}
                          </p>
                          <span className="text-[11px] uppercase tracking-[0.12em] text-rose-200/60">
                            Caja teórica: {numberFormatter.format(row.cajaTeorica)}
                          </span>
                          <span className="text-[11px] uppercase tracking-[0.12em] text-rose-200/60">
                            Saldo actual: {numberFormatter.format(row.saldoTotal)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-4 rounded-xl border border-dashed border-rose-400/30 bg-rose-900/10 px-4 py-6 text-center text-sm text-rose-100/70">
                  No hay sucursales por debajo de la caja teórica.
                </p>
              )}
            </div>

            <div className="rounded-2xl border border-emerald-400/30 bg-emerald-950/20 p-4 shadow-[0_18px_42px_rgba(4,38,27,0.45)]">
              <h3 className="text-sm font-semibold uppercase tracking-[0.14em] text-emerald-200/80">
                Con mayor saldo disponible
              </h3>
              <p className="mt-1 text-xs text-emerald-100/70">Top de sucursales por saldo total acumulado.</p>
              {highestSaldoRows.length ? (
                <div className="mt-4 space-y-4">
                  <ResponsiveContainer width="100%" height={220}>
                    <BarChart
                      data={highestSaldoRows.map((row) => ({
                        name: row.name,
                        saldo: row.saldoTotal,
                        caja: row.cajaTeorica,
                      }))}
                      margin={{ top: 12, right: 16, left: 0, bottom: 32 }}
                    >
                      <CartesianGrid strokeDasharray="3 3" stroke="#123d2c" />
                      <XAxis
                        dataKey="name"
                        angle={-25}
                        textAnchor="end"
                        height={70}
                        tick={{ fill: 'rgba(209,250,229,0.75)', fontSize: 11 }}
                      />
                      <YAxis tick={{ fill: 'rgba(167,243,208,0.85)', fontSize: 11 }} />
                      <Tooltip
                        formatter={tooltipFormatter}
                        cursor={{ fill: 'rgba(16,185,129,0.12)' }}
                        contentStyle={{
                          background: '#062417',
                          borderRadius: 16,
                          border: '1px solid rgba(52,211,153,0.4)',
                          color: '#d1fae5',
                        }}
                      />
                      <Legend
                        iconType="circle"
                        wrapperStyle={{ fontSize: 11, color: 'rgba(209,250,229,0.75)' }}
                      />
                      <Bar
                        dataKey="caja"
                        name="Caja teórica"
                        fill="rgba(110, 231, 183, 0.35)"
                        stroke="rgba(16, 185, 129, 0.6)"
                        strokeWidth={1.2}
                        radius={[6, 6, 0, 0]}
                        maxBarSize={42}
                      />
                      <Bar
                        dataKey="saldo"
                        name="Saldo actual"
                        fill="#34d399"
                        stroke="#10b981"
                        strokeWidth={1.2}
                        radius={[6, 6, 0, 0]}
                        maxBarSize={36}
                      />
                    </BarChart>
                  </ResponsiveContainer>
                  <ul className="space-y-3">
                    {highestSaldoRows.map((row, index) => (
                      <li
                        key={row.id}
                        className="flex items-center justify-between gap-3 rounded-xl border border-emerald-400/25 bg-emerald-900/20 px-4 py-3 text-sm text-emerald-100"
                      >
                        <div className="flex flex-col">
                          <span className="text-xs uppercase tracking-[0.16em] text-emerald-200/70">#{index + 1}</span>
                          <span className="font-semibold text-emerald-50">{row.name}</span>
                        </div>
                        <div className="text-right">
                          <span className="text-xs uppercase tracking-[0.14em] text-emerald-200/70">Saldo total</span>
                          <p className="text-sm font-semibold text-emerald-100">
                            {numberFormatter.format(row.saldoTotal)}
                          </p>
                          <span className="text-[11px] uppercase tracking-[0.12em] text-emerald-200/60">
                            Caja teórica: {numberFormatter.format(row.cajaTeorica)}
                          </span>
                        </div>
                      </li>
                    ))}
                  </ul>
                </div>
              ) : (
                <p className="mt-4 rounded-xl border border-dashed border-emerald-400/30 bg-emerald-900/10 px-4 py-6 text-center text-sm text-emerald-100/70">
                  No hay sucursales con saldo suficiente para mostrar.
                </p>
              )}
            </div>
          </div>
        </section>
      </div>
    );
  }

  return (
    <div className="grid gap-8 text-cyan-100">
      <section className="rounded-3xl border border-cyan-500/20 bg-slate-950/70 p-6 shadow-[0_24px_60px_rgba(5,18,36,0.55)] backdrop-blur">
        <header className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <dl className="grid w-full gap-4 rounded-2xl border border-cyan-400/20 bg-slate-900/50 p-4 text-xs uppercase tracking-[0.08em] text-cyan-200/70 sm:grid-cols-3 sm:text-right">
            <div className="flex flex-col gap-1">
              <dt>Saldo total agregado</dt>
              <dd className="text-base font-semibold text-emerald-300">
                {numberFormatter.format(totals.saldoTotal)}
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt>Caja teórica agregada</dt>
              <dd className="text-base font-semibold text-sky-300">
                {numberFormatter.format(totals.cajaTeorica)}
              </dd>
            </div>
            <div className="flex flex-col gap-1">
              <dt>Diferencia neta</dt>
              <dd className={`text-base font-semibold ${totals.difference >= 0 ? 'text-emerald-300' : 'text-rose-300'}`}>
                {numberFormatter.format(totals.difference)}
              </dd>
            </div>
          </dl>
        </header>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200/70">
            Sucursal A
            <select
              value={primaryId}
              onChange={(event) => setPrimaryId(event.target.value)}
              className="w-full rounded-full border border-cyan-400/40 bg-slate-900/80 px-4 py-2 text-sm font-medium text-cyan-100 shadow-[0_12px_35px_rgba(12,40,67,0.35)] outline-none transition focus:border-cyan-200 focus:ring-2 focus:ring-cyan-300/40"
            >
              {orderedOptions.map((option) => (
                <option key={option.id} value={option.id} className="bg-slate-900 text-cyan-100">
                  {option.name}
                </option>
              ))}
            </select>
          </label>

          <label className="flex flex-col gap-2 text-xs font-semibold uppercase tracking-[0.12em] text-cyan-200/70">
            Sucursal B
            <select
              value={secondaryValue}
              onChange={(event) => setSecondaryId(event.target.value)}
              disabled={secondaryOptions.length === 0}
              className="w-full rounded-full border border-cyan-400/40 bg-slate-900/80 px-4 py-2 text-sm font-medium text-cyan-100 shadow-[0_12px_35px_rgba(12,40,67,0.35)] outline-none transition focus:border-cyan-200 focus:ring-2 focus:ring-cyan-300/40 disabled:cursor-not-allowed disabled:border-cyan-400/20 disabled:text-cyan-300/40"
            >
              {secondaryOptions.length === 0 ? (
                <option value="" className="bg-slate-900 text-cyan-100">
                  Sin alternativas disponibles
                </option>
              ) : (
                secondaryOptions.map((option) => (
                  <option key={option.id} value={option.id} className="bg-slate-900 text-cyan-100">
                    {option.name}
                  </option>
                ))
              )}
            </select>
          </label>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {selectedRows.map((row, index) => {
            const label = index === 0 ? 'Sucursal A' : index === 1 ? 'Sucursal B' : `Sucursal ${index + 1}`;
            const differenceText = row.difference >= 0 ? 'superior a' : 'inferior a';
            return (
              <article
                key={row.id}
                className="rounded-2xl border border-cyan-400/25 bg-slate-900/60 p-4 text-sm backdrop-blur-sm shadow-[0_18px_40px_rgba(7,25,42,0.45)]"
              >
                <header className="mb-2 flex flex-wrap items-baseline gap-x-3 gap-y-1 header-height">
                  <span className="rounded-full bg-cyan-500/15 px-3 text-[11px] font-semibold uppercase tracking-[0.18em] text-cyan-200/80">
                    {label}
                  </span>
                  <h4 className="text-base font-semibold text-cyan-50">{row.name}</h4>
                </header>
                <dl className="space-y-1 text-cyan-100/80">
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <dt className="text-xs uppercase tracking-[0.16em] text-cyan-200/60">Saldo total</dt>
                    <dd className="text-sm font-semibold text-emerald-300">
                      {numberFormatter.format(row.saldoTotal)}
                    </dd>
                  </div>
                  <div className="flex flex-wrap items-center justify-between gap-2">
                    <dt className="text-xs uppercase tracking-[0.16em] text-cyan-200/60">Caja teórica</dt>
                    <dd className="text-sm font-semibold text-sky-300">
                      {numberFormatter.format(row.cajaTeorica)}
                    </dd>
                  </div>
                </dl>
                <p
                  className={`mt-3 text-xs leading-relaxed text-cyan-100/80 md:text-sm ${
                    row.difference >= 0 ? 'text-emerald-200' : 'text-rose-200'
                  }`}
                >
                  El saldo actual es {differenceText} la caja teórica por
                  <strong className="ml-1">{numberFormatter.format(Math.abs(row.difference))}</strong>.
                </p>
              </article>
            );
          })}
          {selectedRows.length === 1 ? (
            <article className="rounded-2xl border border-dashed border-cyan-400/20 bg-slate-900/40 p-4 text-sm text-cyan-200/60">
              Agrega una segunda sucursal para comparar diferencias.
            </article>
          ) : null}
        </div>
      </section>

      <section className="rounded-3xl border border-cyan-500/20 bg-slate-950/70 p-6 shadow-[0_24px_60px_rgba(5,18,36,0.55)] backdrop-blur">
        <header className="mb-6 rounded-2xl border border-cyan-400/25 bg-slate-900/45 px-5 py-4 shadow-[0_18px_42px_rgba(7,25,42,0.4)] backdrop-blur-sm">
          <div className="flex flex-col gap-1">
            <h3 className="text-base font-semibold text-cyan-100">Comparativo visual</h3>
            <p className="text-xs text-cyan-100/70">Barras enfrentadas para las sucursales seleccionadas.</p>
          </div>
        </header>
        {chartData.length === 0 ? (
          <div className="flex h-72 items-center justify-center rounded-3xl border border-dashed border-cyan-500/20 bg-slate-900/60 text-sm text-cyan-100/70">
            Selecciona al menos una sucursal para visualizar el gráfico.
          </div>
        ) : (
          <div className="h-80 rounded-3xl border border-cyan-400/15 bg-slate-900/40 p-4">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={chartData} margin={{ top: 8, right: 24, left: 0, bottom: 32 }}>
                <CartesianGrid strokeDasharray="3 3" stroke="#1f2a3d" />
                <XAxis
                  dataKey="name"
                  angle={-30}
                  textAnchor="end"
                  height={80}
                  tick={{ fontSize: 12, fill: '#a9d5ff' }}
                />
                <YAxis tickFormatter={(value) => `${(value / 1_000_000).toFixed(1)}M`} tick={{ fill: '#a9d5ff' }} />
                <Tooltip
                  formatter={tooltipFormatter}
                  cursor={{ fill: 'rgba(14,165,233,0.08)' }}
                  contentStyle={{
                    background: '#051224',
                    borderRadius: 16,
                    border: '1px solid rgba(45,212,191,0.4)',
                    color: '#e6f1ff',
                  }}
                />
                <Legend wrapperStyle={{ color: '#e6f1ff' }} />
                <Bar dataKey="saldoTotal" name="Saldo total" fill="#34d399" radius={[8, 8, 0, 0]} />
                <Bar dataKey="cajaTeorica" name="Caja teórica" fill="#60a5fa" radius={[8, 8, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}
      </section>

    </div>
  );
};

export default SucursalCashComparison;
