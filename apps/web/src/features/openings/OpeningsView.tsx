"use client";

import Link from "next/link";
import { useId, useState } from "react";

import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";
import type { OpeningIn, OpeningOut, RecommendationOut } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { ActionError } from "@/components/ActionError";
import { VerdictChip } from "@/components/VerdictChip";
import { ErrorBox, Loading } from "@/components/LoadState";
import { attributeLabel } from "@/features/domain/vocabulary";
import { detailHref } from "@/features/memories/MemoryCard";
import { useMemoryLabels } from "@/features/ripple/useMemoryLabels";
import { formatDateTime, formatPercent } from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";

type Source = OpeningIn["source"];

/** Add an opening (FR-2, ADR-0131 point 4): paste a JD or drop a text file. The answer
 * lists every recorded field with the words it came from; the verdict is the API's own
 * ranking entry for this opening, looked up by id. */
export function OpeningsView() {
  const api = useApi();
  const ids = { text: useId(), file: useId(), source: useId() };
  const [text, setText] = useState("");
  const [source, setSource] = useState<Source>("paste");
  const [over, setOver] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<OpeningOut | null>(null);

  async function readFile(file: File | undefined) {
    if (!file) return;
    if (file.type && !file.type.startsWith("text/") && file.type !== "message/rfc822") {
      setError(new Error("Drop a plain-text file (.txt or .eml), or paste the text instead."));
      return;
    }
    setError(null);
    setText(await file.text());
    if (file.name.toLowerCase().endsWith(".eml")) setSource("email");
  }

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!text.trim()) {
      setError(new Error("Paste the job description first."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await api.postOpening({ text, source }));
      setText("");
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <form onSubmit={submit} noValidate aria-label="Add an opening" className="panel">
        <div className="field">
          <label htmlFor={ids.text}>Job description or placement email</label>
          <textarea
            id={ids.text}
            value={text}
            onChange={(event) => setText(event.target.value)}
            rows={10}
            maxLength={50000}
            placeholder="Paste the whole description: title, company, CGPA cutoff, batch, skills, deadline."
          />
        </div>
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
            void readFile(event.dataTransfer.files[0]);
          }}
        >
          <label htmlFor={ids.file}>Or drop a .txt or .eml file here</label>
          <input
            id={ids.file}
            type="file"
            accept=".txt,.eml,text/plain,message/rfc822"
            onChange={(event) => void readFile(event.target.files?.[0])}
          />
        </div>
        <fieldset className="field">
          <legend>Where is it from?</legend>
          <label className="checkbox">
            <input
              type="radio"
              name={ids.source}
              checked={source === "paste"}
              onChange={() => setSource("paste")}
            />
            A job description I copied
          </label>
          <label className="checkbox">
            <input
              type="radio"
              name={ids.source}
              checked={source === "email"}
              onChange={() => setSource("email")}
            />
            A forwarded placement email (headers and signature are removed)
          </label>
        </fieldset>
        {error instanceof ApiError && error.errorName === "OpeningAlreadyRecordedError" ? (
          <p className="notice" role="alert">
            You already saved this opening.{" "}
            {existingAnchor(error) ? (
              <Link href={detailHref(existingAnchor(error) ?? "")}>Open it</Link>
            ) : null}
          </p>
        ) : error ? (
          <ActionError
            error={error}
            needsModelFor="read a job description"
            aftermath="Nothing was stored."
          />
        ) : null}
        <button type="submit" disabled={busy}>
          {busy ? "Reading the description…" : "Record this opening"}
        </button>
      </form>
      {result ? <OpeningResult result={result} /> : null}
    </>
  );
}

function OpeningResult({ result }: { result: OpeningOut }) {
  const api = useApi();
  const verdict = useRequest(
    () => findVerdict(api, result.opening_memory_id),
    result.opening_memory_id,
  );
  const beliefIds = result.memory_ids.filter((id) => id !== result.opening_memory_id);
  const labels = useMemoryLabels(api, beliefIds);
  return (
    <section aria-labelledby="opening-result">
      <h2 id="opening-result">Recorded: {result.summary}</h2>
      <p className="notice notice-ok" role="status">
        Ripple stored the opening with {result.fields.length}{" "}
        {result.fields.length === 1 ? "field" : "fields"} and re-checked your fit.{" "}
        <Link href={detailHref(result.opening_memory_id)}>Open the opening</Link>
      </p>

      <h3>Ripple&apos;s verdict</h3>
      {verdict.state.status === "loading" ? <Loading what="the verdict" /> : null}
      {verdict.state.status === "error" ? (
        <ErrorBox error={verdict.state.error} onRetry={verdict.reload} />
      ) : null}
      {verdict.state.status === "data" ? <Verdict item={verdict.state.data} /> : null}

      <h3>What it read, and where</h3>
      {result.fields.length === 0 ? (
        <p>No fields could be read from this text.</p>
      ) : (
        <ul className="card-list" aria-label="Recorded fields">
          {result.fields.map((field, index) => (
            <li className="card" key={`${field.attribute}-${index}`}>
              <div className="card-head">
                <strong>{attributeLabel(field.attribute)}</strong>
                <span className="chip chip-kind">
                  read with {formatPercent(field.confidence)}
                </span>
              </div>
              <p className="content">{String(field.value)}</p>
              <blockquote className="quote" aria-label="From the text">
                {field.span_text}
              </blockquote>
            </li>
          ))}
        </ul>
      )}

      {beliefIds.length > 0 ? (
        <>
          <h3>Beliefs recorded for it</h3>
          <ul>
            {beliefIds.map((id) => (
              <li key={id}>
                <Link href={detailHref(id)}>
                  {labels.get(id)?.content ?? "Open this belief"}
                </Link>
              </li>
            ))}
          </ul>
        </>
      ) : null}
    </section>
  );
}

function Verdict({ item }: { item: RecommendationOut | null }) {
  if (!item) {
    return (
      <p className="state state-empty" role="status">
        Ripple has no ranking for this opening yet. It ranks openings once it knows enough about
        your profile (for example your CGPA and batch) to judge them.
      </p>
    );
  }
  return (
    <div className="panel">
      <div className="card-head">
        <VerdictChip item={item} />
        <span className="chip chip-kind">fit {formatPercent(item.fit_score)}</span>
      </div>
      <p className="content">
        <strong>{item.title}</strong> at {item.company}
      </p>
      <p className="meta">
        Deadline: {item.deadline ? formatDateTime(item.deadline) : "none recorded"}
      </p>
      {item.fit_reasons.length > 0 ? (
        <ul aria-label="Fit reasons">
          {item.fit_reasons.map((reason, index) => (
            <li key={index}>{reason}</li>
          ))}
        </ul>
      ) : null}
    </div>
  );
}

/** The ranking entry the API computed for this opening, or null when it ranks none. */
async function findVerdict(
  api: RippleApi,
  openingId: string,
): Promise<RecommendationOut | null> {
  const { recommendations } = await api.listRecommendations(50);
  return recommendations.find((item) => item.opening_memory_id === openingId) ?? null;
}

/** The API names the opening already held in its 409 detail ("... recorded as 'ID'"). */
function existingAnchor(error: ApiError): string | null {
  const match =
    typeof error.detail === "string" ? /recorded as '([^']+)'/.exec(error.detail) : null;
  return match?.[1] ?? null;
}
