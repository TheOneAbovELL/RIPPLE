"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";

import type { RippleApi } from "@/api/client";
import type { IntakeOut, ProfileAttributeOut, StatementIn } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { ActionError } from "@/components/ActionError";
import { attributeLabel } from "@/features/domain/vocabulary";
import { detailHref } from "@/features/memories/MemoryCard";
import { RippleTrace, idsInEvent } from "@/features/ripple/RippleTrace";
import { useMemoryLabels } from "@/features/ripple/useMemoryLabels";
import { formatDateTime } from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";

type ValueType = ProfileAttributeOut["value_type"];

const VALUE_HELP: Record<ValueType, string> = {
  number: "A number, such as 8.6.",
  integer: "A whole number, such as 2028.",
  bool: "Yes or no.",
  text: "Text, as you would write it.",
};

/** "Tell Ripple" (FR-4, ADR-0131 point 5): a statement goes through Intake and the answer
 * carries the completed ripple, which the page draws wave by wave. The optional fact
 * section sends a structured fact; which facts, their value types and whether they are
 * permanent all come from GET /vocabulary (`profile_subject`, `profile_attributes`). */
export function TellView() {
  const api = useApi();
  const ids = { content: useId(), attribute: useId(), value: useId() };
  const choices = useRequest(() => loadFactChoices(api));

  const [content, setContent] = useState("");
  const [attribute, setAttribute] = useState("");
  const [value, setValue] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [result, setResult] = useState<IntakeOut | null>(null);
  const known = choices.state.status === "data" ? choices.state.data : null;
  const chosen = known?.facts.find((fact) => fact.attribute.name === attribute) ?? null;
  const valueType: ValueType = chosen?.attribute.value_type ?? "text";

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const text = content.trim();
    if (!text) {
      setError(new Error("Write what changed first."));
      return;
    }
    if (attribute && !value.trim()) {
      setError(new Error("Give the new value for the fact you picked, or clear the fact."));
      return;
    }
    const typed = attribute ? parseValue(value, valueType) : null;
    if (attribute && typed === null) {
      setError(new Error(`${attributeLabel(attribute)}: ${VALUE_HELP[valueType]}`));
      return;
    }
    const body: StatementIn = {
      content: text,
      kind: STATED,
      origin: "conversation",
      sensitivity: "low",
    };
    if (attribute && typed !== null && known?.subject) {
      body.structured = { subject: known.subject, attribute, value: typed };
    }
    setBusy(true);
    setError(null);
    try {
      setResult(await api.postStatement(body));
      setContent("");
      setAttribute("");
      setValue("");
      choices.reload(); // "(now: ...)" shows the new value
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  const held = known?.facts.filter((fact) => fact.held.length > 0) ?? [];
  const other = known?.facts.filter((fact) => fact.held.length === 0) ?? [];
  const noFacts = known !== null && known.facts.length === 0;

  return (
    <>
      <form onSubmit={submit} noValidate aria-label="Tell Ripple" className="panel">
        <div className="field">
          <label htmlFor={ids.content}>What changed?</label>
          <textarea
            id={ids.content}
            value={content}
            onChange={(event) => setContent(event.target.value)}
            aria-describedby={`${ids.content}-help`}
            placeholder="My CGPA is 8.6 after the sixth-semester results."
            maxLength={4000}
          />
          <p id={`${ids.content}-help`} className="meta">
            Say it the way you would tell a friend. Ripple records it, then re-checks every
            belief that depended on it.
          </p>
        </div>
        <details className="disclosure">
          <summary>This changes one profile fact (optional, more precise)</summary>
          <p className="meta">
            Naming the fact lets Ripple match it to what it already knows and re-check what
            depends on it by its rules, without the language model. Leave it empty for anything
            else.
          </p>
          <div className="field-row">
            <div className="field">
              <label htmlFor={ids.attribute}>Fact</label>
              <select
                id={ids.attribute}
                value={attribute}
                onChange={(event) => {
                  setAttribute(event.target.value);
                  setValue("");
                }}
                aria-describedby={`${ids.attribute}-help`}
                disabled={known === null || noFacts}
              >
                <option value="">None</option>
                {held.length > 0 ? (
                  <optgroup label="Facts Ripple holds about you">
                    {held.map((fact) => (
                      <option key={fact.attribute.name} value={fact.attribute.name}>
                        {attributeLabel(fact.attribute.name)} (now: {fact.held.join(", ")})
                      </option>
                    ))}
                  </optgroup>
                ) : null}
                {other.length > 0 ? (
                  <optgroup label="Other facts">
                    {other.map((fact) => (
                      <option key={fact.attribute.name} value={fact.attribute.name}>
                        {attributeLabel(fact.attribute.name)}
                      </option>
                    ))}
                  </optgroup>
                ) : null}
              </select>
              <p id={`${ids.attribute}-help`} className="meta">
                {choices.state.status === "error"
                  ? "The list of facts could not be loaded."
                  : noFacts
                    ? "This deployment publishes no profile facts to pick."
                    : chosen && !chosen.attribute.permanent
                      ? "Ripple may ask a model whether this is temporary."
                      : ""}
              </p>
            </div>
            <div className="field">
              <label htmlFor={ids.value}>New value</label>
              {valueType === "bool" ? (
                <select
                  id={ids.value}
                  value={value}
                  onChange={(event) => setValue(event.target.value)}
                  aria-describedby={`${ids.value}-help`}
                  disabled={!attribute}
                >
                  <option value="">Choose</option>
                  <option value="true">Yes</option>
                  <option value="false">No</option>
                </select>
              ) : (
                <input
                  id={ids.value}
                  value={value}
                  inputMode={
                    valueType === "number"
                      ? "decimal"
                      : valueType === "integer"
                        ? "numeric"
                        : "text"
                  }
                  onChange={(event) => setValue(event.target.value)}
                  aria-describedby={`${ids.value}-help`}
                  disabled={!attribute}
                />
              )}
              <p id={`${ids.value}-help`} className="meta">
                {attribute ? VALUE_HELP[valueType] : ""}
              </p>
            </div>
          </div>
        </details>
        {error ? (
          <ActionError
            error={error}
            needsModelFor="understand a free-text statement and link it"
          />
        ) : null}
        <button type="submit" disabled={busy}>
          {busy ? "Telling Ripple…" : "Tell Ripple"}
        </button>
      </form>
      {result ? <IntakeResult result={result} focusOnShow /> : <WhatHappens />}
    </>
  );
}

function WhatHappens() {
  return (
    <section aria-labelledby="what-happens">
      <h2 id="what-happens">What happens next</h2>
      <ol className="steps">
        <li>Ripple records the statement as a belief, or as a new version of one it held.</li>
        <li>
          Every belief that depended on it is re-checked, wave by wave: kept, updated, retired,
          or parked as a question for you.
        </li>
        <li>You see each decision here with its reason, and in the belief&apos;s history.</li>
      </ol>
    </section>
  );
}

const CHANGE_WORDS: Record<IntakeOut["change_kind"], string> = {
  new: "Recorded as a new belief.",
  update: "Recorded as a new version of a belief Ripple already held.",
  temporary: "Recorded as a temporary belief.",
  unchanged: "Ripple already knew exactly this, so nothing was written and nothing rippled.",
};

interface IntakeResultProps {
  result: IntakeOut;
  title?: string;
  /** Move focus to the heading: the control that had it may have just disappeared. */
  focusOnShow?: boolean;
}

export function IntakeResult({ result, title, focusOnShow = false }: IntakeResultProps) {
  const api = useApi();
  const heading = useRef<HTMLHeadingElement>(null);
  useEffect(() => {
    if (focusOnShow) heading.current?.focus();
  }, [focusOnShow, result]);
  const labels = useMemoryLabels(api, result.event ? idsInEvent(result.event) : []);
  const { memory } = result;
  return (
    <section aria-labelledby="intake-result" className="result">
      <h2 id="intake-result" ref={heading} tabIndex={-1}>
        {title ?? "What Ripple did"}
      </h2>
      <div className="notice notice-ok" role="status">
        <p>
          <strong>{CHANGE_WORDS[result.change_kind]}</strong>{" "}
          {result.links_written > 0
            ? `${result.links_written} new ${result.links_written === 1 ? "link" : "links"} to related beliefs.`
            : null}
        </p>
        <p>
          <Link href={detailHref(memory.id)}>{memory.content}</Link>
          {memory.valid_to ? ` (until ${formatDateTime(memory.valid_to)})` : null}
          {memory.version > 1 ? ` · version ${memory.version}` : null}
        </p>
      </div>
      {result.event ? (
        <RippleTrace event={result.event} labels={labels} title="The ripple" />
      ) : null}
    </section>
  );
}

/** StatementIn's own kind for something the student states (a derived belief about the
 * student, such as the search criteria, is Ripple's conclusion, not a fact to restate). */
const STATED: StatementIn["kind"] = "fact";

interface FactChoice {
  attribute: ProfileAttributeOut;
  /** Today's values, as stated; empty when Ripple holds none. */
  held: string[];
}

interface FactChoices {
  subject: string | null;
  facts: FactChoice[];
}

async function loadFactChoices(api: RippleApi): Promise<FactChoices> {
  const [memories, vocabulary] = await Promise.all([api.listMemories(), api.getVocabulary()]);
  const subject = vocabulary.profile_subject;
  const held = new Map<string, string[]>();
  for (const { memory } of memories.memories) {
    const fact = memory.structured;
    if (!fact || subject === null || fact.subject !== subject || memory.kind !== STATED)
      continue;
    held.set(fact.attribute, [...(held.get(fact.attribute) ?? []), String(fact.value)]);
  }
  return {
    subject,
    facts: vocabulary.profile_attributes
      .filter((attribute) => attribute.stated_by_user)
      .map((attribute) => ({ attribute, held: held.get(attribute.name) ?? [] })),
  };
}

/** The value as the API stores it, by the vocabulary's value type; null when the text
 * does not fit it ("eight" for a number, "8.5" for an integer). Text stays as typed. */
export function parseValue(raw: string, type: ValueType): string | number | boolean | null {
  const trimmed = raw.trim();
  switch (type) {
    case "text":
      return trimmed;
    case "number":
      return /^-?\d+(\.\d+)?$/.test(trimmed) ? Number(trimmed) : null;
    case "integer":
      return /^-?\d+$/.test(trimmed) ? Number(trimmed) : null;
    case "bool":
      return trimmed === "true" ? true : trimmed === "false" ? false : null;
  }
}
