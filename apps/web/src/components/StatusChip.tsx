import type { MemoryStatus } from "@/api/types";

/** Colour AND text for every state (.claude/rules/frontend.md). The label is what a
 * screen reader and a colour-blind reader get; the colour is a hint on top. */
const LABELS: Record<MemoryStatus, string> = {
  VALID: "Valid",
  SUSPECT: "Suspect",
  PENDING_USER: "Awaiting your answer",
  RETIRED: "Retired",
};

interface StatusChipProps {
  status: MemoryStatus;
}

export function StatusChip({ status }: StatusChipProps) {
  return (
    <span className={`chip chip-status-${status.toLowerCase()}`} data-status={status}>
      {LABELS[status]}
    </span>
  );
}

export function statusLabel(status: MemoryStatus): string {
  return LABELS[status];
}

/** The API's own I1 flag (SUSPECT or PENDING_USER): shown as text, never inferred here. */
export function FlaggedChip({ flagged }: { flagged: boolean }) {
  if (!flagged) return null;
  return <span className="chip chip-flagged">Flagged</span>;
}

export function KindChip({ kind }: { kind: string }) {
  return <span className={`chip chip-kind chip-kind-${kind}`}>{kind}</span>;
}
