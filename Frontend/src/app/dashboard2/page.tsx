'use client';

import React, { Suspense, useEffect, useMemo, useState } from 'react';
import type { FeatureCollection, MultiPolygon, Polygon } from 'geojson';
import { argentinaProvincesSimple } from '@/app/data/argentinaProvincesSimple';
const ArgentinaProvincesMap = React.lazy(() => import('@/app/components/dashboard/ArgentinaProvincesMap'));

type ProvinceGeometry = Polygon | MultiPolygon;

const PROVINCE_GEOJSON_SOURCES: readonly string[] = [
  'https://raw.githubusercontent.com/codeforamerica/click_that_hood/main/public/data/argentina-provinces.geojson',
  'https://raw.githubusercontent.com/codeforamerica/click_that_hood/master/public/data/argentina-provinces.geojson',
];

const DEFAULT_REGIONAL_DATA = [
  { provincia: 'Buenos Aires', value: 1880000 },
  { provincia: 'Ciudad Autónoma de Buenos Aires', value: 720000 },
  { provincia: 'Córdoba', value: 610000 },
  { provincia: 'Santa Fe', value: 540000 },
  { provincia: 'Mendoza', value: 320000 },
  { provincia: 'Tucumán', value: 180000 },
  { provincia: 'Salta', value: 160000 },
  { provincia: 'Neuquén', value: 120000 },
  { provincia: 'Chubut', value: 110000 },
  { provincia: 'Misiones', value: 150000 },
];

const REGIONAL_PALETTE = ['#0f172a', '#0b5ed7', '#2563eb', '#38bdf8', '#60efff', '#c4f1ff'];

const REGIONAL_NUMBER_FORMAT = new Intl.NumberFormat('es-AR', {
  maximumFractionDigits: 0,
});
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
  const [activeAction, setActiveAction] = useState<string>('compare');
  const [geoJson, setGeoJson] = useState<FeatureCollection<ProvinceGeometry>>(argentinaProvincesSimple as FeatureCollection<ProvinceGeometry>);
  const [geoLoading, setGeoLoading] = useState(false);
  const [geoError, setGeoError] = useState<string | null>(null);
  const [hasLoadedRemoteGeoJson, setHasLoadedRemoteGeoJson] = useState(false);
  const [selectedProvince, setSelectedProvince] = useState<string | null>(null);

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

  useEffect(() => {
    if (activeAction !== 'map-regional') return;
    if (hasLoadedRemoteGeoJson || geoLoading) return;

    let cancelled = false;
    const fetchProvinceGeoJson = async () => {
      let lastError: unknown = null;

      for (const source of PROVINCE_GEOJSON_SOURCES) {
        try {
          const response = await fetch(source, { cache: 'force-cache' });
          if (!response.ok) {
            lastError = new Error(`GeoJSON status ${response.status} (${source})`);
            continue;
          }

          const payload = (await response.json()) as FeatureCollection<ProvinceGeometry>;
          console.info('[Frontend] [map-regional] GeoJSON cargado desde', source);
          return payload;
        } catch (error) {
          lastError = error;
        }
      }

      throw lastError ?? new Error('No se pudo obtener el GeoJSON de provincias.');
    };

    const loadGeoJson = async () => {
      try {
        setGeoLoading(true);
        setGeoError(null);
        const payload = await fetchProvinceGeoJson();
        if (!cancelled) {
          setGeoJson(payload);
          setHasLoadedRemoteGeoJson(true);
        }
      } catch (err) {
        console.error('No se pudo obtener el GeoJSON de provincias:', err);
        if (!cancelled) {
          setGeoError('No se pudo cargar el mapa regional. Intentá nuevamente más tarde.');
        }
      } finally {
        if (!cancelled) {
          setGeoLoading(false);
        }
      }
    };

    void loadGeoJson();

    return () => {
      cancelled = true;
    };
  }, [activeAction, geoLoading, hasLoadedRemoteGeoJson]);

  useEffect(() => {
    if (activeAction !== 'map-regional') {
      setSelectedProvince(null);
    }
  }, [activeAction]);

  const comparisonRows = useMemo<CashComparisonRow[]>(() => {
    return sucursales.map((item) => ({
      id: item.sucursal_id,
      name: item.sucursal_nombre || `Sucursal ${item.sucursal_numero}`,
      saldoTotal: item.saldo_total_sucursal ?? 0,
      cajaTeorica: item.caja_teorica_sucursal ?? 0,
    }));
  }, [sucursales]);

  const regionalData = useMemo(() => {
    if (sucursales.length === 0) {
      return DEFAULT_REGIONAL_DATA;
    }

    const actualTotal = sucursales.reduce((acc, item) => acc + (item.saldo_total_sucursal ?? 0), 0);
    const fallbackTotal = DEFAULT_REGIONAL_DATA.reduce((acc, item) => acc + item.value, 0);

    if (!Number.isFinite(actualTotal) || actualTotal <= 0 || fallbackTotal <= 0) {
      return DEFAULT_REGIONAL_DATA;
    }

    const scale = actualTotal / fallbackTotal;
    return DEFAULT_REGIONAL_DATA.map((item) => ({
      provincia: item.provincia,
      value: Math.round(item.value * scale),
    }));
  }, [sucursales]);

  const topProvinces = useMemo(() => {
    return [...regionalData].sort((a, b) => b.value - a.value).slice(0, 5);
  }, [regionalData]);

  const selectedProvinceMetric = useMemo(() => {
    if (!selectedProvince) return null;
    return regionalData.find((item) => item.provincia === selectedProvince) ?? null;
  }, [regionalData, selectedProvince]);

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
      { value: 'map-regional', label: 'Mapa Regional' },
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
                  onChange={(event) => setActiveAction(event.target.value)}
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
            <SucursalCashComparison
              data={comparisonRows}
              isLoading={isLoading}
              view={activeAction as ComparisonView}
            />
          ) : activeAction === 'map-regional' ? (
            <Suspense
              fallback={
                <div className={styles.placeholderCard}>
                  <strong>Cargando mapa regional</strong>
                  Los límites provinciales se están sincronizando con el tablero.
                </div>
              }
            >
              <div className={styles.mapRegionLayout}>
                {geoError ? (
                  <div className={styles.errorCard}>
                    <span className={styles.errorAccent} aria-hidden="true" />
                    <div>
                      <strong>Mapa base alternativo</strong>
                      <p>
                        {geoError} Usando geometría simplificada para continuar trabajando sin interrupciones.
                      </p>
                    </div>
                  </div>
                ) : null}

                <ArgentinaProvincesMap
                  geojson={geoJson}
                  data={regionalData}
                  palette={REGIONAL_PALETTE}
                  onSelect={(province) => setSelectedProvince(province)}
                />
                <div className={styles.mapSummaryCard}>
                  <div className={styles.mapSummaryHeader}>
                    <span className={styles.mapSummaryEyebrow}>Insights rápidos</span>
                    <strong>
                      {selectedProvince
                        ? `Foco en ${selectedProvince}`
                        : 'Seleccioná una provincia para profundizar'}
                    </strong>
                    {selectedProvinceMetric ? (
                      <p>
                        Saldo observado{' '}
                        <span className={styles.mapSummaryValue}>
                          {REGIONAL_NUMBER_FORMAT.format(selectedProvinceMetric.value)}
                        </span>
                      </p>
                    ) : (
                      <p>
                        El ranking refleja la distribución estimada de saldos operativos a nivel país.
                      </p>
                    )}
                  </div>
                  <ol className={styles.mapRankingList}>
                    {topProvinces.map((item, index) => (
                      <li key={item.provincia} className={styles.mapRankingItem}>
                        <span className={styles.mapRankingIndex}>{index + 1}</span>
                        <span className={styles.mapRankingName}>{item.provincia}</span>
                        <span className={styles.mapRankingValue}>
                          {REGIONAL_NUMBER_FORMAT.format(item.value)}
                        </span>
                      </li>
                    ))}
                  </ol>
                </div>
              </div>
            </Suspense>
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
