/** Words for what the API records. Display only: every value comes from a ChangeEvent. */
import type { ChangeEvent, DecisionAction, MemoryStatus } from "@/api/types";

/** What a trace prints for a memory id: its content and, when known, its status, so
 * a version the event retired reads as the past (I1: shown only inside history). */
export interface MemoryLabel {
  content: string;
  status?: MemoryStatus;
}

export type MemoryLabels = ReadonlyMap<string, MemoryLabel>;

export const ACTION_LABELS: Record<DecisionAction, string> = {
  update: "Updated",
  keep: "Kept",
  retire: "Retired",
  ask: "Asked you",
};

export const ACTION_ORDER: readonly DecisionAction[] = ["update", "retire", "ask", "keep"];

export const TRIGGER_LABELS: Record<ChangeEvent["trigger_kind"], string> = {
  ripple: "Recorded",
  expiry: "Expired",
  user_edit: "You edited",
  user_answer: "You answered",
};

/** How many decisions of each action the event recorded, in a fixed reading order. */
export function actionCounts(event: ChangeEvent): { action: DecisionAction; count: number }[] {
  return ACTION_ORDER.map((action) => ({
    action,
    count: event.decisions.filter((decision) => decision.action === action).length,
  })).filter((entry) => entry.count > 0);
}

export function countPhrase(action: DecisionAction, count: number): string {
  const noun = count === 1 ? "belief" : "beliefs";
  const verb: Record<DecisionAction, string> = {
    update: "updated",
    keep: "kept",
    retire: "retired",
    ask: count === 1 ? "needs your answer" : "need your answer",
  };
  return `${count} ${noun} ${verb[action]}`;
}
