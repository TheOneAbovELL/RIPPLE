import Link from "next/link";

import type { ChangeEvent, Decision } from "@/api/types";
import { detailHref } from "@/features/memories/MemoryCard";
import { formatDateTime, shortId } from "@/lib/format";

import { ACTION_LABELS, TRIGGER_LABELS, actionCounts, countPhrase } from "./labels";
import type { MemoryLabel, MemoryLabels } from "./labels";

interface RippleTraceProps {
  event: ChangeEvent;
  /** Memory id → content, when the page has looked them up. */
  labels?: MemoryLabels;
  title?: string;
  /** Heading level inside the page; the trace sits under an h2 by default. */
  headingLevel?: 2 | 3;
}

/** One ChangeEvent as the waves it sent out: every decision the engine recorded, with its
 * action word and the resolver's reason, grouped by wave (I2 made visible). */
export function RippleTrace({ event, labels, title, headingLevel = 3 }: RippleTraceProps) {
  const Heading = headingLevel === 2 ? "h2" : "h3";
  const waves = groupByWave(event.decisions);
  const counts = actionCounts(event);
  const trigger = labels?.get(event.trigger_memory_id);
  const heading = title ?? TRIGGER_LABELS[event.trigger_kind];
  return (
    <section className="trace" aria-label={heading} data-event-id={event.id}>
      <div className="trace-head">
        <Heading>{heading}</Heading>
        <span className="when">{formatDateTime(event.created_at)}</span>
      </div>
      {trigger ? (
        <p className="meta">
          Started by:{" "}
          <Link href={detailHref(event.trigger_memory_id)}>
            <MemoryName label={trigger} />
          </Link>
        </p>
      ) : null}
      {event.decisions.length === 0 ? (
        <p>
          {event.completed_at
            ? "Nothing else depended on this, so no other belief had to change."
            : "This ripple has not finished yet; the nightly sweep will complete it."}
        </p>
      ) : (
        <>
          <ul className="trace-summary" aria-label="Summary">
            {counts.map(({ action, count }) => (
              <li key={action} className={`action action-${action}`}>
                {countPhrase(action, count)}
              </li>
            ))}
          </ul>
          <ol className="waves">
            {waves.map(([wave, decisions]) => (
              <li className="wave" key={wave}>
                <p className="wave-label">{wave === 0 ? "Your answer" : `Wave ${wave}`}</p>
                <ul className="decisions">
                  {decisions.map((decision, index) => (
                    <DecisionRow
                      key={`${decision.memory_id}-${index}`}
                      decision={decision}
                      before={labels?.get(decision.memory_id)}
                      after={
                        decision.new_version_id
                          ? labels?.get(decision.new_version_id)
                          : undefined
                      }
                    />
                  ))}
                </ul>
              </li>
            ))}
          </ol>
          {event.completed_at ? null : (
            <p className="notice notice-warn">
              This ripple stopped before its last wave; the nightly sweep resumes it.
            </p>
          )}
        </>
      )}
    </section>
  );
}

function DecisionRow({
  decision,
  before,
  after,
}: {
  decision: Decision;
  before: MemoryLabel | undefined;
  after: MemoryLabel | undefined;
}) {
  const target = decision.new_version_id ?? decision.memory_id;
  const name = after ?? before ?? { content: `belief ${shortId(decision.memory_id)}` };
  return (
    <li className="decision" data-action={decision.action}>
      <span className={`action action-${decision.action}`}>
        {ACTION_LABELS[decision.action]}
      </span>
      <div>
        <Link href={detailHref(target)}>
          <MemoryName label={name} />
        </Link>
        {after && before && after.content !== before.content ? (
          <p className="meta">
            Was: <MemoryName label={before} />
          </p>
        ) : null}
        <p className="reason">{decision.reason}</p>
        {decision.question ? (
          <p className="question">
            “{decision.question}” <Link href="/questions/">Answer it</Link>
          </p>
        ) : null}
      </div>
    </li>
  );
}

/** A memory's content; a RETIRED version is struck through and named as the past. */
export function MemoryName({ label }: { label: MemoryLabel }) {
  if (label.status !== "RETIRED") return <>{label.content}</>;
  return (
    <>
      <del>{label.content}</del> <span className="meta">(earlier version)</span>
    </>
  );
}

function groupByWave(decisions: readonly Decision[]): [number, Decision[]][] {
  const byWave = new Map<number, Decision[]>();
  for (const decision of decisions) {
    const list = byWave.get(decision.wave) ?? [];
    list.push(decision);
    byWave.set(decision.wave, list);
  }
  return [...byWave.entries()].sort(([a], [b]) => a - b);
}

/** Every memory id a trace may name: trigger, decided memories and new versions. */
export function idsInEvent(event: ChangeEvent): string[] {
  const ids = [event.trigger_memory_id];
  for (const decision of event.decisions) {
    ids.push(decision.memory_id);
    if (decision.new_version_id) ids.push(decision.new_version_id);
  }
  return ids;
}
