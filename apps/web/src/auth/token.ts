/** The bearer token lives in sessionStorage only (ADR-0086): it dies with the tab, is
 * never sent as a cookie and never written to localStorage.
 *
 * The module is a tiny external store so React can read it with useSyncExternalStore:
 * the pre-rendered page knows no token (server snapshot null), the browser reads the
 * real one right after hydration, and login/logout notify every subscriber. */
export const TOKEN_KEY = "ripple.token";

type Listener = () => void;
const listeners = new Set<Listener>();

export function readToken(): string | null {
  try {
    return window.sessionStorage.getItem(TOKEN_KEY);
  } catch {
    return null;
  }
}

export function writeToken(token: string): void {
  window.sessionStorage.setItem(TOKEN_KEY, token);
  notify();
}

export function clearToken(): void {
  window.sessionStorage.removeItem(TOKEN_KEY);
  notify();
}

export function subscribeToken(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

function notify(): void {
  for (const listener of listeners) listener();
}
