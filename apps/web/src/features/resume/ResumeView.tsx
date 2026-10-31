"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { ApiError } from "@/api/client";
import type { ConfirmOut, ResumeCandidate } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { ActionError } from "@/components/ActionError";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { attributeLabel } from "@/features/domain/vocabulary";
import { detailHref } from "@/features/memories/MemoryCard";
import { IntakeResult } from "@/features/tell/TellView";
import { formatDateTime, formatPercent } from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";

/** The generated schema marks `id` optional (it has a default on the server); the API
 * always sends it, and a row without one could not be decided, so it is not listed. */
type Decidable = ResumeCandidate & { id: string };
const hasId = (candidate: ResumeCandidate): candidate is Decidable =>
  typeof candidate.id === "string";

/** Resume upload and review (FR-1, I5; ADR-0131 point 3). What the parser found is a
 * list of candidates, not beliefs: each one is stored only when the student confirms
 * it, and the page says so above the list. */
export function ResumeView() {
  const api = useApi();
  // One "all" request feeds both lists, so a decision moves a row in one reload.
  const candidates = useRequest(() => api.listCandidates("all"));
  const [confirmed, setConfirmed] = useState<ConfirmOut | null>(null);

  return (
    <>
      <UploadForm onUploaded={candidates.reload} />
      <RequestView request={candidates} what="your resume candidates">
        {(data) => {
          const listed = data.candidates.filter(hasId);
          const pending = listed.filter((c) => c.status === "pending");
          const decided = listed.filter((c) => c.status !== "pending");
          return (
            <>
              <section aria-labelledby="review-heading">
                <h2 id="review-heading">Review what Ripple found</h2>
                <div className="notice" role="note">
                  <p>
                    <strong>Not saved yet.</strong> Nothing from your resume becomes a belief
                    until you confirm it. Rejected items are kept only as a record of what you
                    declined.
                  </p>
                </div>
                {pending.length === 0 ? (
                  <Empty>
                    Nothing is waiting for review. Upload your resume above to start.
                  </Empty>
                ) : (
                  <ul className="card-list" aria-label="Waiting for your review">
                    {pending.map((candidate) => (
                      <PendingRow
                        key={candidate.id}
                        candidate={candidate}
                        onDecided={(outcome) => {
                          if (outcome) setConfirmed(outcome);
                          candidates.reload();
                        }}
                      />
                    ))}
                  </ul>
                )}
              </section>
              {confirmed ? (
                <IntakeResult
                  result={confirmed.intake}
                  title={`Saved: ${confirmed.candidate.content}`}
                  focusOnShow
                />
              ) : null}
              {decided.length > 0 ? (
                <section aria-labelledby="decided-heading">
                  <h2 id="decided-heading">Already decided</h2>
                  <ul className="card-list" aria-label="Already decided">
                    {decided.map((candidate) => (
                      <DecidedRow key={candidate.id} candidate={candidate} />
                    ))}
                  </ul>
                </section>
              ) : null}
            </>
          );
        }}
      </RequestView>
    </>
  );
}

function UploadForm({ onUploaded }: { onUploaded: () => void }) {
  const api = useApi();
  const inputId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [found, setFound] = useState<number | null>(null);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!file) {
      setError(new Error("Choose your resume as a PDF first."));
      return;
    }
    setBusy(true);
    setError(null);
    setFound(null);
    try {
      const uploaded = await api.uploadResume(file);
      setFound(uploaded.candidates.length);
      setFile(null);
      onUploaded();
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <form onSubmit={submit} noValidate aria-label="Upload your resume" className="panel">
      {/* Dropping is a pointer shortcut; the file input inside is the keyboard and
          screen-reader path, so the zone itself needs no role. */}
      {/* eslint-disable-next-line jsx-a11y/no-static-element-interactions */}
      <div
        className="dropzone"
        data-over={over}
        onDragOver={(event) => {
          event.preventDefault();
          setOver(true);
        }}
        onDragLeave={() => setOver(false)}
        onDrop={(event) => {
          event.preventDefault();
          setOver(false);
          setFile(event.dataTransfer.files[0] ?? null);
        }}
      >
        <label htmlFor={inputId}>Your resume (PDF)</label>
        <input
          id={inputId}
          type="file"
          accept="application/pdf,.pdf"
          onChange={(event) => setFile(event.target.files?.[0] ?? null)}
        />
        <p className="meta">
          {file ? `Ready: ${file.name}` : "Drop the file here or choose it."} The text is kept
          so every fact can point at the line it came from.
        </p>
      </div>
      {error ? (
        <ActionError
          error={error}
          needsModelFor="read your resume"
          aftermath="Nothing was stored."
        />
      ) : null}
      {found !== null ? (
        <p className="notice notice-ok" role="status">
          Ripple found {found} {found === 1 ? "fact" : "facts"} to review below. None is saved
          until you confirm it.
        </p>
      ) : null}
      <div className="actions">
        <button type="submit" disabled={busy}>
          {busy ? "Reading your resume…" : "Upload and read"}
        </button>
      </div>
    </form>
  );
}

function PendingRow({
  candidate,
  onDecided,
}: {
  candidate: Decidable;
  onDecided: (confirmed: ConfirmOut | null) => void;
}) {
  const api = useApi();
  const [busy, setBusy] = useState<"confirm" | "reject" | null>(null);
  const [error, setError] = useState<Error | null>(null);

  async function decide(action: "confirm" | "reject") {
    setBusy(action);
    setError(null);
    try {
      if (action === "confirm") onDecided(await api.confirmCandidate(candidate.id));
      else {
        await api.rejectCandidate(candidate.id);
        onDecided(null);
      }
    } catch (caught) {
      // 409: another tab or the bot decided first; reload so the row shows that outcome.
      if (caught instanceof ApiError && caught.status === 409) {
        onDecided(null);
        return;
      }
      setError(toError(caught));
      setBusy(null);
    }
  }

  return (
    <li className="card" data-candidate-id={candidate.id}>
      <div className="card-head">
        <span className="chip chip-status-pending_user">Not saved yet</span>
        <strong>{attributeLabel(candidate.attribute)}</strong>
        <span className="meta">read with {formatPercent(candidate.confidence)}</span>
      </div>
      <p className="content">{candidate.content}</p>
      <blockquote className="quote" aria-label="From your resume">
        {candidate.span_text}
      </blockquote>
      {error ? (
        <ActionError error={error} needsModelFor="link this fact to what it already knows" />
      ) : null}
      <div className="actions">
        <button
          type="button"
          onClick={() => void decide("confirm")}
          disabled={busy !== null}
          aria-label={`Confirm: ${candidate.content}`}
        >
          {busy === "confirm" ? "Saving…" : "Confirm"}
        </button>
        <button
          type="button"
          className="quiet"
          onClick={() => void decide("reject")}
          disabled={busy !== null}
          aria-label={`Reject: ${candidate.content}`}
        >
          {busy === "reject" ? "Rejecting…" : "Reject"}
        </button>
      </div>
    </li>
  );
}

function DecidedRow({ candidate }: { candidate: Decidable }) {
  const confirmed = candidate.status === "confirmed";
  return (
    <li className="card" data-candidate-id={candidate.id}>
      <div className="card-head">
        <span className={`chip ${confirmed ? "chip-verdict-yes" : "chip-verdict-no"}`}>
          {confirmed ? "Confirmed" : "Rejected"}
        </span>
        <strong>{attributeLabel(candidate.attribute)}</strong>
        <span className="meta">{formatDateTime(candidate.decided_at)}</span>
      </div>
      <p className="content">
        {confirmed && candidate.memory_id ? (
          <Link href={detailHref(candidate.memory_id)}>{candidate.content}</Link>
        ) : (
          candidate.content
        )}
      </p>
    </li>
  );
}
