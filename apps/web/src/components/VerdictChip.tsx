import Link from "next/link";

import type { RecommendationOut } from "@/api/types";

interface VerdictChipProps {
  /** The API's verdict and its I1 flag, printed as given. */
  item: Pick<RecommendationOut, "eligible" | "flagged">;
}

/** Eligibility as the API judged it. A flagged verdict is one Ripple parked on a
 * question, so it reads "… · waiting on your answer" in amber with a way to answer,
 * rather than a green verdict beside a red flag that seems to contradict it. */
export function VerdictChip({ item }: VerdictChipProps) {
  const verdict = item.eligible ? "Eligible" : "Not eligible";
  if (!item.flagged) {
    return (
      <span className={`chip ${item.eligible ? "chip-verdict-yes" : "chip-verdict-no"}`}>
        {verdict}
      </span>
    );
  }
  return (
    <span className="verdict-waiting">
      <span className="chip chip-verdict-waiting">{verdict} · waiting on your answer</span>
      <Link href="/questions/">Answer</Link>
    </span>
  );
}
