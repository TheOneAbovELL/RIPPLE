import Link from "next/link";

import type { Memory } from "@/api/types";
import { FlaggedChip, KindChip, StatusChip } from "@/components/StatusChip";
import { formatDateTime, structuredToText } from "@/lib/format";

interface MemoryCardProps {
  memory: Memory;
  flagged: boolean;
}

export function detailHref(memoryId: string): string {
  return `/memories/detail?id=${encodeURIComponent(memoryId)}`;
}

export function MemoryCard({ memory, flagged }: MemoryCardProps) {
  const structured = structuredToText(memory.structured);
  return (
    <li className="card" data-memory-id={memory.id}>
      <div className="card-head">
        <StatusChip status={memory.status} />
        <FlaggedChip flagged={flagged} />
        <KindChip kind={memory.kind} />
      </div>
      <p className="content">
        <Link href={detailHref(memory.id)}>{memory.content}</Link>
      </p>
      {structured ? <p className="meta">{structured}</p> : null}
      <p className="meta">
        Recorded {formatDateTime(memory.recorded_at)} · version {memory.version} · by{" "}
        {memory.created_by}
      </p>
    </li>
  );
}
