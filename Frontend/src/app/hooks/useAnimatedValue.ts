/**
 * useAnimatedValue Hook - Hook personalizado para animar valores numéricos
 * Proporciona funcionalidades avanzadas de animación con control granular
 */

'use client';

import { useState, useEffect, useRef, useCallback } from 'react';

export interface AnimationConfig {
  duration?: number;
  delay?: number;
  easing?: 'linear' | 'easeIn' | 'easeOut' | 'easeInOut' | 'bounce' | 'elastic';
  autoStart?: boolean;
  loop?: boolean;
  reverse?: boolean;
}

export interface UseAnimatedValueReturn {
  value: number;
  isAnimating: boolean;
  progress: number;
  start: () => void;
  stop: () => void;
  reset: () => void;
  setTarget: (newTarget: number) => void;
}

// Funciones de easing
const easingFunctions = {
  linear: (t: number) => t,
  easeIn: (t: number) => t * t * t,
  easeOut: (t: number) => 1 - Math.pow(1 - t, 3),
  easeInOut: (t: number) => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
  bounce: (t: number) => {
    const n1 = 7.5625;
    const d1 = 2.75;
    if (t < 1 / d1) {
      return n1 * t * t;
    } else if (t < 2 / d1) {
      return n1 * (t -= 1.5 / d1) * t + 0.75;
    } else if (t < 2.5 / d1) {
      return n1 * (t -= 2.25 / d1) * t + 0.9375;
    } else {
      return n1 * (t -= 2.625 / d1) * t + 0.984375;
    }
  },
  elastic: (t: number) => {
    const c4 = (2 * Math.PI) / 3;
    return t === 0 ? 0 : t === 1 ? 1 : -Math.pow(2, 10 * t - 10) * Math.sin((t * 10 - 10.75) * c4);
  }
};

export const useAnimatedValue = (
  targetValue: number,
  startValue: number = 0,
  config: AnimationConfig = {}
): UseAnimatedValueReturn => {
  const {
    duration = 1000,
    delay = 0,
    easing = 'easeOut',
    autoStart = true,
    loop = false,
    reverse = false
  } = config;

  const [currentValue, setCurrentValue] = useState(startValue);
  const [isAnimating, setIsAnimating] = useState(false);
  const [progress, setProgress] = useState(0);
  const [target, setTarget] = useState(targetValue);

  const frameRef = useRef<number>(0);
  const startTimeRef = useRef<number>(0);
  const startRef = useRef<() => void>(() => {});
  const startValueRef = useRef(startValue);

  const animate = useCallback((timestamp: number) => {
    if (startTimeRef.current === 0) {
      startTimeRef.current = timestamp;
    }

    const elapsed = timestamp - startTimeRef.current;
    const rawProgress = Math.min(elapsed / duration, 1);
    
    // Aplicar función de easing
    const easedProgress = easingFunctions[easing](rawProgress);
    const difference = target - startValueRef.current;
    const animatedValue = startValueRef.current + (difference * easedProgress);
    
    setCurrentValue(animatedValue);
    setProgress(rawProgress);

    if (rawProgress < 1) {
      frameRef.current = requestAnimationFrame(animate);
    } else {
      setIsAnimating(false);
      setProgress(1);
      
      if (loop) {
        // Reiniciar la animación para loop
        setTimeout(() => {
          if (reverse) {
            const temp = target;
            setTarget(startValueRef.current);
            startValueRef.current = temp;
          } else {
            startValueRef.current = startValue;
          }
          startRef.current();
        }, 100);
      }
    }
  }, [target, duration, easing, loop, reverse, startValue]);

  const start = useCallback(() => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
    }
    
    setIsAnimating(true);
    startTimeRef.current = 0;
    
    const startAnimation = () => {
      frameRef.current = requestAnimationFrame(animate);
    };

    if (delay > 0) {
      setTimeout(startAnimation, delay);
    } else {
      startAnimation();
    }
  }, [animate, delay]);

  useEffect(() => {
    startRef.current = start;
  }, [start]);

  const stop = useCallback(() => {
    if (frameRef.current) {
      cancelAnimationFrame(frameRef.current);
    }
    setIsAnimating(false);
  }, []);

  const reset = useCallback(() => {
    stop();
    setCurrentValue(startValue);
    setProgress(0);
    startValueRef.current = startValue;
  }, [stop, startValue]);

  const setTargetValue = useCallback((newTarget: number) => {
    startValueRef.current = currentValue;
    setTarget(newTarget);
  }, [currentValue]);

  // Auto-start effect
  useEffect(() => {
    if (autoStart && !isAnimating) {
      start();
    }
  }, [autoStart, start, isAnimating]);

  // Target change effect
  useEffect(() => {
    if (target !== targetValue) {
      setTargetValue(targetValue);
      if (!isAnimating && autoStart) {
        start();
      }
    }
  }, [targetValue, target, setTargetValue, start, autoStart, isAnimating]);

  // Cleanup effect
  useEffect(() => {
    return () => {
      if (frameRef.current) {
        cancelAnimationFrame(frameRef.current);
      }
    };
  }, []);

  return {
    value: currentValue,
    isAnimating,
    progress,
    start,
    stop,
    reset,
    setTarget: setTargetValue
  };
};

// Hook específico para animaciones de contadores
export const useCounterAnimation = (
  targetValue: number,
  options: {
    duration?: number;
    delay?: number;
    decimals?: number;
    startOnMount?: boolean;
  } = {}
) => {
  const {
    duration = 2000,
    delay = 0,
    decimals = 0,
    startOnMount = true
  } = options;

  const { value, isAnimating, start, reset } = useAnimatedValue(
    targetValue,
    0,
    {
      duration,
      delay,
      easing: 'easeOut',
      autoStart: startOnMount
    }
  );

  const formattedValue = decimals > 0 
    ? value.toFixed(decimals)
    : Math.floor(value).toString();

  return {
    value: formattedValue,
    rawValue: value,
    isAnimating,
    start,
    reset
  };
};

// Hook para animaciones con IntersectionObserver
export const useInViewAnimation = (
  targetValue: number,
  startValue: number = 0,
  config: AnimationConfig & { threshold?: number } = {}
) => {
  const { threshold = 0.1, ...animationConfig } = config;
  const [elementRef, setElementRef] = useState<Element | null>(null);
  const [hasAnimated, setHasAnimated] = useState(false);

  const {
    value,
    isAnimating,
    start,
    reset
  } = useAnimatedValue(targetValue, startValue, {
    ...animationConfig,
    autoStart: false
  });

  useEffect(() => {
    if (!elementRef || hasAnimated) return;

    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting && !hasAnimated) {
          start();
          setHasAnimated(true);
        }
      },
      { threshold }
    );

    observer.observe(elementRef);

    return () => {
      observer.unobserve(elementRef);
    };
  }, [elementRef, hasAnimated, start, threshold]);

  const resetAnimation = useCallback(() => {
    setHasAnimated(false);
    reset();
  }, [reset]);

  return {
    value,
    isAnimating,
    setElementRef,
    hasAnimated,
    resetAnimation
  };
};

export default useAnimatedValue;
