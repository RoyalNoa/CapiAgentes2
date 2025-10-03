/**
 * AnimatedCounter Component - Contador animado para valores numericos
 * Anima la transicion entre valores con efectos visuales suaves
 */

'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';

interface AnimatedCounterProps {
  value: number;
  duration?: number;
  delay?: number;
  decimals?: number;
  prefix?: string;
  suffix?: string;
  className?: string;
  formatter?: (value: number) => string;
  trigger?: boolean;
}

export const AnimatedCounter: React.FC<AnimatedCounterProps> = ({
  value,
  duration = 2000,
  delay = 0,
  decimals = 0,
  prefix = '',
  suffix = '',
  className = '',
  formatter,
  trigger = true
}) => {
  const [currentValue, setCurrentValue] = useState(0);
  const [isAnimating, setIsAnimating] = useState(false);
  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);

  const formatValue = (val: number): string => {
    if (formatter) {
      return formatter(val);
    }

    const formattedValue = decimals > 0 ? val.toFixed(decimals) : Math.floor(val).toString();
    return `${prefix}${formattedValue}${suffix}`;
  };

  const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3);

  const animate = useCallback(
    (timestamp: number) => {
      if (startTimeRef.current === 0) {
        startTimeRef.current = timestamp;
      }

      const elapsed = timestamp - startTimeRef.current;
      const progress = Math.min(elapsed / duration, 1);
      const easedProgress = easeOutCubic(progress);
      const animatedValue = easedProgress * value;

      setCurrentValue(animatedValue);

      if (progress < 1) {
        frameRef.current = requestAnimationFrame(animate);
      } else {
        setIsAnimating(false);
        startTimeRef.current = 0;
      }
    },
    [duration, value]
  );

  useEffect(() => {
    if (!trigger) {
      return undefined;
    }

    const startAnimation = () => {
      setIsAnimating(true);
      setCurrentValue(0);
      startTimeRef.current = 0;

      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }

      frameRef.current = requestAnimationFrame(animate);
    };

    let timer: ReturnType<typeof setTimeout> | undefined;

    if (delay > 0) {
      timer = setTimeout(startAnimation, delay);
    } else {
      startAnimation();
    }

    return () => {
      if (timer) {
        clearTimeout(timer);
      }
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
        frameRef.current = 0;
      }
    };
  }, [animate, delay, trigger]);

  return (
    <span className={`animated-counter ${isAnimating ? 'counting' : ''} ${className}`.trim()}>
      {formatValue(currentValue)}
    </span>
  );
};

// Contador especifico para monedas
export const CurrencyCounter: React.FC<{
  value: number;
  currency?: string;
  locale?: string;
  duration?: number;
  delay?: number;
  className?: string;
  trigger?: boolean;
}> = ({
  value,
  currency = 'COP',
  locale = 'es-CO',
  duration = 2000,
  delay = 0,
  className = '',
  trigger = true
}) => {
  const formatter = (val: number) =>
    new Intl.NumberFormat(locale, {
      style: 'currency',
      currency,
      minimumFractionDigits: 0,
      maximumFractionDigits: 0
    }).format(val);

  return (
    <AnimatedCounter
      value={value}
      duration={duration}
      delay={delay}
      className={className}
      formatter={formatter}
      trigger={trigger}
    />
  );
};

// Contador para porcentajes
export const PercentageCounter: React.FC<{
  value: number;
  decimals?: number;
  duration?: number;
  delay?: number;
  className?: string;
  trigger?: boolean;
}> = ({
  value,
  decimals = 1,
  duration = 2000,
  delay = 0,
  className = '',
  trigger = true
}) => (
  <AnimatedCounter
    value={value}
    decimals={decimals}
    duration={duration}
    delay={delay}
    suffix="%"
    className={className}
    trigger={trigger}
  />
);
