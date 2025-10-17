"use client";

import { useEffect, useMemo, useState } from 'react';
import styles from './styles.module.css';

export default function Home2Page() {
  type SucursalRecord = {
    saldo_total_sucursal: number;
    caja_teorica_sucursal?: number | null;
  };

  type WeatherInfo = {
    location: string;
    temperatureFormatted: string;
    condition: string;
    observedAt?: string | null;
  };

  const [weatherInfo, setWeatherInfo] = useState<WeatherInfo>({
    location: 'CABA · Microcentro',
    temperatureFormatted: '---',
    condition: 'Actualizando...',
    observedAt: null,
  });
  const [weatherLoading, setWeatherLoading] = useState(true);

  const NEWS_ITEMS = useMemo(
    () => [
      '🚨 Radar IA: monitoreo contínuo de saldos críticos en toda la red.',
      '🤖 Agente CAPI sugiere redistribución preventiva para Zona Norte.',
      '📊 Se actualiza el tablero de comparativas cada 15 minutos.',
      '🔐 Auditoría en curso: refuerzo de protocolos de tesorería.',
      '⚡ Flujo LangGraph optimizado: alertas anticipadas en menos de 5 minutos.',
    ],
    []
  );

  const [branchStats, setBranchStats] = useState({
    above: 0,
    below: 0,
    loading: true,
  });
  const [tickerItems, setTickerItems] = useState<string[]>([]);

  useEffect(() => {
    let cancelled = false;

    async function fetchBranchStats() {
      try {
        const response = await fetch('/api/maps/sucursales', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }
        const payload: SucursalRecord[] = await response.json();
        if (cancelled) {
          return;
        }

        const totals = payload.reduce(
          (acc, record) => {
            const caja = record.caja_teorica_sucursal;
            if (!Number.isFinite(caja) || !caja) {
              return acc;
            }

            const upperThreshold = caja * 1.40;
            const lowerThreshold = caja * 0.60;

            if (record.saldo_total_sucursal >= upperThreshold) {
              acc.above += 1;
            } else if (record.saldo_total_sucursal <= lowerThreshold) {
              acc.below += 1;
            }

            return acc;
          },
          { above: 0, below: 0 }
        );

        setBranchStats({
          above: totals.above,
          below: totals.below,
          loading: false,
        });
      } catch (error) {
        if (!cancelled) {
          setBranchStats((prev) => ({ ...prev, loading: false }));
        }
      }
    }

    fetchBranchStats();
    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    let cancelled = false;

    async function fetchWeather() {
      try {
        const response = await fetch('/api/weather', { cache: 'no-store' });
        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const payload = await response.json();
        if (cancelled) {
          return;
        }

        setWeatherInfo({
          location: payload?.location ?? 'CABA · Microcentro',
          temperatureFormatted: payload?.temperatureFormatted ?? '---',
          condition: payload?.condition ?? 'Condiciones no disponibles',
          observedAt: payload?.observedAt ?? null,
        });
      } catch (error) {
        if (!cancelled) {
          setWeatherInfo((previous) => ({
            ...previous,
            temperatureFormatted: '---',
            condition: 'Sin datos recientes',
            observedAt: null,
          }));
        }
      } finally {
        if (!cancelled) {
          setWeatherLoading(false);
        }
      }
    }

    fetchWeather();

    return () => {
      cancelled = true;
    };
  }, []);

  useEffect(() => {
    setTickerItems((current) => {
      if (current.length) {
        return current;
      }
      const duplicated = [...NEWS_ITEMS, ...NEWS_ITEMS];
      return duplicated;
    });
  }, [NEWS_ITEMS]);

  const formattedAbove = branchStats.loading ? '---' : branchStats.above.toString();
  const formattedBelow = branchStats.loading ? '---' : branchStats.below.toString();
  const temperatureDisplay = weatherLoading ? '---' : weatherInfo.temperatureFormatted;
  const conditionDisplay = weatherLoading ? 'Actualizando...' : weatherInfo.condition;
  const observedTooltip = weatherInfo.observedAt
    ? new Date(weatherInfo.observedAt).toLocaleString('es-AR', {
        hour: '2-digit',
        minute: '2-digit',
      })
    : undefined;

  return (
    <main className="relative min-h-screen w-full overflow-hidden">
      {/* Background Video */}
      <video
        className="absolute inset-0 h-full w-full object-cover"
        autoPlay
        muted
        loop
        playsInline
      >
        <source src="/videoplayback (1).webm" type="video/webm" />
        Tu navegador no soporta video HTML5.
      </video>

      {/* Foreground: centered capibara above the video */}
      <div className="relative z-10 flex min-h-screen w-full flex-col items-center justify-center">
        {/* Circular container with the logo video inside */}
        <div className={styles.heroCircle} aria-label="Logo Capi en video" role="img">
          <video className={styles.heroVideo} autoPlay muted loop playsInline>
            <source src="/logocapi.mp4" type="video/mp4" />
            Tu navegador no soporta video HTML5.
          </video>
        </div>

        <div className={styles.teleprompterWrapper} role="complementary" aria-label="Ticker de información en tiempo real">
          <div className={styles.teleprompterStatic}>
            <div className={styles.weatherWidget}>
              <span className={styles.weatherIcon} aria-hidden="true">
                <svg viewBox="0 0 64 64" xmlns="http://www.w3.org/2000/svg">
                  <defs>
                    <linearGradient id="sunGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                      <stop offset="0%" stopColor="#fffb9a" />
                      <stop offset="100%" stopColor="#ffb347" />
                    </linearGradient>
                  </defs>
                  <circle cx="24" cy="24" r="12" fill="url(#sunGradient)" />
                  <path
                    d="M44 24c-8.837 0-16 7.163-16 16h16c8.837 0 16-7.163 16-16 0-6.627-5.373-12-12-12-4.418 0-8.268 2.402-10.344 6A15.92 15.92 0 0 1 44 24Z"
                    fill="rgba(94, 234, 212, 0.65)"
                  />
                </svg>
              </span>
              <div>
                <p className={styles.weatherLocation}>{weatherInfo.location}</p>
                <p
                  className={styles.weatherDetails}
                  title={observedTooltip ? `Actualizado ${observedTooltip}` : undefined}
                >
                  {temperatureDisplay}
                  <span className={styles.weatherDivider}>·</span>
                  {conditionDisplay}
                </p>
              </div>
            </div>

            <div className={styles.counterGroup}>
              <div className={styles.counterItem}>
                <span className={styles.counterLabel}>Sobre caja teórica</span>
                <span className={styles.counterValue} aria-live="polite">{formattedAbove}</span>
              </div>
              <div className={styles.counterItem}>
                <span className={styles.counterLabel}>Bajo caja teórica</span>
                <span className={styles.counterValue} aria-live="polite">{formattedBelow}</span>
              </div>
            </div>
          </div>

          <div className={styles.teleprompterTicker} aria-hidden="true">
            <div className={styles.tickerContent}>
              {tickerItems.map((headline, index) => (
                <span key={`${headline}-${index}`} className={styles.tickerItem}>
                  {headline}
                </span>
              ))}
            </div>
          </div>
        </div>
      </div>
    </main>
  );
}
