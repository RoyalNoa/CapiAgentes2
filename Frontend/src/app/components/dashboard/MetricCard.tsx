/**
 * MetricCard Component - Tarjeta de KPI moderna con efectos de glassmorfismo
 * Muestra métricas clave con iconos, valores animados y tendencias visuales
 */

'use client';

import React, { useState, useEffect } from 'react';
import { AnimatedCounter, CurrencyCounter, PercentageCounter } from './AnimatedCounter';

interface MetricCardProps {
  title: string;
  value: string | number;
  subtitle?: string;
  trend?: {
    direction: 'up' | 'down' | 'neutral';
    percentage: number;
    period: string;
  };
  icon?: React.ReactNode;
  color?: 'blue' | 'green' | 'red' | 'orange' | 'purple';
  isLoading?: boolean;
  animated?: boolean;
  format?: 'currency' | 'percentage' | 'number' | 'custom';
  currency?: string;
  locale?: string;
}

const modernColorClasses = {
  blue: {
    glass: 'glass-accent-blue',
    gradient: 'from-blue-400 to-blue-600',
    glow: 'shadow-blue-500/25',
    text: 'text-blue-100'
  },
  green: {
    glass: 'glass-accent-green',
    gradient: 'from-green-400 to-green-600',
    glow: 'shadow-green-500/25',
    text: 'text-green-100'
  },
  red: {
    glass: 'glass-accent-red',
    gradient: 'from-red-400 to-red-600',
    glow: 'shadow-red-500/25',
    text: 'text-red-100'
  },
  orange: {
    glass: 'glass-accent-orange',
    gradient: 'from-orange-400 to-orange-600',
    glow: 'shadow-orange-500/25',
    text: 'text-orange-100'
  },
  purple: {
    glass: 'glass-accent-purple',
    gradient: 'from-purple-400 to-purple-600',
    glow: 'shadow-purple-500/25',
    text: 'text-purple-100'
  }
};

const TrendIcon: React.FC<{ direction: 'up' | 'down' | 'neutral' }> = ({ direction }) => {
  if (direction === 'up') {
    return (
      <svg className="w-4 h-4 text-green-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M3.293 9.707a1 1 0 010-1.414l6-6a1 1 0 011.414 0l6 6a1 1 0 01-1.414 1.414L11 5.414V17a1 1 0 11-2 0V5.414L4.707 9.707a1 1 0 01-1.414 0z" clipRule="evenodd" />
      </svg>
    );
  }
  
  if (direction === 'down') {
    return (
      <svg className="w-4 h-4 text-red-500" fill="currentColor" viewBox="0 0 20 20">
        <path fillRule="evenodd" d="M16.707 10.293a1 1 0 010 1.414l-6 6a1 1 0 01-1.414 0l-6-6a1 1 0 011.414-1.414L9 14.586V3a1 1 0 012 0v11.586l4.293-4.293a1 1 0 011.414 0z" clipRule="evenodd" />
      </svg>
    );
  }

  return (
    <svg className="w-4 h-4 text-gray-400" fill="currentColor" viewBox="0 0 20 20">
      <path fillRule="evenodd" d="M3 10a1 1 0 011-1h12a1 1 0 110 2H4a1 1 0 01-1-1z" clipRule="evenodd" />
    </svg>
  );
};

export const MetricCard: React.FC<MetricCardProps> = ({
  title,
  value,
  subtitle,
  trend,
  icon,
  color = 'blue',
  isLoading = false,
  animated = true,
  format = 'custom',
  currency = 'COP',
  locale = 'es-CO'
}) => {
  const [isVisible, setIsVisible] = useState(false);
  const colorClass = modernColorClasses[color];
  
  // Convert value to number for animations
  const numericValue = typeof value === 'string' ? parseFloat(value.replace(/[^0-9.-]/g, '')) : value;
  const isValidNumber = !isNaN(numericValue);

  useEffect(() => {
    // Trigger visibility for staggered animations
    const timer = setTimeout(() => setIsVisible(true), 100);
    return () => clearTimeout(timer);
  }, []);

  const renderAnimatedValue = () => {
    if (!animated || !isValidNumber) {
      return typeof value === 'number' 
        ? new Intl.NumberFormat(locale).format(value)
        : value;
    }

    switch (format) {
      case 'currency':
        return (
          <CurrencyCounter
            value={numericValue}
            currency={currency}
            locale={locale}
            duration={2500}
            delay={200}
            trigger={isVisible}
          />
        );
      case 'percentage':
        return (
          <PercentageCounter
            value={numericValue}
            decimals={1}
            duration={2000}
            delay={200}
            trigger={isVisible}
          />
        );
      case 'number':
        return (
          <AnimatedCounter
            value={numericValue}
            duration={2200}
            delay={200}
            decimals={0}
            trigger={isVisible}
            formatter={(val) => new Intl.NumberFormat(locale).format(val)}
          />
        );
      default:
        return (
          <AnimatedCounter
            value={numericValue}
            duration={2200}
            delay={200}
            trigger={isVisible}
            formatter={(val) => typeof value === 'string' && value.includes('$')
              ? new Intl.NumberFormat(locale, { style: 'currency', currency }).format(val)
              : new Intl.NumberFormat(locale).format(val)
            }
          />
        );
    }
  };
  
  if (isLoading) {
    return (
      <div className={`glass-metric-card ${colorClass.glass} skeleton`}>
        <div className="glass-metric-header">
          <div className="glass-metric-title">
            <div className="h-4 bg-white/20 rounded w-1/2 mb-2"></div>
            <div className="h-10 w-10 bg-white/20 rounded-xl"></div>
          </div>
        </div>
        <div className="glass-metric-content">
          <div className="h-12 bg-white/20 rounded w-3/4 mb-3"></div>
          <div className="h-4 bg-white/20 rounded w-1/2"></div>
        </div>
      </div>
    );
  }

  return (
    <div 
      className={`
        glass-metric-card 
        ${colorClass.glass} 
        glass-hover 
        glass-animated
        dashboard-animate-scale
        transition-all duration-300 ease-out
        ${isVisible ? 'opacity-100 translate-y-0' : 'opacity-0 translate-y-4'}
      `}
      style={{ 
        transitionDelay: '100ms',
        animation: 'dashboard-fade-in 0.6s ease-out forwards'
      }}
    >
      {/* Header moderno */}
      <div className="glass-metric-header">
        <div className="glass-metric-title">
          <h3 className="glass-title-text">
            {title}
          </h3>
          {icon && (
            <div className="glass-metric-icon group-hover:scale-110 transition-transform duration-300">
              {icon}
            </div>
          )}
        </div>
      </div>

      {/* Contenido principal */}
      <div className="glass-metric-content">
        <div className="glass-metric-value group-hover:scale-105 transition-transform duration-300">
          {renderAnimatedValue()}
        </div>
        
        {subtitle && (
          <div className="glass-metric-subtitle">
            {subtitle}
          </div>
        )}
        
        {trend && (
          <div className={`glass-metric-trend glass-trend-${trend.direction}`}>
            <span className="glass-trend-icon transform transition-transform duration-300 group-hover:scale-125">
              <TrendIcon direction={trend.direction} />
            </span>
            <span className="glass-trend-value">
              {animated ? (
                <PercentageCounter
                  value={trend.percentage}
                  decimals={1}
                  duration={1500}
                  delay={600}
                  trigger={isVisible}
                />
              ) : (
                `${trend.percentage}%`
              )}
              <span className="text-xs ml-1 opacity-75">{trend.period}</span>
            </span>
          </div>
        )}
      </div>

      {/* Efecto de hover flotante */}
      <div className="absolute inset-0 opacity-0 group-hover:opacity-100 transition-opacity duration-500 pointer-events-none">
        <div className="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-white/5 rounded-full blur-xl"></div>
      </div>
    </div>
  );
};

// Componentes de iconos específicos para métricas financieras
export const CashIcon: React.FC = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8c-1.657 0-3 .895-3 2s1.343 2 3 2 3 .895 3 2-1.343 2-3 2m0-8c1.11 0 2.08.402 2.599 1M12 8V7m0 1v8m0 0v1m0-1c-1.11 0-2.08-.402-2.599-1" />
  </svg>
);

export const TrendUpIcon: React.FC = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13 7h8m0 0v8m0-8l-8 8-4-4-6 6" />
  </svg>
);

export const BuildingIcon: React.FC = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4" />
  </svg>
);

export const AlertIcon: React.FC = () => (
  <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
  </svg>
);

export default MetricCard;