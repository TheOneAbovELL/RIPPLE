import type { MemoryStatus } from "@/api/types";

/** I1 at the UI, in one place: the API never lists a RETIRED memory (ADR-0042), and
 * should one arrive anyway, no list, map or parents section shows it. The history
 * section of the detail page is the only view that shows retired versions, because
 * it asked for them with `history=true`. */
export function isVisibleInLists(status: MemoryStatus | undefined): boolean {
  return status !== "RETIRED";
}
