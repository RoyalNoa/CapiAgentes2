'use client';

import React from 'react';

type NavigationMode = 'client' | 'developer';

interface NavigationModeContextValue {
  mode: NavigationMode;
  isDeveloper: boolean;
  setMode: (mode: NavigationMode) => void;
  toggleMode: () => void;
}

const STORAGE_KEY = 'capi.navigationMode';

const NavigationModeContext = React.createContext<NavigationModeContextValue | undefined>(undefined);

export function NavigationModeProvider({
  children,
}: {
  children: React.ReactNode;
}) {
  const [mode, setModeState] = React.useState<NavigationMode>('client');

  React.useEffect(() => {
    if (typeof window === 'undefined') {
      return;
    }

    const stored = window.localStorage.getItem(STORAGE_KEY);
    if (stored === 'client' || stored === 'developer') {
      setModeState(stored);
    }
  }, []);

  const updateMode = React.useCallback((next: NavigationMode) => {
    setModeState(next);

    if (typeof window !== 'undefined') {
      window.localStorage.setItem(STORAGE_KEY, next);
    }
  }, []);

  const toggleMode = React.useCallback(() => {
    updateMode(mode === 'developer' ? 'client' : 'developer');
  }, [mode, updateMode]);

  const value = React.useMemo(
    () => ({
      mode,
      isDeveloper: mode === 'developer',
      setMode: updateMode,
      toggleMode,
    }),
    [mode, updateMode, toggleMode],
  );

  return <NavigationModeContext.Provider value={value}>{children}</NavigationModeContext.Provider>;
}

export function useNavigationMode(): NavigationModeContextValue {
  const context = React.useContext(NavigationModeContext);

  if (!context) {
    throw new Error('useNavigationMode must be used within a NavigationModeProvider');
  }

  return context;
}
