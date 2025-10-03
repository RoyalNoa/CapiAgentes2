let loggerConfigured = false;
let globalHandlersRegistered = false;

type ConsoleMethod = 'log' | 'info' | 'warn' | 'error' | 'debug';

type ConsoleMap = Record<ConsoleMethod, ConsoleMethod>;

const METHODS: ConsoleMethod[] = ['log', 'info', 'warn', 'error', 'debug'];
const SEND_LEVELS: Set<ConsoleMethod> = new Set(['error', 'warn']);
const CLIENT_ENDPOINT = '/api/logs/client';

const LEVEL_LABEL: Record<ConsoleMethod, string> = {
  log: 'INFO',
  info: 'INFO',
  warn: 'WARN',
  error: 'ERROR',
  debug: 'DEBUG',
};

const formatPrefix = (level: ConsoleMethod): string => {
  const timestamp = new Date().toISOString();
  const label = LEVEL_LABEL[level];
  const pathLabel = typeof window !== 'undefined' ? window.location.pathname : 'server';
  return `[${timestamp}] [Frontend] [${label}] [path=${pathLabel}]`;
};

const stringifyArgument = (value: unknown): string => {
  if (typeof value === 'string') {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const sendClientLog = (level: ConsoleMethod, args: unknown[], context?: Record<string, unknown>): void => {
  if (typeof window === 'undefined') {
    return;
  }

  if (!SEND_LEVELS.has(level)) {
    return;
  }

  const payload = {
    level,
    message: args.map(stringifyArgument).join(' '),
    timestamp: new Date().toISOString(),
    context: {
      path: window.location.pathname,
      ...(context ?? {}),
    },
  };

  try {
    const body = JSON.stringify(payload);
    if (navigator.sendBeacon) {
      const blob = new Blob([body], { type: 'application/json' });
      navigator.sendBeacon(CLIENT_ENDPOINT, blob);
    } else {
      void fetch(CLIENT_ENDPOINT, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body,
        keepalive: true,
      });
    }
  } catch {
    // swallow errors to avoid breaking console invocation
  }
};

const wrapConsoleMethod = (method: ConsoleMethod, original: (...args: unknown[]) => void) => {
  return (...args: unknown[]) => {
    const prefix = formatPrefix(method);
    try {
      original(prefix, ...args);
    } catch {
      original(prefix, '[Frontend] Logging failure while printing arguments');
    }
    sendClientLog(method, args);
  };
};

const registerGlobalClientHandlers = (): void => {
  if (globalHandlersRegistered || typeof window === 'undefined') {
    return;
  }

  window.addEventListener('error', (event) => {
    const context = {
      source: event.filename,
      line: event.lineno,
      column: event.colno,
      stack: event.error?.stack,
    };
    sendClientLog('error', [event.message], context);
  });

  window.addEventListener('unhandledrejection', (event) => {
    const reason = event.reason;
    const message =
      typeof reason === 'string'
        ? reason
        : reason?.message ?? stringifyArgument(reason ?? 'Unhandled rejection');

    const context: Record<string, unknown> = {
      type: 'unhandledrejection',
    };
    if (reason?.stack) {
      context.stack = reason.stack;
    }

    sendClientLog('error', [message], context);
  });

  globalHandlersRegistered = true;
};

export const initializeFrontendLogger = (): void => {
  if (loggerConfigured) {
    return;
  }

  METHODS.forEach((method) => {
    const original = console[method] as (...args: unknown[]) => void;
    console[method] = wrapConsoleMethod(method, original.bind(console));
  });

  registerGlobalClientHandlers();
  loggerConfigured = true;
};
