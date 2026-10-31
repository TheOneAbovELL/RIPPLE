"use client";

import { useId, useState } from "react";

import type { VisibleStatus } from "@/api/types";
import { useApi } from "@/auth/SessionProvider";
import { Empty } from "@/components/LoadState";
import { RequestView } from "@/components/RequestView";
import { statusLabel } from "@/components/StatusChip";
import { kindLabel, loadKinds } from "@/features/domain/vocabulary";
import { useRequest } from "@/lib/useRequest";
import { isVisibleInLists } from "@/lib/visibility";

import { MemoryCard } from "./MemoryCard";

const STATUSES: readonly VisibleStatus[] = ["VALID", "SUSPECT", "PENDING_USER"];

/** The memories list (FR-12). Filtering happens in the API: kind, status and the
 * flagged toggle are query parameters, so what is shown is exactly what GET /memories
 * returned, RETIRED rows never among them (I1 at the boundary, ADR-0042). */
export function MemoriesView() {
  const api = useApi();
  const ids = { kind: useId(), status: useId(), flagged: useId() };
  const [kind, setKind] = useState<string>("");
  const [status, setStatus] = useState<VisibleStatus | "">("");
  const [includeFlagged, setIncludeFlagged] = useState(true);
  // The kind choices are the domain's (GET /vocabulary). Until they arrive, or if they
  // never do, the filter offers "Any kind" only: the list itself still loads.
  const vocabulary = useRequest(() => loadKinds(api));
  const known = vocabulary.state.status === "data" ? vocabulary.state.data : null;
  const kinds = known?.kinds ?? [];
  const kindsUnavailable = known !== null && !known.fromApi;

  const request = useRequest(
    () =>
      api.listMemories({
        kind: kind || null,
        status: status || null,
        flagged: includeFlagged,
      }),
    `${kind}|${status}|${includeFlagged}`,
  );

  return (
    <>
      <form
        className="toolbar"
        aria-label="Filters"
        onSubmit={(event) => event.preventDefault()}
      >
        <div>
          <label htmlFor={ids.kind}>Kind</label>
          <select
            id={ids.kind}
            value={kind}
            disabled={kindsUnavailable}
            aria-describedby={kindsUnavailable ? `${ids.kind}-help` : undefined}
            onChange={(event) => setKind(event.target.value)}
          >
            <option value="">Any kind</option>
            {kinds.map((k) => (
              <option key={k} value={k}>
                {kindLabel(k)}
              </option>
            ))}
          </select>
          {kindsUnavailable ? (
            <p id={`${ids.kind}-help`} className="meta">
              Kind choices could not be loaded; showing every kind.
            </p>
          ) : null}
        </div>
        <div>
          <label htmlFor={ids.status}>Status</label>
          <select
            id={ids.status}
            value={status}
            onChange={(event) => setStatus(event.target.value as VisibleStatus | "")}
          >
            <option value="">Any status</option>
            {STATUSES.map((s) => (
              <option key={s} value={s}>
                {statusLabel(s)}
              </option>
            ))}
          </select>
        </div>
        <label className="checkbox" htmlFor={ids.flagged}>
          <input
            id={ids.flagged}
            type="checkbox"
            checked={includeFlagged}
            onChange={(event) => setIncludeFlagged(event.target.checked)}
          />
          Include flagged (suspect or awaiting an answer)
        </label>
      </form>
      <RequestView request={request} what="memories">
        {(data) => {
          const visible = data.memories.filter((item) => isVisibleInLists(item.memory.status));
          return visible.length === 0 ? (
            <Empty>No memories match these filters.</Empty>
          ) : (
            <ul className="card-list" aria-label="Memories">
              {visible.map((item) => (
                <MemoryCard key={item.memory.id} memory={item.memory} flagged={item.flagged} />
              ))}
            </ul>
          );
        }}
      </RequestView>
    </>
  );
}
