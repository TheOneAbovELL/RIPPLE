"use client";

import Link from "next/link";
import { useSearchParams } from "next/navigation";
import { Suspense } from "react";

import { Loading } from "@/components/LoadState";
import { Shell } from "@/components/Shell";
import { MemoryDetailView } from "@/features/memories/MemoryDetailView";

/** A static export cannot pre-render one page per memory id, so the id travels as a
 * query parameter: /memories/detail/?id=<memory id> (ADR-0086). */
export default function MemoryDetailPage() {
  return (
    <Shell title="Belief">
      <Suspense fallback={<Loading what="this memory" />}>
        <DetailFromQuery />
      </Suspense>
    </Shell>
  );
}

function DetailFromQuery() {
  const params = useSearchParams();
  const id = params.get("id");
  if (!id) {
    return (
      <p className="notice">
        No memory was named. Pick one from the <Link href="/memories/">memories list</Link>.
      </p>
    );
  }
  return <MemoryDetailView memoryId={id} />;
}
