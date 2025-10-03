/**
 * Ruta: Frontend/src/app/layout.tsx
 * Descripción: Root layout del Frontend. Aplica tema HUD (Ironman) y tipografías globales.
 * Estado: Activo
 * Autor: Copilot
 * Última actualización: 2025-09-14
 * Referencias: AI/estandares.md
 */
'use client';

import "@/app/ui/globals.css";
import "@/app/ui/hud.css";
import { Inter, Orbitron } from 'next/font/google';
import { useEffect } from 'react';
import { initializeFrontendLogger } from './utils/logger';
import Footer from "./components/footer/Footer";
import HUDNavigator from "./components/HUD/HUDNavigator";
import { GlobalChatProvider } from "./contexts/GlobalChatContext";
import { GlobalAlertProvider } from "./contexts/GlobalAlertContext";
import { HistoricalAlertsProvider } from "./contexts/HistoricalAlertsContext";
import GlobalChatOverlay from "./components/chat/GlobalChatOverlay";
import ChatToggleButton from "./components/chat/ChatToggleButton";
import HistoricalAlertsSystem from "./components/alerts/HistoricalAlertsSystem";
import { usePathname } from 'next/navigation';

const inter = Inter({ subsets: ['latin'], weight: ['400', '500', '600', '700'], display: 'swap', variable: '--font-inter' });
const orbitron = Orbitron({ subsets: ['latin'], weight: ['600', '700', '800'], display: 'swap', variable: '--font-orbitron' });

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const pathname = usePathname();

  useEffect(() => {
    initializeFrontendLogger();
  }, []);

  // Check if we're on the agents page (immersive HUD mode)
  const isAgentsPage = pathname === '/pages/agentes';
  const isMapPage = pathname?.startsWith('/pages/map');

  return (
    <html lang="en" className={`${inter.variable} ${orbitron.variable}`}> 
      <head>
        {/* Tipografías Google: Orbitron (headings HUD) + Inter (UI) */}
      </head>
      <body className={`Content hud-root ${isAgentsPage ? 'immersive-hud' : ''}`}>
        <GlobalChatProvider>
          <GlobalAlertProvider>
            <HistoricalAlertsProvider>
              <HUDNavigator />

              {children}

              {!isAgentsPage && !isMapPage && <Footer />}

              {/* Global Chat System - Available on ALL pages */}
              <GlobalChatOverlay />
              <ChatToggleButton />

              {/* Historical Alerts System - Sourced from database */}
              <HistoricalAlertsSystem />
            </HistoricalAlertsProvider>
          </GlobalAlertProvider>
        </GlobalChatProvider>
      </body>
    </html>
  );
}

