// Main component
export { default as SimpleChatBox } from './SimpleChatBox';

// Specialized components
export { default as HolographicContainer } from './effects/HolographicContainer';
export { default as HolographicGrid } from './effects/HolographicGrid';
export { default as ChatHeader } from './header/ChatHeader';
export { default as MessageArea } from './messages/MessageArea';
export { default as MessageBubble } from './messages/MessageBubble';
export { default as ProcessingView } from './messages/ProcessingView';
export { default as VoiceInterface } from './voice/VoiceInterface';
export { default as ChatInput } from './input/ChatInput';
export { default as PendingActions } from './actions/PendingActions';

// Specialized hooks
export { default as useVoiceInterface } from './hooks/useVoiceInterface';
export { default as useAlertContext } from './hooks/useAlertContext';