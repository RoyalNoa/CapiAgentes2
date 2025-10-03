import { useState, useEffect, useCallback } from 'react';

interface AlertContext {
  text: string;
  context: any;
}

export default function useAlertContext() {
  const [alertContext, setAlertContext] = useState<AlertContext | null>(null);

  // Expert-level alert-chat integration system
  useEffect(() => {
    const handleAlertContext = (event: any) => {
      if (event.detail?.text && event.detail?.context) {
        setAlertContext({
          text: event.detail.text,
          context: event.detail.context
        });
      }
    };

    window.addEventListener('add-to-chat', handleAlertContext);
    return () => window.removeEventListener('add-to-chat', handleAlertContext);
  }, []);

  // Accept alert context into input
  const acceptAlertContext = useCallback(() => {
    if (alertContext) {
      setAlertContext(null);
      return alertContext.text;
    }
    return null;
  }, [alertContext]);

  // Reject alert context
  const rejectAlertContext = useCallback(() => {
    setAlertContext(null);
  }, []);

  return {
    alertContext,
    acceptAlertContext,
    rejectAlertContext,
  };
}