/**
 * Dashboard Service - Manejo de datos para el dashboard ejecutivo
 * Proporciona datos procesados y KPIs para la gestión de distribución de efectivo
 */

export interface DashboardData {
  metrics: {
    totalCash: number;
    netFlow: number;
    activeBranches: number;
    criticalAlerts: number;
  };
  branchPerformance: BranchPerformance[];
  cashFlow: CashFlowData[];
  denominations: DenominationData[];
  anomalies: AnomalyData[];
  summary: any;
}

export interface BranchPerformance {
  branch: string;
  cajero: string;
  totalIncome: number;
  totalExpenses: number;
  netFlow: number;
  efficiency: number;
  status: 'excellent' | 'good' | 'warning' | 'critical';
}

export interface CashFlowData {
  date: string;
  ingresos: number;
  egresos: number;
  net: number;
}

export interface DenominationData {
  denomination: string;
  amount: number;
  count: number;
  percentage: number;
}

export interface AnomalyData {
  id: string;
  branch: string;
  type: string;
  severity: 'high' | 'medium' | 'low';
  description: string;
  timestamp: string;
}

class DashboardService {
  private readonly configuredApiBase = (process.env.NEXT_PUBLIC_API_BASE ?? 'http://backend:8000').replace(/\/$/, '');

  private resolveApiBase(): string {
    if (typeof window === 'undefined') {
      return this.configuredApiBase;
    }

    if (!this.configuredApiBase || this.configuredApiBase.includes('://backend')) {
      try {
        const parsed = new URL(this.configuredApiBase || 'http://backend:8000');
        const protocol = window.location.protocol || parsed.protocol || 'http:';
        const hostname = window.location.hostname || parsed.hostname;
        const port = parsed.port || '8000';
        const normalizedPort = port && port !== '80' && port !== '443' ? `:${port}` : '';
        return `${protocol}//${hostname}${normalizedPort}`;
      } catch {
        const protocol = window.location.protocol || 'http:';
        const hostname = window.location.hostname || 'localhost';
        return `${protocol}//${hostname}:8000`;
      }
    }

    return this.configuredApiBase;
  }

  private buildUrl(path: string): string {
    if (/^https?:\/\//i.test(path)) {
      return path;
    }
    const normalized = path.startsWith('/') ? path : `/${path}`;
    const base = this.resolveApiBase();
    return base ? `${base}${normalized}` : normalized;
  }


  /**
   * Obtener todos los datos del dashboard
   */
  async getDashboardData(): Promise<DashboardData> {
    try {
      // Solicitar resumen general
      const summaryResponse = await this.makeRequest('Dame un resumen completo de los datos');
      
      // Solicitar datos específicos
      const [branchData, anomalyData] = await Promise.all([
        this.makeRequest('Muestra las mejores sucursales por ingresos'),
        this.makeRequest('¿Hay anomalías detectadas?')
      ]);

      return this.processRawData(summaryResponse, branchData, anomalyData);
    } catch (error) {
      console.error('Error fetching dashboard data:', error);
      throw new Error('Failed to load real data from backend. No fallback data allowed per ARCHITECTURE.md');
    }
  }

  /**
   * Hacer solicitud al orquestador
   */
  private async makeRequest(instruction: string): Promise<any> {
    const response = await fetch(this.buildUrl('/api/command'), {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        instruction,
        client_id: 'dashboard'
      })
    });

    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }

    return response.json();
  }

  /**
   * Procesar datos raw del backend (usando métricas estructuradas)
   */
  private processRawData(summaryData: any, branchData: any, anomalyData: any): DashboardData {
    // Acceder a métricas estructuradas del ResponseEnvelope
    const envelopeData = summaryData.envelope?.data || summaryData.response?.data || {};
    const structuredMetrics = envelopeData.metrics || {};
    
    // Usar métricas estructuradas directamente (elimina parsing frágil)
    const totalCash = structuredMetrics.total_cash || 0;
    const totalExpenses = structuredMetrics.total_expenses || 0;
    const netFlow = structuredMetrics.net_flow || (totalCash - totalExpenses);
    const activeBranches = structuredMetrics.branch_count || 0;
    const criticalAlerts = structuredMetrics.anomaly_count || 0;

    return {
      metrics: {
        totalCash,
        netFlow,
        activeBranches,
        criticalAlerts
      },
      branchPerformance: [],
      cashFlow: [],
      denominations: [],
      anomalies: this.processAnomalies(anomalyData),
      summary: summaryData.response
    };
  }

  // FAKE DATA GENERATION METHODS ELIMINATED per ARCHITECTURE.md



  /**
   * Process anomalies from REAL data only
   */
  private processAnomalies(anomalyData: any): AnomalyData[] {
    if (!anomalyData) return [];
    // Process real anomaly data from backend
    return anomalyData.anomalies || [];
  }

  // MOCK DATA METHOD ELIMINATED per ARCHITECTURE.md

  /**
   * Formatear números como moneda
   */
  formatCurrency(amount: number): string {
    return new Intl.NumberFormat('es-CO', {
      style: 'currency',
      currency: 'COP',
      minimumFractionDigits: 0
    }).format(amount);
  }

  /**
   * Formatear números con separadores
   */
  formatNumber(num: number): string {
    return new Intl.NumberFormat('es-CO').format(num);
  }
}

export const dashboardService = new DashboardService();