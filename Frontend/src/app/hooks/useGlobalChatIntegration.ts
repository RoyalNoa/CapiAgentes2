/**
 * @file useGlobalChatIntegration.ts
 * @module hooks
 * @description Hook para integrar funcionalidad de páginas con el chat global.
 * Permite que páginas como mapas interactúen con el estado del chat
 * sin duplicar instancias ni perder estado.
 */

'use client';

import { useCallback } from 'react';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';

/**
 * @function useGlobalChatIntegration
 * @description Hook que provee métodos de integración con el chat global CAPI.
 * Extiende useGlobalChat con funciones utilitarias para abrir/cerrar chat
 * y enviar mensajes con contexto de sucursal.
 * @returns {Object} Estado del chat y métodos de integración
 * @example
 * const { openChatWith, sendMessageAndOpen, isConnected } = useGlobalChatIntegration();
 * openChatWith({ sucursal: selectedBranch });
 */
export function useGlobalChatIntegration() {
  const {
    isOpen,
    setIsOpen,
    messages,
    loading,
    summary,
    anomalies,
    dashboard,
    sendCommand,
    connection,
    selectedSucursal,
    setSelectedSucursal,
    chatWidth,
    setChatWidth,
    chatPosition,
    setChatPosition,
    showSidebar,
    setShowSidebar,
  } = useGlobalChat();

  /**
   * Abre el chat con datos de contexto opcionales (ej. sucursal).
   */
  const openChatWith = useCallback((data: any) => {
    if (data?.sucursal) {
      setSelectedSucursal(data.sucursal);
    }
    setIsOpen(true);
  }, [setIsOpen, setSelectedSucursal]);

  /**
   * Cierra el chat y limpia la selección de sucursal.
   */
  const closeChatAndClear = useCallback(() => {
    setIsOpen(false);
    setSelectedSucursal(null);
  }, [setIsOpen, setSelectedSucursal]);

  /**
   * Envía un mensaje al chat y lo abre si está cerrado.
   */
  const sendMessageAndOpen = useCallback(async (message: string, contextData?: any) => {
    if (contextData?.sucursal) {
      setSelectedSucursal(contextData.sucursal);
    }
    setIsOpen(true);
    await sendCommand(message);
  }, [setSelectedSucursal, setIsOpen, sendCommand]);

  return {
    isOpen,
    setIsOpen,
    messages,
    loading,
    summary,
    anomalies,
    dashboard,
    sendCommand,
    connection,
    selectedSucursal,
    setSelectedSucursal,
    chatWidth,
    setChatWidth,
    chatPosition,
    setChatPosition,
    showSidebar,
    setShowSidebar,
    openChatWith,
    closeChatAndClear,
    sendMessageAndOpen,
    isChatAvailable: true,
    hasMessages: messages.length > 0,
    isConnected: connection.status === 'open',
  };
}
