"use client";

import { useEffect, useId, useRef, useState } from "react";
import type { ReactNode, SyntheticEvent } from "react";

interface ConfirmDialogProps {
  open: boolean;
  title: string;
  children: ReactNode;
  confirmLabel: string;
  /** When set, the user must type this exact phrase before the confirm button enables. */
  typedPhrase?: string;
  busy?: boolean;
  onConfirm(): void;
  onCancel(): void;
}

/** A native <dialog>: focus trap, Escape to close and backdrop come from the browser,
 * which keeps the component small and keyboard-navigable without a library. */
export function ConfirmDialog({
  open,
  title,
  children,
  confirmLabel,
  typedPhrase,
  busy = false,
  onConfirm,
  onCancel,
}: ConfirmDialogProps) {
  const ref = useRef<HTMLDialogElement>(null);
  const titleId = useId();
  const inputId = useId();
  const [typed, setTyped] = useState("");

  useEffect(() => {
    const dialog = ref.current;
    if (!dialog) return;
    if (open && !dialog.open) {
      setTyped("");
      // jsdom implements show() but not showModal(); production browsers have both.
      if (typeof dialog.showModal === "function") dialog.showModal();
      else dialog.show();
    } else if (!open && dialog.open) {
      dialog.close();
    }
  }, [open]);

  const armed = typedPhrase === undefined || typed === typedPhrase;

  // Escape must not close the dialog while the request it confirmed is still running.
  function cancel(event: SyntheticEvent<HTMLDialogElement>) {
    if (busy) {
      event.preventDefault();
      return;
    }
    onCancel();
  }

  return (
    <dialog ref={ref} className="dialog" aria-labelledby={titleId} onCancel={cancel}>
      <h2 id={titleId}>{title}</h2>
      <div className="dialog-body">{children}</div>
      {typedPhrase !== undefined ? (
        <p>
          <label htmlFor={inputId}>
            Type <code>{typedPhrase}</code> to confirm
          </label>
          <input
            id={inputId}
            type="text"
            value={typed}
            autoComplete="off"
            onChange={(event) => setTyped(event.target.value)}
          />
        </p>
      ) : null}
      <div className="dialog-actions">
        <button type="button" onClick={onCancel} disabled={busy}>
          Cancel
        </button>
        <button type="button" className="danger" onClick={onConfirm} disabled={!armed || busy}>
          {busy ? "Working…" : confirmLabel}
        </button>
      </div>
    </dialog>
  );
}
