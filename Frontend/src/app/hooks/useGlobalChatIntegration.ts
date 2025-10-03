'use client';

import { useCallback } from 'react';
import { useGlobalChat } from '@/app/contexts/GlobalChatContext';

/**
 * Hook for integrating existing page functionality with global chat
 * This allows pages like maps to interact with the global chat state
 * without duplicating chat instances or losing state.
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

  const openChatWith = useCallback((data: any) => {
    if (data?.sucursal) {
      setSelectedSucursal(data.sucursal);
    }
    setIsOpen(true);
  }, [setIsOpen, setSelectedSucursal]);

  const closeChatAndClear = useCallback(() => {
    setIsOpen(false);
    setSelectedSucursal(null);
  }, [setIsOpen, setSelectedSucursal]);

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
