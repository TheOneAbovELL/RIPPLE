"use client";

import { createContext, useCallback, useContext, useMemo, useSyncExternalStore } from "react";
import type { ReactNode } from "react";

import { API_BASE_URL } from "@/api/config";
import { createClient } from "@/api/client";
import type { RippleApi } from "@/api/client";
import type { MeOut } from "@/api/types";

import { withUnauthorizedLogout } from "./unauthorized";

import { clearToken, readToken, subscribeToken, writeToken } from "./token";

export interface Session {
  /** false while the pre-rendered page hydrates; true once the browser has read storage. */
  ready: boolean;
  /** A client bound to the stored token, or null when logged out. */
  api: RippleApi | null;
  /** Checks a token against GET /me and, when accepted, stores it for this tab. */
  login(token: string): Promise<MeOut>;
  /** Forgets the token: sessionStorage entry removed, client dropped. */
  logout(): void;
}

const SessionContext = createContext<Session | null>(null);

interface SessionProviderProps {
  children: ReactNode;
  /** Tests inject a fake client; the app builds one from the stored token. */
  buildClient?: (token: string) => RippleApi;
}

const noSubscription = () => () => {};

export function SessionProvider({ children, buildClient }: SessionProviderProps) {
  // Static export: the HTML is rendered without a token, so the server snapshot is
  // null and `ready` is false; both flip together in the first client render.
  const token = useSyncExternalStore(subscribeToken, readToken, () => null);
  const ready = useSyncExternalStore(
    noSubscription,
    () => true,
    () => false,
  );

  const build = useCallback(
    (raw: string) =>
      buildClient ? buildClient(raw) : createClient({ baseUrl: API_BASE_URL, token: raw }),
    [buildClient],
  );

  const login = useCallback(
    async (raw: string) => {
      const me = await build(raw).me();
      writeToken(raw);
      return me;
    },
    [build],
  );

  const logout = useCallback(() => {
    clearToken();
  }, []);

  // A 401 anywhere (list, edit, answer, delete) means the token stopped working:
  // clear it, and Shell returns the user to the login page (ADR-0086).
  const api = useMemo(
    () => (token ? withUnauthorizedLogout(build(token), clearToken) : null),
    [token, build],
  );

  const value = useMemo<Session>(
    () => ({ ready, api, login, logout }),
    [ready, api, login, logout],
  );
  return <SessionContext.Provider value={value}>{children}</SessionContext.Provider>;
}

export function useSession(): Session {
  const session = useContext(SessionContext);
  if (!session) throw new Error("useSession needs a SessionProvider above it");
  return session;
}

/** The client for a signed-in page. Shell only renders children once a token exists,
 * so a missing client here is a programming error, not a user state. */
export function useApi(): RippleApi {
  const { api } = useSession();
  if (!api) throw new Error("useApi called without a signed-in session");
  return api;
}
