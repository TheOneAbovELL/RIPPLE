"use client";

import { useId, useState } from "react";

import type { FeedbackKind } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { toError } from "@/lib/useRequest";

import type { FeedbackOption } from "./feedback";

interface Outcome {
  label: string;
  created: boolean;
}

/** Buttons that send POST /feedback about one memory (ADR-0105). `recorded` is what
 * GET /feedback already holds; a statement made here is added to it locally, since the
 * API never takes one back. A failed request changes nothing and says why. */
export function FeedbackControls({
  targetMemoryId,
  options,
  prompt,
  recorded,
}: {
  targetMemoryId: string;
  options: readonly FeedbackOption[];
  /** The visible question the buttons answer; it also names the button group. */
  prompt: string;
  recorded: ReadonlySet<FeedbackKind>;
}) {
  const api = useApi();
  const promptId = useId();
  const captionId = useId();
  const [statedHere, setStatedHere] = useState<ReadonlySet<FeedbackKind>>(new Set());
  const [busy, setBusy] = useState(false);
  const [outcome, setOutcome] = useState<Outcome | null>(null);
  const [error, setError] = useState<Error | null>(null);

  async function state(option: FeedbackOption) {
    setBusy(true);
    setError(null);
    setOutcome(null);
    try {
      const receipt = await api.recordFeedback({
        target_memory_id: targetMemoryId,
        kind: option.kind,
      });
      setStatedHere((previous) => new Set(previous).add(receipt.feedback.kind));
      setOutcome({ label: option.label, created: receipt.created });
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  const held = options.filter(
    (option) => recorded.has(option.kind) || statedHere.has(option.kind),
  );

  return (
    <div className="feedback" role="group" aria-labelledby={promptId}>
      <p className="meta" id={promptId}>
        {prompt}
      </p>
      {/* The buttons sit together; a note that explains one of them goes on its own line
          under the whole row, so it never pushes the next button away. */}
      <div className="actions feedback-options">
        {options.map((option) => (
          <button
            key={option.kind}
            type="button"
            className="quiet"
            disabled={busy}
            aria-describedby={option.caption ? `${captionId}-${option.kind}` : undefined}
            onClick={() => state(option)}
          >
            {option.label}
          </button>
        ))}
      </div>
      {options
        .filter((option) => option.caption)
        .map((option) => (
          <p
            className="meta feedback-caption"
            id={`${captionId}-${option.kind}`}
            key={option.kind}
          >
            {option.label}: {option.caption}
          </p>
        ))}
      {held.length > 0 ? (
        <p className="meta">Recorded: {held.map((option) => option.label).join(", ")}.</p>
      ) : null}
      {outcome ? (
        <p className="meta" role="status">
          {outcome.created ? "Noted" : "Already recorded"}: {outcome.label}.
        </p>
      ) : null}
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
    </div>
  );
}
