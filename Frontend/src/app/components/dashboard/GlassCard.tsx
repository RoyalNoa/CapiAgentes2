/**
 * GlassCard Component - Componente con efectos de glassmorfismo
 * Implementa un card moderno con blur backdrop, transparencias y efectos visuales
 */

import React from 'react';

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
  hover?: boolean;
  animated?: boolean;
  blur?: 'light' | 'medium' | 'strong';
  variant?: 'default' | 'frosted' | 'crystal' | 'minimal';
  onClick?: () => void;
}

export const GlassCard: React.FC<GlassCardProps> = ({
  children,
  className = '',
  hover = true,
  animated = true,
  blur = 'medium',
  variant = 'default',
  onClick
}) => {
  const getVariantClasses = () => {
    switch (variant) {
      case 'frosted':
        return 'glass-card-frosted';
      case 'crystal':
        return 'glass-card-crystal';
      case 'minimal':
        return 'glass-card-minimal';
      default:
        return 'glass-card';
    }
  };

  const getBlurClasses = () => {
    switch (blur) {
      case 'light':
        return 'glass-blur-light';
      case 'strong':
        return 'glass-blur-strong';
      default:
        return 'glass-blur-medium';
    }
  };

  const baseClasses = [
    getVariantClasses(),
    getBlurClasses(),
    hover && 'glass-hover',
    animated && 'glass-animated',
    onClick && 'glass-clickable',
    className
  ].filter(Boolean).join(' ');

  return (
    <div 
      className={baseClasses}
      onClick={onClick}
    >
      {children}
    </div>
  );
};

// Componente especializado para métricas
export const GlassMetricCard: React.FC<{
  title: string;
  value: string | number;
  subtitle?: string;
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'purple' | 'orange' | 'red';
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    value: string;
  };
  children?: React.ReactNode;
}> = ({
  title,
  value,
  subtitle,
  icon,
  color = 'blue',
  trend,
  children
}) => {
  const colorClasses = {
    blue: 'glass-accent-blue',
    green: 'glass-accent-green',
    purple: 'glass-accent-purple',
    orange: 'glass-accent-orange',
    red: 'glass-accent-red'
  };

  return (
    <GlassCard 
      variant="crystal" 
      className={`glass-metric-card ${colorClasses[color]} dashboard-animate-scale dashboard-stagger-1`}
    >
      <div className="glass-metric-header">
        <div className="glass-metric-title">
          <h3 className="glass-title-text">{title}</h3>
          {icon && (
            <div className="glass-metric-icon">
              {icon}
            </div>
          )}
        </div>
      </div>
      
      <div className="glass-metric-content">
        <div className="glass-metric-value">
          {value}
        </div>
        
        {subtitle && (
          <div className="glass-metric-subtitle">
            {subtitle}
          </div>
        )}
        
        {trend && (
          <div className={`glass-metric-trend glass-trend-${trend.direction}`}>
            <span className="glass-trend-icon">
              {trend.direction === 'up' && '↗'}
              {trend.direction === 'down' && '↙'}
              {trend.direction === 'neutral' && '→'}
            </span>
            <span className="glass-trend-value">{trend.value}</span>
          </div>
        )}
        
        {children}
      </div>
    </GlassCard>
  );
};

// Componente para contenedores de gráficos
export const GlassChartContainer: React.FC<{
  title: string;
  subtitle?: string;
  children: React.ReactNode;
  actions?: React.ReactNode;
}> = ({
  title,
  subtitle,
  children,
  actions
}) => {
  return (
    <GlassCard 
      variant="frosted" 
      className="glass-chart-container dashboard-animate-in dashboard-stagger-2"
    >
      <div className="glass-chart-header">
        <div className="glass-chart-title-section">
          <h3 className="glass-chart-title">{title}</h3>
          {subtitle && (
            <p className="glass-chart-subtitle">{subtitle}</p>
          )}
        </div>
        {actions && (
          <div className="glass-chart-actions">
            {actions}
          </div>
        )}
      </div>
      
      <div className="glass-chart-content">
        {children}
      </div>
    </GlassCard>
  );
};

export default GlassCard;