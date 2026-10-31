import { render } from "@testing-library/react";
import type { ReactElement } from "react";
import { vi } from "vitest";

import type { RippleApi } from "@/api/client";
import type {
  ChangeEvent,
  Decision,
  Feedback,
  IntakeOut,
  OpeningOut,
  ResumeCandidate,
  VocabularyOut,
  Memory,
  MemoryDetailOut,
  MemoryOut,
  MemoryStatus,
  ParentOut,
  QuestionOut,
  RecommendationOut,
} from "@/api/types";
import { SessionProvider, useSession } from "@/auth/SessionProvider";
import { TOKEN_KEY } from "@/auth/token";

/** The router stub vitest.setup.ts installs in place of next/navigation. */
export const router = {
  push: vi.fn(),
  replace: vi.fn(),
  back: vi.fn(),
  forward: vi.fn(),
  refresh: vi.fn(),
  prefetch: vi.fn(),
};
export const navigation = { pathname: "/memories/", search: "" };

/** A RippleApi where every method rejects until a test sets it. Keeps tests honest:
 * a page that calls an endpoint the test did not expect fails loudly. */
export function fakeApi(overrides: Partial<RippleApi> = {}): RippleApi {
  const unexpected = (name: string) =>
    vi.fn(() => Promise.reject(new Error(`unexpected call to ${name}`)));
  return {
    me: unexpected("me"),
    listMemories: unexpected("listMemories"),
    getMemory: unexpected("getMemory"),
    editMemory: unexpected("editMemory"),
    forgetMemory: unexpected("forgetMemory"),
    getGraph: unexpected("getGraph"),
    getVocabulary: unexpected("getVocabulary"),
    listQuestions: unexpected("listQuestions"),
    answerQuestion: unexpected("answerQuestion"),
    listRecommendations: unexpected("listRecommendations"),
    exportMe: unexpected("exportMe"),
    deleteMe: unexpected("deleteMe"),
    recordFeedback: unexpected("recordFeedback"),
    listFeedback: unexpected("listFeedback"),
    createTelegramLink: unexpected("createTelegramLink"),
    postStatement: unexpected("postStatement"),
    postOpening: unexpected("postOpening"),
    uploadResume: unexpected("uploadResume"),
    listCandidates: unexpected("listCandidates"),
    confirmCandidate: unexpected("confirmCandidate"),
    rejectCandidate: unexpected("rejectCandidate"),
    listEvents: unexpected("listEvents"),
    ...overrides,
  };
}

/** A promise the test resolves by hand, to hold a page in its loading state. */
export function deferred<T>() {
  let resolve!: (value: T) => void;
  let reject!: (error: Error) => void;
  const promise = new Promise<T>((res, rej) => {
    resolve = res;
    reject = rej;
  });
  return { promise, resolve, reject };
}

/** Mirrors Shell's gate: a page only renders once the token has been read, so tests
 * of a view see the same first render a signed-in user would. */
function SignedIn({ children }: { children: ReactElement }) {
  const { ready, api } = useSession();
  if (!ready || !api) return null;
  return children;
}

export function renderSignedIn(ui: ReactElement, api: RippleApi) {
  window.sessionStorage.setItem(TOKEN_KEY, "test-token");
  return render(
    <SessionProvider buildClient={() => api}>
      <SignedIn>{ui}</SignedIn>
    </SessionProvider>,
  );
}

export function renderSignedOut(ui: ReactElement, api: RippleApi) {
  return render(<SessionProvider buildClient={() => api}>{ui}</SessionProvider>);
}

// ---- builders ---------------------------------------------------------------------------

let counter = 0;
const nextId = (prefix: string) => `${prefix}-${++counter}`;

export function memory(overrides: Partial<Memory> = {}): Memory {
  return {
    id: nextId("mem"),
    user_id: "user-1",
    domain: "jobs",
    kind: "fact",
    content: "I know Python",
    status: "VALID",
    version: 1,
    confidence: 1,
    recorded_at: "2026-10-20T09:00:00Z",
    valid_from: "2026-10-20T09:00:00Z",
    valid_to: null,
    created_by: "user",
    source_ref: null,
    supersedes_id: null,
    structured: null,
    sensitivity: "low",
    ...overrides,
  };
}

export function listed(overrides: Partial<Memory> = {}, flagged = false): MemoryOut {
  const m = memory(overrides);
  return { memory: m, flagged };
}

export function parent(
  parentMemory: Memory,
  overrides: Partial<Omit<ParentOut, "parent">> = {},
): ParentOut {
  return {
    link_id: nextId("link"),
    link_type: "eligibility_of",
    link_class: "depends_on",
    created_by: "rule",
    confidence: 0.9,
    parent: parentMemory,
    ...overrides,
  };
}

export function changeEvent(overrides: Partial<ChangeEvent> = {}): ChangeEvent {
  return {
    id: nextId("evt"),
    user_id: "user-1",
    trigger_kind: "ripple",
    trigger_memory_id: "mem-trigger",
    created_at: "2026-10-21T10:00:00Z",
    completed_at: "2026-10-21T10:00:01Z",
    affected_ids: [],
    decisions: [],
    parked: {},
    latency_ms: 10,
    cost_usd: 0,
    trace_id: null,
    ...overrides,
  };
}

export function detail(
  memoryOverrides: Partial<Memory> = {},
  extra: Partial<Omit<MemoryDetailOut, "memory">> = {},
): MemoryDetailOut {
  const m = memory(memoryOverrides);
  return {
    memory: m,
    flagged: false,
    why: [],
    history: { versions: [m], events: [] },
    ...extra,
  };
}

export function question(overrides: Partial<QuestionOut> = {}): QuestionOut {
  return {
    memory: memory({ status: "PENDING_USER", content: "CGPA is 8.2" }),
    question: "Is your CGPA still 8.2?",
    reason: "A newer transcript was recorded.",
    asked_at: "2026-10-22T08:00:00Z",
    event_id: nextId("evt"),
    ...overrides,
  };
}

export function recommendation(overrides: Partial<RecommendationOut> = {}): RecommendationOut {
  return {
    opening_memory_id: nextId("opening"),
    title: "SDE intern",
    company: "Acme",
    eligible: true,
    fit_score: 0.8,
    fit_reasons: ["Knows Python", "Batch 2028 matches"],
    deadline: "2026-11-01T18:30:00Z",
    flagged: false,
    ...overrides,
  };
}

export function feedbackRow(overrides: Partial<Feedback> = {}): Feedback {
  return {
    id: nextId("fb"),
    user_id: "user-1",
    target_memory_id: "opening-1",
    kind: "saved",
    note: null,
    created_at: "2026-10-30T09:00:00Z",
    ...overrides,
  };
}

export const ALL_STATUSES: readonly MemoryStatus[] = [
  "VALID",
  "SUSPECT",
  "PENDING_USER",
  "RETIRED",
];

export function decision(overrides: Partial<Decision> = {}): Decision {
  return {
    memory_id: nextId("mem"),
    wave: 1,
    action: "keep",
    reason: "recomputed from current parents; unchanged",
    evidence_refs: [],
    new_version_id: null,
    question: null,
    ...overrides,
  };
}

export function intake(overrides: Partial<IntakeOut> = {}): IntakeOut {
  return {
    memory: memory({ content: "CGPA is 8.6", version: 2, supersedes_id: "mem-old" }),
    change_kind: "update",
    links_written: 0,
    event: changeEvent(),
    ...overrides,
  };
}

export function candidate(overrides: Partial<ResumeCandidate> = {}): ResumeCandidate {
  return {
    id: nextId("cand"),
    user_id: "user-1",
    upload_id: "upload-1",
    attribute: "skill",
    value: "Python",
    span_start: 10,
    span_end: 16,
    span_text: "Skills: Python, SQL",
    confidence: 0.9,
    content: "Knows Python",
    status: "pending",
    created_at: "2026-10-31T09:00:00Z",
    decided_at: null,
    memory_id: null,
    ...overrides,
  };
}

export function openingOut(overrides: Partial<OpeningOut> = {}): OpeningOut {
  return {
    opening_memory_id: "opening-1",
    memory_ids: ["opening-1", "field-1", "belief-1"],
    event_id: "evt-opening",
    source_ref: "paste:1",
    summary: "SDE intern at Acme",
    fields: [
      {
        attribute: "cgpa_cutoff",
        value: 7.5,
        span_start: 40,
        span_end: 60,
        span_text: "CGPA of 7.5 and above",
        confidence: 0.95,
      },
    ],
    ...overrides,
  };
}

export function vocabulary(overrides: Partial<VocabularyOut> = {}): VocabularyOut {
  return {
    domain: "jobs",
    kinds: ["fact", "derived", "opening"],
    attributes: [],
    link_types: [],
    profile_subject: "student",
    profile_attributes: [],
    ...overrides,
  };
}
