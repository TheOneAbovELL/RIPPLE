"use client";

import { useCallback, useEffect, useState } from "react";

import { ApiError } from "@/api/client";

/** The four states every page renders: loading, error, empty and data. "Empty" is the
 * page's call (an empty list); this hook only distinguishes the first three. */
export type RequestState<T> =
  { status: "loading" } | { status: "error"; error: Error } | { status: "data"; data: T };

export interface Request<T> {
  state: RequestState<T>;
  /** true while a reload() is in flight and the previous data is still shown. */
  reloading: boolean;
  reload(): void;
}

const LOADING = { status: "loading" } as const;

interface Settled<T> {
  key: string;
  attempt: number;
  state: RequestState<T>;
}

/** Runs `load` once per change of `key` (and once more per `reload()`), ignoring a
 * result that arrives after a newer request started. `key` names the request: the
 * filter values a page sends, or "" for a page that always asks the same question. The
 * client itself needs no key: it only changes with the token, which remounts the page.
 *
 * A changed key shows "loading" again; a reload() keeps the last data on screen (no
 * flash to a spinner after answering a question or pressing Try again) and reports
 * `reloading` instead. */
export function useRequest<T>(load: () => Promise<T>, key = ""): Request<T> {
  const [attempt, setAttempt] = useState(0);
  // The settled result remembers which request it answers, so a changed key shows
  // "loading" again without a setState inside the effect.
  const [settled, setSettled] = useState<Settled<T> | null>(null);

  useEffect(() => {
    let cancelled = false;
    load()
      .then((data) => {
        if (!cancelled) setSettled({ key, attempt, state: { status: "data", data } });
      })
      .catch((error: unknown) => {
        if (!cancelled)
          setSettled({ key, attempt, state: { status: "error", error: toError(error) } });
      });
    return () => {
      cancelled = true;
    };
    // `load` closes over the values `key` encodes; depending on its identity would
    // refetch on every render.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key, attempt]);

  const sameKey = settled !== null && settled.key === key;
  const current = sameKey && settled.attempt === attempt;
  const reloading = sameKey && !current && settled.state.status === "data";
  const state: RequestState<T> = current || reloading ? settled.state : LOADING;
  const reload = useCallback(() => setAttempt((n) => n + 1), []);
  return { state, reloading, reload };
}

export function toError(error: unknown): Error {
  if (error instanceof Error) return error;
  return new Error(String(error));
}

export function isUnauthorized(error: Error): boolean {
  return error instanceof ApiError && error.status === 401;
}
