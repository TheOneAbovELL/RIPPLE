"use client";

import Link from "next/link";
import { useId, useState } from "react";

import type { AnswerIn, AnswerOut, FeedbackKind, QuestionOut } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { KindChip, StatusChip, statusLabel } from "@/components/StatusChip";
import { FeedbackControls } from "@/features/feedback/FeedbackControls";
import { QUESTION_OPTIONS } from "@/features/feedback/feedback";
import { detailHref } from "@/features/memories/MemoryCard";
import { formatDateTime, fromDateTimeLocal } from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";

interface Receipt {
  question: string;
  /** The memory the resolver asked about: the target of the question feedback. */
  askedMemoryId: string;
  result: AnswerOut;
}

/** Nothing was said about a question that was just answered on this page. */
const NOTHING_RECORDED: ReadonlySet<FeedbackKind> = new Set();

/** Pending questions (FR-7) with the three answers the API accepts: still holds,
 * no longer holds, correction (ADR-0013 step 4). Receipts live above the list because
 * an answered question leaves the list on reload, taking its card with it; each receipt
 * asks whether the question was worth asking (pilot feedback, ADR-0105). */
export function QuestionsView() {
  const api = useApi();
  const request = useRequest(() => api.listQuestions());
  const [receipts, setReceipts] = useState<Receipt[]>([]);

  function answered(question: QuestionOut, result: AnswerOut) {
    setReceipts((previous) => [
      { question: question.question, askedMemoryId: question.memory.id, result },
      ...previous,
    ]);
    request.reload();
  }

  return (
    <>
      {receipts.length > 0 ? (
        <ul className="card-list" aria-label="Answers recorded">
          {receipts.map((receipt) => (
            <li className="notice" key={receipt.result.event.id}>
              <p className="content" role="status">
                Answer recorded for “{receipt.question}”. The memory is now{" "}
                {statusLabel(receipt.result.status).toLowerCase()}.
              </p>
              <FeedbackControls
                targetMemoryId={receipt.askedMemoryId}
                options={QUESTION_OPTIONS}
                prompt="Was this question useful?"
                recorded={NOTHING_RECORDED}
              />
            </li>
          ))}
        </ul>
      ) : null}
      <RequestView request={request} what="questions">
        {(data) =>
          data.questions.length === 0 ? (
            <Empty>Nothing to answer. Ripple will ask here when a belief needs you.</Empty>
          ) : (
            <ul className="card-list" aria-label="Questions">
              {data.questions.map((question) => (
                <QuestionCard
                  key={question.event_id}
                  question={question}
                  onAnswered={(result) => answered(question, result)}
                />
              ))}
            </ul>
          )
        }
      </RequestView>
    </>
  );
}

function QuestionCard({
  question,
  onAnswered,
}: {
  question: QuestionOut;
  onAnswered(result: AnswerOut): void;
}) {
  const api = useApi();
  const ids = { content: useId(), validTo: useId() };
  const memoryId = question.memory.id;
  const [correcting, setCorrecting] = useState(false);
  const [content, setContent] = useState(question.memory.content);
  const [validTo, setValidTo] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function answer(body: AnswerIn) {
    setBusy(true);
    setError(null);
    try {
      const result = await api.answerQuestion(memoryId, body);
      onAnswered(result);
    } catch (caught) {
      setError(toError(caught));
      setBusy(false);
    }
  }

  function submitCorrection(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    answer({
      answer: "correction",
      content: content.trim(),
      valid_to: validTo ? fromDateTimeLocal(validTo) : null,
    });
  }

  return (
    <li className="card" data-memory-id={memoryId}>
      <div className="card-head">
        <StatusChip status={question.memory.status} />
        <KindChip kind={question.memory.kind} />
        <span className="meta">asked {formatDateTime(question.asked_at)}</span>
      </div>
      <p className="content">
        <strong>{question.question}</strong>
      </p>
      <p className="meta">
        About: <Link href={detailHref(memoryId)}>{question.memory.content}</Link>
      </p>
      <p className="meta">Why Ripple asks: {question.reason}</p>
      <div className="actions" role="group" aria-label="Answer">
        <button type="button" disabled={busy} onClick={() => answer({ answer: "still_holds" })}>
          Still holds
        </button>
        <button
          type="button"
          disabled={busy}
          onClick={() => answer({ answer: "no_longer_holds" })}
        >
          No longer holds
        </button>
        <button
          type="button"
          className="quiet"
          disabled={busy}
          aria-expanded={correcting}
          onClick={() => setCorrecting((open) => !open)}
        >
          {correcting ? "Cancel correction" : "Correct it"}
        </button>
      </div>
      {correcting ? (
        <form onSubmit={submitCorrection} aria-label="Correction">
          <div className="field">
            <label htmlFor={ids.content}>Corrected content</label>
            <textarea
              id={ids.content}
              value={content}
              required
              maxLength={4000}
              onChange={(event) => setContent(event.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor={ids.validTo}>Valid until (optional)</label>
            <input
              id={ids.validTo}
              type="datetime-local"
              value={validTo}
              onChange={(event) => setValidTo(event.target.value)}
            />
          </div>
          <button type="submit" disabled={busy || content.trim().length === 0}>
            {busy ? "Saving…" : "Save correction"}
          </button>
        </form>
      ) : null}
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
    </li>
  );
}
