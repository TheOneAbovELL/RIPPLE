"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useId, useState } from "react";

import type { ChangeEvent, EditIn, Memory, MemoryDetailOut, ParentOut } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { FlaggedChip, KindChip, StatusChip } from "@/components/StatusChip";
import {
  formatDateTime,
  formatPercent,
  fromDateTimeLocal,
  shortId,
  structuredToText,
  toDateTimeLocal,
} from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";
import { isVisibleInLists } from "@/lib/visibility";

import { detailHref } from "./MemoryCard";

interface MemoryDetailViewProps {
  memoryId: string;
}

/** One belief: content, structured fact, why it is held (parents), its history
 * (versions and the ChangeEvents that touched them), edit and forget (FR-12, ADR-0042). */
export function MemoryDetailView({ memoryId }: MemoryDetailViewProps) {
  const api = useApi();
  const request = useRequest(() => api.getMemory(memoryId, { history: true }), memoryId);

  return (
    <RequestView request={request} what="this memory">
      {(detail) => <MemoryDetail detail={detail} />}
    </RequestView>
  );
}

function MemoryDetail({ detail }: { detail: MemoryDetailOut }) {
  const { memory } = detail;
  const retired = memory.status === "RETIRED";
  return (
    <>
      <section className="card" aria-labelledby="memory-heading">
        <div className="card-head">
          <StatusChip status={memory.status} />
          <FlaggedChip flagged={detail.flagged} />
          <KindChip kind={memory.kind} />
        </div>
        <h2 className="content" id="memory-heading">
          {memory.content}
        </h2>
        <MemoryFacts memory={memory} source={detail.source ?? null} />
      </section>

      {retired ? (
        <p className="notice">
          This is a retired version, shown because you followed its history. It cannot be
          edited; the current version is listed under History.
        </p>
      ) : (
        <MemoryActions key={memory.id} memory={memory} />
      )}

      <h2>Why this is held</h2>
      <WhyList parents={detail.why} />

      <h2>History</h2>
      {detail.history ? (
        <HistoryView versions={detail.history.versions} events={detail.history.events} />
      ) : (
        <Empty>No history was returned for this memory.</Empty>
      )}
    </>
  );
}

function MemoryFacts({
  memory,
  source,
}: {
  memory: Memory;
  source: MemoryDetailOut["source"] | null;
}) {
  const structured = structuredToText(memory.structured);
  return (
    <dl className="facts">
      {structured ? (
        <>
          <dt>Structured</dt>
          <dd>{structured}</dd>
        </>
      ) : null}
      <dt>Domain</dt>
      <dd>{memory.domain}</dd>
      <dt>Version</dt>
      <dd>{memory.version}</dd>
      <dt>Confidence</dt>
      <dd>{formatPercent(memory.confidence)}</dd>
      <dt>Recorded</dt>
      <dd>{formatDateTime(memory.recorded_at)}</dd>
      <dt>Valid from</dt>
      <dd>{formatDateTime(memory.valid_from)}</dd>
      <dt>Valid to</dt>
      <dd>{memory.valid_to ? formatDateTime(memory.valid_to) : "Open-ended"}</dd>
      <dt>Created by</dt>
      <dd>{memory.created_by}</dd>
      <dt>Source</dt>
      <dd>{memory.source_ref ?? "—"}</dd>
      {source ? (
        <>
          <dt>From your resume</dt>
          <dd>
            {source.filename} (uploaded {formatDateTime(source.uploaded_at)})
            {source.quote ? (
              <>
                {" "}
                · <q>{source.quote}</q>
              </>
            ) : null}
            {source.line ? <span className="meta"> · line: {source.line}</span> : null}
          </dd>
        </>
      ) : null}
      {memory.supersedes_id ? (
        <>
          <dt>Supersedes</dt>
          <dd>
            <Link href={detailHref(memory.supersedes_id)}>version {memory.version - 1}</Link>
          </dd>
        </>
      ) : null}
      <dt>Id</dt>
      <dd>
        <code>{memory.id}</code>
      </dd>
    </dl>
  );
}

function WhyList({ parents }: { parents: ParentOut[] }) {
  // I1 at the UI: the API skips superseded parents on propagating links but may still
  // return a retired snapshot parent; a list never shows a retired memory.
  const visible = parents.filter((parent) => isVisibleInLists(parent.parent.status));
  if (visible.length === 0) {
    return <Empty>This belief rests on no other memory.</Empty>;
  }
  return (
    <ul className="card-list" aria-label="Parents">
      {visible.map((parent) => (
        <li className="card" key={parent.link_id}>
          <div className="card-head">
            <span className="chip chip-kind">{parent.link_type}</span>
            <span className="chip chip-kind">{parent.link_class}</span>
            <StatusChip status={parent.parent.status} />
          </div>
          <p className="content">
            <Link href={detailHref(parent.parent.id)}>{parent.parent.content}</Link>
          </p>
          <p className="meta">
            Link by {parent.created_by} · confidence {formatPercent(parent.confidence)}
          </p>
        </li>
      ))}
    </ul>
  );
}

function HistoryView({ versions, events }: { versions: Memory[]; events: ChangeEvent[] }) {
  return (
    <>
      <h3>Versions</h3>
      <ol className="timeline" aria-label="Versions">
        {versions.map((version) => (
          <li key={version.id}>
            <div className="card-head">
              <strong>Version {version.version}</strong>
              <StatusChip status={version.status} />
            </div>
            <Link href={detailHref(version.id)}>{version.content}</Link>
            <p className="meta">
              Recorded {formatDateTime(version.recorded_at)} · by {version.created_by}
            </p>
          </li>
        ))}
      </ol>
      <h3>Change events</h3>
      {events.length === 0 ? (
        <Empty>No change event has touched this memory yet.</Empty>
      ) : (
        <ol className="timeline" aria-label="Change events">
          {events.map((event) => (
            <li key={event.id}>
              <div className="card-head">
                <strong>{event.trigger_kind.replace("_", " ")}</strong>
                <span className="meta">{formatDateTime(event.created_at)}</span>
                {event.completed_at ? null : <span className="chip chip-flagged">open</span>}
              </div>
              <p className="meta">
                Triggered by memory <code>{shortId(event.trigger_memory_id)}</code>
                {event.affected_ids.length > 0
                  ? ` · ${event.affected_ids.length} affected`
                  : null}
              </p>
              {event.decisions.length > 0 ? (
                <ul aria-label="Decisions">
                  {event.decisions.map((decision, index) => (
                    <li key={`${event.id}-${index}`}>
                      <strong>{decision.action}</strong> (wave {decision.wave}):{" "}
                      {decision.reason}
                      {decision.question ? (
                        <>
                          {" "}
                          <em>Question: {decision.question}</em>
                        </>
                      ) : null}
                      {decision.evidence_refs.length > 0 ? (
                        <span className="meta">
                          {" "}
                          · evidence: {decision.evidence_refs.join(", ")}
                        </span>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : null}
            </li>
          ))}
        </ol>
      )}
    </>
  );
}

/** What the edit does to `valid_to`. EditIn tells the three apart: the field omitted
 * keeps the current end, null makes the belief open-ended, a timestamp sets the end. */
type ValidToChoice = "keep" | "set" | "clear";

function MemoryActions({ memory }: { memory: Memory }) {
  const api = useApi();
  const router = useRouter();
  const ids = { content: useId(), validTo: useId() };
  const [editing, setEditing] = useState(false);
  const [content, setContent] = useState(memory.content);
  const [validToChoice, setValidToChoice] = useState<ValidToChoice>("keep");
  // Pre-filled with the current end at minute precision (what datetime-local shows);
  // choosing "End at" without touching it therefore sends that minute, not the seconds.
  const [validTo, setValidTo] = useState(toDateTimeLocal(memory.valid_to));
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [confirmForget, setConfirmForget] = useState(false);
  const memoryId = memory.id;
  const pending = memory.status === "PENDING_USER";

  async function saveEdit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const body: EditIn = { content: content.trim() };
      if (validToChoice === "set") body.valid_to = fromDateTimeLocal(validTo);
      if (validToChoice === "clear") body.valid_to = null;
      const result = await api.editMemory(memoryId, body);
      // The edit is a new version with its own id (ADR-0015); following it remounts
      // the page, which fetches the new version.
      router.push(detailHref(result.memory.id));
    } catch (caught) {
      setError(toError(caught));
      setBusy(false);
    }
  }

  async function forget() {
    setBusy(true);
    setError(null);
    try {
      await api.forgetMemory(memoryId);
      setConfirmForget(false);
      router.push("/memories/");
    } catch (caught) {
      setError(toError(caught));
      setBusy(false);
    }
  }

  return (
    <section aria-label="Actions">
      {pending ? (
        <p className="notice">
          This memory has an open question. Editing is disabled until you{" "}
          <Link href="/questions/">answer it</Link>.
        </p>
      ) : null}
      <div className="actions">
        <button
          type="button"
          onClick={() => setEditing((open) => !open)}
          disabled={pending || busy}
        >
          {editing ? "Cancel edit" : "Edit"}
        </button>
        <button
          type="button"
          className="danger"
          onClick={() => setConfirmForget(true)}
          disabled={busy}
        >
          Forget…
        </button>
      </div>
      {editing ? (
        <form onSubmit={saveEdit} className="card" aria-label="Edit memory">
          <div className="field">
            <label htmlFor={ids.content}>Content</label>
            <textarea
              id={ids.content}
              value={content}
              required
              maxLength={4000}
              onChange={(event) => setContent(event.target.value)}
            />
          </div>
          <fieldset className="field">
            <legend>Valid to</legend>
            <p className="meta">
              Currently:{" "}
              {memory.valid_to ? formatDateTime(memory.valid_to) : "no end (open-ended)"}.
            </p>
            <label className="checkbox">
              <input
                type="radio"
                name={`${ids.validTo}-choice`}
                value="keep"
                checked={validToChoice === "keep"}
                onChange={() => setValidToChoice("keep")}
              />
              Keep the current end
            </label>
            <label className="checkbox">
              <input
                type="radio"
                name={`${ids.validTo}-choice`}
                value="set"
                checked={validToChoice === "set"}
                onChange={() => setValidToChoice("set")}
              />
              End at a date and time
            </label>
            <label htmlFor={ids.validTo}>End date and time</label>
            <input
              id={ids.validTo}
              type="datetime-local"
              value={validTo}
              disabled={validToChoice !== "set"}
              required={validToChoice === "set"}
              onChange={(event) => setValidTo(event.target.value)}
            />
            <label className="checkbox">
              <input
                type="radio"
                name={`${ids.validTo}-choice`}
                value="clear"
                checked={validToChoice === "clear"}
                onChange={() => setValidToChoice("clear")}
              />
              No end (holds until something changes it)
            </label>
          </fieldset>
          <p className="meta">Saving creates a new version by you and ripples to dependents.</p>
          <button
            type="submit"
            disabled={
              busy ||
              content.trim().length === 0 ||
              (validToChoice === "set" && validTo.length === 0)
            }
          >
            {busy ? "Saving…" : "Save as new version"}
          </button>
        </form>
      ) : null}
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
      <ConfirmDialog
        open={confirmForget}
        title="Forget this memory?"
        confirmLabel="Forget permanently"
        busy={busy}
        onConfirm={forget}
        onCancel={() => setConfirmForget(false)}
      >
        <p>
          Forgetting deletes every version of this memory and everything that depends on it.
          This cannot be undone; a deletion record with ids only is kept.
        </p>
      </ConfirmDialog>
    </section>
  );
}
