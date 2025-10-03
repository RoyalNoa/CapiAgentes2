'use client';

import { useEffect, useState } from 'react';

interface ViewportData {
  zoom: number;
  isOptimal: boolean;
  recommendation: string;
  viewportHeight: number;
  viewportWidth: number;
  devicePixelRatio: number;
}

export const useViewportOptimization = () => {
  const [viewportData, setViewportData] = useState<ViewportData>({
    zoom: 1,
    isOptimal: true,
    recommendation: '',
    viewportHeight: 0,
    viewportWidth: 0,
    devicePixelRatio: 1
  });

  const [showZoomWarning, setShowZoomWarning] = useState(false);

  useEffect(() => {
    const detectViewportAndZoom = () => {
      const vw = Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0);
      const vh = Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0);
      const dpr = window.devicePixelRatio || 1;

      // Detectar zoom aproximado comparando con screen dimensions
      const screenWidth = window.screen.width;
      const screenHeight = window.screen.height;

      // Calcular zoom aproximado basado en la relación de viewport vs screen
      let estimatedZoom = 1;
      if (screenWidth > 0) {
        estimatedZoom = Math.round((screenWidth / vw) * 100) / 100;
      }

      // Determinar si la configuración actual es óptima para el HUD
      const minOptimalHeight = 700;
      const minOptimalWidth = 1200;

      let isOptimal = true;
      let recommendation = 'Configuración óptima para visualización HUD';
      let showWarning = false;

      // Detectar problemas comunes
      if (vh < minOptimalHeight && vw > minOptimalWidth) {
        isOptimal = false;
        recommendation = 'Zoom demasiado alto. Reduce el zoom del navegador (Ctrl + -)';
        showWarning = true;
      } else if (vh < 600 && vw < 1000) {
        isOptimal = false;
        recommendation = 'Pantalla pequeña detectada. El HUD se adaptará automáticamente';
        showWarning = false;
      } else if (vh < 500) {
        isOptimal = false;
        recommendation = 'Viewport muy pequeño. Considera reducir el zoom o usar pantalla completa (F11)';
        showWarning = true;
      } else if (vw < 900) {
        isOptimal = false;
        recommendation = 'Pantalla estrecha detectada. El HUD cambiará a modo columna única';
        showWarning = false;
      }

      setViewportData({
        zoom: estimatedZoom,
        isOptimal,
        recommendation,
        viewportHeight: vh,
        viewportWidth: vw,
        devicePixelRatio: dpr
      });

      setShowZoomWarning(showWarning);

      // Auto-ocultar warning después de 5 segundos
      if (showWarning) {
        setTimeout(() => setShowZoomWarning(false), 5000);
      }
    };

    // Ejecutar inmediatamente
    detectViewportAndZoom();

    // Escuchar cambios de viewport (zoom, resize, orientación)
    const handleResize = () => {
      detectViewportAndZoom();
    };

    window.addEventListener('resize', handleResize);
    window.addEventListener('orientationchange', handleResize);

    // Detectar cambios de zoom más precisos
    let resizeTimer: NodeJS.Timeout;
    const handleZoomChange = () => {
      clearTimeout(resizeTimer);
      resizeTimer = setTimeout(detectViewportAndZoom, 150);
    };

    window.addEventListener('resize', handleZoomChange);

    return () => {
      window.removeEventListener('resize', handleResize);
      window.removeEventListener('orientationchange', handleResize);
      window.removeEventListener('resize', handleZoomChange);
      clearTimeout(resizeTimer);
    };
  }, []);

  const dismissWarning = () => {
    setShowZoomWarning(false);
  };

  const resetZoom = () => {
    // Sugerir zoom óptimo basado en resolución de pantalla
    const screenWidth = window.screen.width;
    let optimalZoom = '100%';

    if (screenWidth >= 1920) {
      optimalZoom = '110%';
    } else if (screenWidth >= 1600) {
      optimalZoom = '100%';
    } else if (screenWidth >= 1366) {
      optimalZoom = '90%';
    } else if (screenWidth >= 1280) {
      optimalZoom = '85%';
    } else {
      optimalZoom = '80%';
    }

    alert(`Para una experiencia óptima, establece el zoom del navegador a ${optimalZoom}.\n\nUsa Ctrl + 0 para resetear a 100%, luego ajusta con Ctrl + + o Ctrl + -`);
  };

  return {
    viewportData,
    showZoomWarning,
    dismissWarning,
    resetZoom
  };
};