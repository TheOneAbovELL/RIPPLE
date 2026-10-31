"use client";

import Link from "next/link";

import type { FeedbackKind, RecommendationOut } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { VerdictChip } from "@/components/VerdictChip";
import { FeedbackControls } from "@/features/feedback/FeedbackControls";
import { RECOMMENDATION_OPTIONS, kindsByTarget, kindsFor } from "@/features/feedback/feedback";
import { detailHref } from "@/features/memories/MemoryCard";
import { formatDateTime, formatPercent } from "@/lib/format";
import { useRequest } from "@/lib/useRequest";

const LIMIT = 50;

/** Ranked openings from GET /recommendations. Eligibility, fit and the reasons are the
 * adapter's verdicts (WS-1 ranking); this page prints them and nothing else. Each card
 * also takes the student's pilot feedback (ADR-0105); what they said before comes from
 * one GET /feedback for the whole page. */
export function RecommendationsView() {
  const api = useApi();
  const request = useRequest(() => api.listRecommendations(LIMIT));
  const feedback = useRequest(() => api.listFeedback());
  const recorded =
    feedback.state.status === "data" ? kindsByTarget(feedback.state.data.feedback) : null;

  return (
    <RequestView request={request} what="recommendations">
      {(data) =>
        data.recommendations.length === 0 ? (
          <Empty>No recommendations yet. Paste a job description or wait for the Scout.</Empty>
        ) : (
          <>
            {feedback.state.status === "error" ? (
              <p className="notice notice-error" role="alert">
                Could not load the feedback you gave earlier ({feedback.state.error.message}).
                The buttons still work.
              </p>
            ) : null}
            <ol className="card-list" aria-label="Recommendations">
              {data.recommendations.map((item) => (
                <RecommendationCard
                  key={item.opening_memory_id}
                  item={item}
                  recorded={kindsFor(recorded, item.opening_memory_id)}
                />
              ))}
            </ol>
          </>
        )
      }
    </RequestView>
  );
}

function RecommendationCard({
  item,
  recorded,
}: {
  item: RecommendationOut;
  recorded: ReadonlySet<FeedbackKind>;
}) {
  return (
    <li className="card" data-opening-id={item.opening_memory_id}>
      <div className="card-head">
        <VerdictChip item={item} />
        <span className="chip chip-kind">fit {formatPercent(item.fit_score)}</span>
      </div>
      <p className="content">
        <Link href={detailHref(item.opening_memory_id)}>
          <strong>{item.title}</strong> at {item.company}
        </Link>
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
      <FeedbackControls
        targetMemoryId={item.opening_memory_id}
        options={RECOMMENDATION_OPTIONS}
        prompt={`What did you do with ${item.title} at ${item.company}?`}
        recorded={recorded}
      />
    </li>
  );
}
