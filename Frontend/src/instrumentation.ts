import { setupServerLogger } from './lib/serverLogger';

export async function register(): Promise<void> {
  setupServerLogger();
}
