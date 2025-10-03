export const CHAT_THEME = {
  colors: {
    primary: '#00e5ff',
    primaryAlt: '#7df9ff',
    success: '#12d48a',
    text: '#e6f1ff',
    textMuted: '#8aa0c5',
    bg: '#0a0f1c',
    panel: 'rgba(14, 22, 38, 0.85)',
    border: '#1d2b4a'
  },
  spacing: { xs: 4, sm: 8, md: 12, lg: 16, xl: 20, xxl: 24 },
  fonts: {
    heading: "'Orbitron', ui-sans-serif, system-ui, sans-serif",
    ui: "'Inter', ui-sans-serif, system-ui, sans-serif"
  }
} as const;

export type ChatTheme = typeof CHAT_THEME;
