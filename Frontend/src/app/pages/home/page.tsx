"use client";
import { useState, useEffect } from "react";
import Link from "next/link";
import "./styles.css";

interface SystemMetrics {
  totalRevenue: number;
  activeBranches: number;
  anomaliesDetected: number;
  systemStatus: "online" | "offline" | "maintenance";
  lastUpdate: string;
}

export default function Home() {
  const [metrics, setMetrics] = useState<SystemMetrics | null>(null);
  const [currentTime, setCurrentTime] = useState<string>("");

  useEffect(() => {
    const updateClock = () => {
      setCurrentTime(
        new Date().toLocaleTimeString("es-AR", {
          hour: "2-digit",
          minute: "2-digit",
          second: "2-digit",
        })
      );
    };

    const fetchMetrics = async () => {
      try {
        const response = await fetch("/api/health");
        if (response.ok) {
          setMetrics({
            totalRevenue: 15420000 + Math.floor(Math.random() * 1000000),
            activeBranches: 47,
            anomaliesDetected: Math.floor(Math.random() * 5),
            systemStatus: "online",
            lastUpdate: new Date().toLocaleTimeString(),
          });
        } else {
          setMetrics((prev) => ({
            totalRevenue: prev?.totalRevenue ?? 0,
            activeBranches: prev?.activeBranches ?? 0,
            anomaliesDetected: prev?.anomaliesDetected ?? 0,
            systemStatus: "offline",
            lastUpdate: new Date().toLocaleTimeString(),
          }));
        }
      } catch (error) {
        console.error("Error fetching metrics:", error);
        setMetrics((prev) => ({
          totalRevenue: prev?.totalRevenue ?? 0,
          activeBranches: prev?.activeBranches ?? 0,
          anomaliesDetected: prev?.anomaliesDetected ?? 0,
          systemStatus: "offline",
          lastUpdate: new Date().toLocaleTimeString(),
        }));
      }
    };

    updateClock();
    void fetchMetrics();

    const timeInterval = setInterval(updateClock, 1000);
    const metricsInterval = setInterval(fetchMetrics, 30000);

    return () => {
      clearInterval(timeInterval);
      clearInterval(metricsInterval);
    };
  }, []);

  const formatCurrency = (amount?: number) => {
    if (typeof amount !== "number" || Number.isNaN(amount)) {
      return "-";
    }
    return new Intl.NumberFormat("es-AR", {
      style: "currency",
      currency: "ARS",
      minimumFractionDigits: 0,
    }).format(amount);
  };

  const status = metrics?.systemStatus ?? "offline";
  const lastUpdate = metrics?.lastUpdate ?? "--:--:--";

  return (
    <div className="hud-container">
      {/* Header HUD */}
      <header className="hud-header">
        <div className="hud-brand">
          <div className="brand-logo">??</div>
          <div className="brand-text">
            <h1>
              CAPI<span>AGENTES</span>
            </h1>
            <span className="brand-subtitle">Financial Intelligence Hub</span>
          </div>
        </div>

        <div className="hud-status">
          <div className="status-indicator">
            <div className={`status-light ${status}`}></div>
            <span>Sistema {status.toUpperCase()}</span>
          </div>
          <div className="hud-time">{currentTime || "--:--:--"}</div>
        </div>
      </header>

      {/* Metrics Grid */}
      <div className="hud-metrics-grid">
        <div className="metric-card revenue">
          <div className="metric-icon">??</div>
          <div className="metric-content">
            <h3>Ingresos Totales</h3>
            <div className="metric-value">{formatCurrency(metrics?.totalRevenue)}</div>
            <div className="metric-change positive">+12.5% vs ayer</div>
          </div>
        </div>

        <div className="metric-card branches">
          <div className="metric-icon">??</div>
          <div className="metric-content">
            <h3>Sucursales Activas</h3>
            <div className="metric-value">{metrics?.activeBranches ?? "--"}</div>
            <div className="metric-change neutral">100% operativas</div>
          </div>
        </div>

        <div className="metric-card anomalies">
          <div className="metric-icon">??</div>
          <div className="metric-content">
            <h3>Anomalías</h3>
            <div className="metric-value">{metrics?.anomaliesDetected ?? "--"}</div>
            <div className="metric-change warning">Requieren atención</div>
          </div>
        </div>

        <div className="metric-card agents">
          <div className="metric-icon">??</div>
          <div className="metric-content">
            <h3>Agentes IA</h3>
            <div className="metric-value">4</div>
            <div className="metric-change positive">Todos activos</div>
          </div>
        </div>
      </div>

      {/* Navigation Grid */}
      <div className="hud-nav-grid">
        <Link href="/dashboard" className="nav-module dashboard">
          <div className="module-header">
            <div className="module-icon">??</div>
            <h3>Dashboard Ejecutivo</h3>
          </div>
          <div className="module-content">
            <p>Análisis financiero completo con métricas en tiempo real</p>
            <div className="module-stats">
              <span>47 sucursales monitoreadas</span>
            </div>
          </div>
          <div className="module-footer">
            <span className="access-btn">ACCEDER ⇢</span>
          </div>
        </Link>

        <Link href="/pages/map" className="nav-module map">
          <div className="module-header">
            <div className="module-icon">???</div>
            <h3>Mapa Inteligente</h3>
          </div>
          <div className="module-content">
            <p>Visualización geográfica con chat AI integrado</p>
            <div className="module-stats">
              <span>Geolocalización en tiempo real</span>
            </div>
          </div>
          <div className="module-footer">
            <span className="access-btn">EXPLORAR ⇢</span>
          </div>
        </Link>

        <Link href="/workspace" className="nav-module workspace">
          <div className="module-header">
            <div className="module-icon">??</div>
            <h3>AI Workspace</h3>
          </div>
          <div className="module-content">
            <p>Gestión de agentes y base de conocimiento</p>
            <div className="module-stats">
              <span>4 agentes especializados</span>
            </div>
          </div>
          <div className="module-footer">
            <span className="access-btn">GESTIONAR ⇢</span>
          </div>
        </Link>
      </div>

      {/* Quick Actions */}
      <div className="hud-actions">
        <button className="action-btn primary">
          <span className="action-icon">?</span>
          Análisis Rápido
        </button>
        <button className="action-btn secondary">
          <span className="action-icon">??</span>
          Detectar Anomalías
        </button>
        <button className="action-btn tertiary">
          <span className="action-icon">??</span>
          Generar Reporte
        </button>
      </div>

      {/* Footer Info */}
      <footer className="hud-footer">
        <div className="footer-info">
          <span>Última actualización: {lastUpdate}</span>
        </div>
        <div className="footer-version">
          <span>CapiAgentes v2.0 | LangGraph Intelligence</span>
        </div>
      </footer>
    </div>
  );
}
