"use client";

import { useEffect, useState } from "react";

import type { RippleApi } from "@/api/client";

import type { MemoryLabel, MemoryLabels } from "./labels";

/** Content for memory ids a ripple names, so a decision reads "eligible for SDE intern…"
 * rather than an id. One GET per id with history, because a decision may point at a
 * version that is now RETIRED (I1 hides those from lists, not from their history). A
 * failed lookup leaves that id unnamed; the trace still shows the decision. */
export function useMemoryLabels(api: RippleApi, ids: readonly string[]): MemoryLabels {
  const key = [...new Set(ids)].join("|");
  const [settled, setSettled] = useState<{ key: string; labels: MemoryLabels }>({
    key: "",
    labels: new Map(),
  });

  useEffect(() => {
    if (!key) return;
    let cancelled = false;
    const wanted = key.split("|");
    void Promise.allSettled(wanted.map((id) => api.getMemory(id, { history: true }))).then(
      (results) => {
        if (cancelled) return;
        const found = new Map<string, MemoryLabel>();
        results.forEach((result, index) => {
          const id = wanted[index];
          if (id !== undefined && result.status === "fulfilled") {
            const { content, status } = result.value.memory;
            found.set(id, { content, status });
          }
        });
        setSettled({ key, labels: found });
      },
    );
    return () => {
      cancelled = true;
    };
  }, [api, key]);

  return settled.key === key ? settled.labels : EMPTY;
}

const EMPTY: MemoryLabels = new Map();
