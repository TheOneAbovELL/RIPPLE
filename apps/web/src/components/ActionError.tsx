import { ApiError } from "@/api/client";

/** A 503 from an endpoint that calls the language model (resume and JD parsing, change
 * detection, a ripple the rules cannot decide). The API maps every model failure to 503
 * (ADR-0098), and a server without a working model answers it every time, so the page
 * says so plainly instead of "try again shortly" (ADR-0131 point 7). */
export function isModelUnavailable(error: Error): boolean {
  return error instanceof ApiError && error.status === 503;
}

interface ActionErrorProps {
  error: Error;
  /** What the model was needed for, in the student's words ("read your resume"). */
  needsModelFor: string;
  /** What is true after the failure, e.g. "Nothing was stored." */
  aftermath?: string;
}

/** The error under a form: a model-specific message for a 503, the API's message otherwise. */
export function ActionError({ error, needsModelFor, aftermath }: ActionErrorProps) {
  // The write succeeded and only the re-check needs the model: say so, and that the
  // nightly sweep finishes the open ripple (the 503 body names its events).
  if (isModelUnavailable(error) && (error as ApiError).openChangeEventIds.length > 0) {
    return (
      <p className="notice notice-warn" role="alert">
        Saved. Ripple couldn&apos;t finish re-checking because the model is unavailable; it will
        finish automatically.
      </p>
    );
  }
  if (isModelUnavailable(error)) {
    return (
      <div className="notice notice-warn" role="alert">
        <p>
          <strong>Ripple needs its language model to {needsModelFor}</strong>, and the model is
          not answering on this server right now. On a local run this usually means
          ANTHROPIC_API_KEY is not set; the server log names the cause.
        </p>
        <p>
          {aftermath ? `${aftermath} ` : ""}Everything that does not need the model still works:
          your beliefs, questions, recommendations and the map.
        </p>
      </div>
    );
  }
  return (
    <p className="notice notice-error" role="alert">
      {error.message}
      {aftermath ? ` ${aftermath}` : ""}
    </p>
  );
}
