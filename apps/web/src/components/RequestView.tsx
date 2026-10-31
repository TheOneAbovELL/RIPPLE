"use client";

import type { ReactNode } from "react";

import type { Request } from "@/lib/useRequest";

import { ErrorBox, Loading } from "./LoadState";

interface RequestViewProps<T> {
  request: Request<T>;
  what: string;
  children(data: T): ReactNode;
}

/** Renders loading and error for a request and hands the data to the page. A 401 is
 * handled before it gets here: the session wrapper clears the token and Shell returns
 * to the login page. */
export function RequestView<T>({ request, what, children }: RequestViewProps<T>) {
  const { state } = request;
  if (state.status === "loading") return <Loading what={what} />;
  if (state.status === "error")
    return <ErrorBox error={state.error} onRetry={request.reload} />;
  return <div aria-busy={request.reloading || undefined}>{children(state.data)}</div>;
}
