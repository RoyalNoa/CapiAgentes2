import fs from "fs";
import path from "path";

export type ConsoleMethod = "log" | "info" | "warn" | "error" | "debug";

const METHODS: ConsoleMethod[] = ["log", "info", "warn", "error", "debug"];
const LEVEL_LABEL: Record<ConsoleMethod, string> = {
  log: "INFO",
  info: "INFO",
  warn: "WARN",
  error: "ERROR",
  debug: "DEBUG",
};

type LogOrigin = "FrontendServer" | "FrontendClient";

type ClientLogPayload = {
  level: ConsoleMethod | string;
  message: string;
  timestamp?: string;
  context?: Record<string, unknown>;
};

let stream: fs.WriteStream | null = null;
let patched = false;

const ensureStream = (): fs.WriteStream => {
  if (stream) {
    return stream;
  }

  const logDirectory = path.resolve(process.cwd(), "logs");
  if (!fs.existsSync(logDirectory)) {
    fs.mkdirSync(logDirectory, { recursive: true });
  }

  const target = path.join(logDirectory, "front.log");
  stream = fs.createWriteStream(target, { flags: "a" });
  return stream;
};

const stringifyArgument = (value: unknown): string => {
  if (typeof value === "string") {
    return value;
  }
  try {
    return JSON.stringify(value);
  } catch {
    return String(value);
  }
};

const formatArgs = (args: unknown[]): string => args.map(stringifyArgument).join(" ");

const writeLogLine = (
  origin: LogOrigin,
  level: ConsoleMethod,
  message: string,
  context?: Record<string, unknown>,
): void => {
  const timestamp = new Date().toISOString();
  const label = LEVEL_LABEL[level];
  const contextSegment = context && Object.keys(context).length > 0 ? ` ${JSON.stringify(context)}` : "";
  ensureStream().write(`[${timestamp}] [${origin}] [${label}] ${message}${contextSegment}\n`);
};

const patchConsoleMethod = (method: ConsoleMethod): void => {
  const original = console[method].bind(console);

  console[method] = (...args: unknown[]): void => {
    original(...args);

    try {
      const message = formatArgs(args);
      writeLogLine("FrontendServer", method, message);
    } catch (error) {
      original("[Frontend] logger failure", error);
    }
  };
};

const logUnhandledError = (message: string, context?: Record<string, unknown>): void => {
  try {
    writeLogLine("FrontendServer", "error", message, context);
  } catch (error) {
    // eslint-disable-next-line no-console
    console.error("[Frontend] failed to persist unhandled error", error);
  }
};

export const appendClientLog = (payload: ClientLogPayload): void => {
  const candidate = typeof payload.level === "string" ? payload.level.toLowerCase() : payload.level;
  const normalizedLevel: ConsoleMethod =
    METHODS.includes(candidate as ConsoleMethod) ? (candidate as ConsoleMethod) : "info";

  const context = payload.context && Object.keys(payload.context).length > 0 ? payload.context : undefined;
  const timestamp = payload.timestamp ?? new Date().toISOString();

  writeLogLine("FrontendClient", normalizedLevel, payload.message, {
    timestamp,
    ...(context ?? {}),
  });
};

export const setupServerLogger = (): void => {
  if (patched) {
    return;
  }

  if (typeof window !== "undefined") {
    return;
  }

  METHODS.forEach(patchConsoleMethod);

  process.on("uncaughtException", (error: unknown) => {
    const message = error instanceof Error ? error.stack ?? error.message : stringifyArgument(error);
    logUnhandledError("Uncaught exception", { message });
    process.exit(1);
  });

  process.on("unhandledRejection", (reason: unknown) => {
    const message =
      reason instanceof Error ? reason.stack ?? reason.message : stringifyArgument(reason ?? "unknown");
    logUnhandledError("Unhandled promise rejection", { message });
  });

  process.on("exit", () => {
    stream?.end();
  });

  patched = true;
};
