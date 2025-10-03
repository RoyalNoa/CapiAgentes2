// Enhanced ChatBox logging utility
export class ChatBoxLogger {
  private static instance: ChatBoxLogger;

  static getInstance(): ChatBoxLogger {
    if (!ChatBoxLogger.instance) {
      ChatBoxLogger.instance = new ChatBoxLogger();
    }
    return ChatBoxLogger.instance;
  }

  private log(level: string, message: string, data?: any) {
    const timestamp = new Date().toISOString();
    const logMsg = `[${timestamp}] [CHATBOX-${level}] ${message}`;

    switch(level) {
      case 'INFO':
        console.log(logMsg, data || '');
        break;
      case 'WARN':
        console.warn(logMsg, data || '');
        break;
      case 'ERROR':
        console.error(logMsg, data || '');
        break;
      case 'DEBUG':
        console.debug(logMsg, data || '');
        break;
    }
  }

  info(message: string, data?: any) { this.log('INFO', message, data); }
  warn(message: string, data?: any) { this.log('WARN', message, data); }
  error(message: string, data?: any) { this.log('ERROR', message, data); }
  debug(message: string, data?: any) { this.log('DEBUG', message, data); }
}

// Export singleton instance for convenience
export const chatLogger = ChatBoxLogger.getInstance();