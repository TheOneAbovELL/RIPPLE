"use client";

import Link from "next/link";
import type { ReactNode } from "react";

import type { RippleApi } from "@/api/client";
import type { ChangeEvent, RecommendationOut } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { VerdictChip } from "@/components/VerdictChip";
import { kindLabel } from "@/features/domain/vocabulary";
import { detailHref } from "@/features/memories/MemoryCard";
import { MemoryName, RippleTrace } from "@/features/ripple/RippleTrace";
import { TRIGGER_LABELS, actionCounts, countPhrase } from "@/features/ripple/labels";
import type { MemoryLabels } from "@/features/ripple/labels";
import { formatDateTime, formatRelative } from "@/lib/format";
import { useRequest } from "@/lib/useRequest";

const SHOWN = 5;

/** Home (ADR-0130 point 1): what needs you, what changed, what Ripple knows. Each block
 * loads on its own, so a slow export never hides the questions. */
export function HomeView() {
  return (
    <>
      <QuestionsBlock />
      <DeadlinesBlock />
      <RipplesBlock />
      <KnowsBlock />
      <StartBlock />
    </>
  );
}

function Block({
  id,
  title,
  hint,
  children,
}: {
  id: string;
  title: string;
  hint: string;
  children: ReactNode;
}) {
  return (
    <section className="block" aria-labelledby={id}>
      <div className="block-head">
        <h2 id={id}>{title}</h2>
        <p>{hint}</p>
      </div>
      <div>{children}</div>
    </section>
  );
}

function QuestionsBlock() {
  const api = useApi();
  const request = useRequest(() => api.listQuestions());
  return (
    <Block id="home-questions" title="Needs your answer" hint="Beliefs Ripple parked for you.">
      <RequestView request={request} what="your questions">
        {(data) =>
          data.questions.length === 0 ? (
            <Empty>
              No open questions. Ripple asks only when a change leaves a belief it cannot
              re-check on its own.
            </Empty>
          ) : (
            <>
              <p>
                <strong>
                  {data.questions.length}{" "}
                  {data.questions.length === 1 ? "question" : "questions"}
                </strong>{" "}
                waiting. Answering one lets Ripple finish the ripple it paused.
              </p>
              <ul className="card-list" aria-label="Open questions">
                {data.questions.slice(0, 3).map((question) => (
                  <li className="card" key={question.memory.id}>
                    <p className="content">{question.question}</p>
                    <p className="meta">
                      About: {question.memory.content} · asked{" "}
                      {formatDateTime(question.asked_at)}
                    </p>
                  </li>
                ))}
              </ul>
              <p className="actions">
                <Link className="button" href="/questions/">
                  Answer {data.questions.length === 1 ? "it" : "them"}
                </Link>
              </p>
            </>
          )
        }
      </RequestView>
    </Block>
  );
}

function DeadlinesBlock() {
  const api = useApi();
  const request = useRequest(() => upcoming(api));
  return (
    <Block
      id="home-deadlines"
      title="Deadlines"
      hint="Recommended openings with a recorded closing date, soonest first."
    >
      <RequestView request={request} what="your recommendations">
        {(items) =>
          items.length === 0 ? (
            <Empty>
              No deadlines recorded yet. <Link href="/openings/">Add an opening</Link> and its
              closing date shows up here.
            </Empty>
          ) : (
            <>
              <ol className="card-list" aria-label="Upcoming deadlines">
                {items.slice(0, SHOWN).map((item) => (
                  <li className="card" key={item.opening_memory_id}>
                    <div className="row-link">
                      <span className="content">
                        <Link href={detailHref(item.opening_memory_id)}>
                          <strong>{item.title}</strong> at {item.company}
                        </Link>
                      </span>
                      <span className="when">
                        {formatDateTime(item.deadline)} · {formatRelative(item.deadline)}
                      </span>
                    </div>
                    <div className="card-head">
                      <VerdictChip item={item} />
                    </div>
                  </li>
                ))}
              </ol>
              <p className="meta">
                <Link href="/recommendations/">All recommendations, with fit and reasons</Link>
              </p>
            </>
          )
        }
      </RequestView>
    </Block>
  );
}

/** The ranking's openings that carry a deadline, ordered by that date (display order
 * only; which openings rank, and how, is the API's). */
async function upcoming(api: RippleApi): Promise<RecommendationOut[]> {
  const { recommendations } = await api.listRecommendations(50);
  return recommendations
    .filter((item): item is RecommendationOut & { deadline: string } => item.deadline !== null)
    .sort((a, b) => Date.parse(a.deadline) - Date.parse(b.deadline));
}

interface RecentRipples {
  events: ChangeEvent[];
  labels: MemoryLabels;
  /** Every recorded event, rippled or not. */
  total: number;
}

/** The newest ChangeEvents that decided something, with the content and status of every
 * memory they name, from GET /events (ADR-0131 point 6). A write nothing depended on (a
 * first fact, a derived belief's own creation) is left out by `rippled_only`. */
async function recentRipples(api: RippleApi): Promise<RecentRipples> {
  const data = await api.listEvents({ limit: SHOWN, rippledOnly: true });
  return {
    events: data.events,
    labels: new Map(Object.entries(data.memories)),
    total: data.total,
  };
}

function RipplesBlock() {
  const api = useApi();
  const request = useRequest(() => recentRipples(api));
  return (
    <Block
      id="home-ripples"
      title="Recent ripples"
      hint="Each change, and what Ripple re-checked because of it."
    >
      <RequestView request={request} what="recent ripples">
        {({ events, labels, total }) =>
          events.length === 0 ? (
            <Empty>
              {total === 0
                ? "Nothing has changed yet."
                : "No change has reached another belief yet."}{" "}
              <Link href="/tell/">Tell Ripple something</Link> and the beliefs it touches appear
              here.
            </Empty>
          ) : (
            <ul className="card-list" aria-label="Recent ripples">
              {events.map((event) => (
                <li className="card" key={event.id}>
                  <div className="row-link">
                    <span className="content">
                      <strong>{TRIGGER_LABELS[event.trigger_kind]}:</strong>{" "}
                      <Link href={detailHref(event.trigger_memory_id)}>
                        <MemoryName
                          label={labels.get(event.trigger_memory_id) ?? { content: "a belief" }}
                        />
                      </Link>
                    </span>
                    <span className="when">{formatRelative(event.created_at)}</span>
                  </div>
                  <p className="meta">
                    {actionCounts(event)
                      .map(({ action, count }) => countPhrase(action, count))
                      .join(" · ")}
                  </p>
                  <details className="disclosure">
                    <summary>Show the waves</summary>
                    <RippleTrace event={event} labels={labels} title="The ripple" />
                  </details>
                </li>
              ))}
            </ul>
          )
        }
      </RequestView>
    </Block>
  );
}

interface Tally {
  total: number;
  flagged: number;
  byKind: [string, number][];
}

async function tally(api: RippleApi): Promise<Tally> {
  const { memories } = await api.listMemories();
  const byKind = new Map<string, number>();
  for (const { memory } of memories)
    byKind.set(memory.kind, (byKind.get(memory.kind) ?? 0) + 1);
  return {
    total: memories.length,
    flagged: memories.filter((item) => item.flagged).length,
    byKind: [...byKind.entries()],
  };
}

function KnowsBlock() {
  const api = useApi();
  const request = useRequest(() => tally(api));
  return (
    <Block
      id="home-knows"
      title="What Ripple knows"
      hint="Current beliefs; retired ones stay in each belief's history."
    >
      <RequestView request={request} what="your beliefs">
        {(data) =>
          data.total === 0 ? (
            <Empty>
              Ripple knows nothing about you yet. Start with your{" "}
              <Link href="/resume/">resume</Link> or <Link href="/tell/">one fact</Link>.
            </Empty>
          ) : (
            <>
              <ul className="tally" aria-label="Totals">
                <li>
                  <span className="figure">{data.total}</span>
                  <span className="what">current beliefs</span>
                </li>
                <li>
                  <span className="figure">{data.flagged}</span>
                  <span className="what">flagged (in doubt or awaiting you)</span>
                </li>
              </ul>
              <ul className="tally tally-kinds" aria-label="Beliefs by kind">
                {data.byKind.map(([kind, count]) => (
                  <li key={kind}>
                    <span className="figure">{count}</span>
                    <span className="what">{kindLabel(kind).toLowerCase()}</span>
                  </li>
                ))}
              </ul>
              <p className="meta">
                <Link href="/memories/">Browse every belief</Link> ·{" "}
                <Link href="/map/">See how they connect</Link>
              </p>
            </>
          )
        }
      </RequestView>
    </Block>
  );
}

function StartBlock() {
  const api = useApi();
  const me = useRequest(() => api.me());
  const linked = me.state.status === "data" ? me.state.data.telegram_linked : true;
  return (
    <Block id="home-start" title="Tell Ripple" hint="Anything new keeps its beliefs current.">
      <ul className="start-list">
        <li>
          <Link className="button" href="/tell/">
            Say what changed
          </Link>
        </li>
        <li>
          <Link className="button quiet" href="/openings/">
            Add an opening
          </Link>
        </li>
        <li>
          <Link className="button quiet" href="/resume/">
            Upload your resume
          </Link>
        </li>
        {linked ? null : (
          <li>
            <Link className="button quiet" href="/account/">
              Link Telegram
            </Link>
          </li>
        )}
      </ul>
    </Block>
  );
}
