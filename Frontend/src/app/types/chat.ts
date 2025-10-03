// Shared types for chat components

export interface Message {
  id?: string;
  sender: 'user' | 'bot' | 'system';
  text: string;
  agent?: string;
  timestamp?: number;
  kind?: string;
  payload?: unknown;
  raw?: unknown;
}

export interface ChatBoxProps {
  sucursal?: any;
  onRemoveSucursal?: () => void;
}