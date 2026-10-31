import type { ReactNode } from "react";

export function Loading({ what }: { what: string }) {
  return (
    <p className="state state-loading" role="status" aria-live="polite">
      Loading {what}…
    </p>
  );
}

interface ErrorBoxProps {
  error: Error;
  onRetry?: () => void;
}

export function ErrorBox({ error, onRetry }: ErrorBoxProps) {
  return (
    <div className="state state-error" role="alert">
      <p>{error.message}</p>
      {onRetry ? (
        <button type="button" onClick={onRetry}>
          Try again
        </button>
      ) : null}
    </div>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <p className="state state-empty" role="status">
      {children}
    </p>
  );
}
