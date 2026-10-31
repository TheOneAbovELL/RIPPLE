import type { Feedback, FeedbackKind } from "@/api/types";

/** What a student can say about a recommended opening, and about a question the
 * resolver asked (ADR-0105). The API checks that a kind fits its target; this file
 * only names the buttons. */
export interface FeedbackOption {
  kind: FeedbackKind;
  label: string;
  /** Shown under the button and read as its description. */
  caption?: string;
}

export const RECOMMENDATION_OPTIONS: readonly FeedbackOption[] = [
  { kind: "saved", label: "Saved" },
  // I6: the agent never applies for the student; the button only records what they did.
  {
    kind: "applied",
    label: "Applied",
    caption: "Only tells Ripple. Nothing is submitted anywhere.",
  },
  { kind: "dismissed", label: "Not interested" },
];

export const QUESTION_OPTIONS: readonly FeedbackOption[] = [
  { kind: "question_useful", label: "Yes" },
  { kind: "question_not_useful", label: "No" },
];

const EMPTY: ReadonlySet<FeedbackKind> = new Set();

/** One GET /feedback for the whole page, indexed by target so each card looks up its
 * own kinds instead of asking the API once per card. */
export function kindsByTarget(rows: readonly Feedback[]): Map<string, Set<FeedbackKind>> {
  const byTarget = new Map<string, Set<FeedbackKind>>();
  for (const row of rows) {
    const kinds = byTarget.get(row.target_memory_id) ?? new Set<FeedbackKind>();
    kinds.add(row.kind);
    byTarget.set(row.target_memory_id, kinds);
  }
  return byTarget;
}

export function kindsFor(
  byTarget: ReadonlyMap<string, ReadonlySet<FeedbackKind>> | null,
  targetMemoryId: string,
): ReadonlySet<FeedbackKind> {
  return byTarget?.get(targetMemoryId) ?? EMPTY;
}
