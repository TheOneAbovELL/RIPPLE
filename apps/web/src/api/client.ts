/** Thin fetch wrapper over the Ripple API (ADR-0085).
 *
 * The request and response shapes come from src/api/schema.d.ts, generated from
 * openapi.json by openapi-typescript. This file only knows how to send a bearer token,
 * encode a query string and turn a non-2xx response into an ApiError. It computes
 * nothing about memories: the API decides, the dashboard renders.
 */
import type {
  AnswerIn,
  AnswerOut,
  CandidateFilter,
  CandidateOut,
  CandidatesOut,
  ConfirmOut,
  EditIn,
  EventsOut,
  ExportOut,
  Feedback,
  FeedbackIn,
  FeedbackListOut,
  ForgetOut,
  GraphOut,
  IntakeOut,
  LinkCodeOut,
  ListMemoriesQuery,
  MemoriesOut,
  MemoryDetailOut,
  MeOut,
  OpeningIn,
  OpeningOut,
  QuestionsOut,
  RecommendationsOut,
  ResumeUploadOut,
  StatementIn,
  VocabularyOut,
} from "./types";

export class ApiError extends Error {
  readonly status: number;
  readonly detail: unknown;
  /** The whole JSON body, for fields beside `detail` (`error`, `open_change_event_ids`). */
  readonly body: unknown;

  constructor(status: number, detail: unknown, body: unknown = undefined) {
    super(messageFor(status, detail));
    this.name = "ApiError";
    this.status = status;
    this.detail = detail;
    this.body = body;
  }

  /** The API's error class name (`OpeningAlreadyRecordedError`), when the body has one. */
  get errorName(): string | null {
    const value = field(this.body, "error");
    return typeof value === "string" ? value : null;
  }

  /** ChangeEvents left open by a model failure after a write: the write is stored and
   * the nightly sweep finishes the ripple. Empty when nothing was written. */
  get openChangeEventIds(): string[] {
    const value = field(this.body, "open_change_event_ids");
    return Array.isArray(value)
      ? value.filter((id): id is string => typeof id === "string")
      : [];
  }
}

function field(body: unknown, name: string): unknown {
  return body && typeof body === "object" && name in body
    ? (body as Record<string, unknown>)[name]
    : undefined;
}

function messageFor(status: number, detail: unknown): string {
  if (typeof detail === "string" && detail.length > 0) return detail;
  if (status === 401) return "Your token was not accepted.";
  if (status === 404) return "Not found.";
  if (status === 409)
    return "The API refused this change as conflicting with the memory's state.";
  if (status === 413) return "That file is too large for the API.";
  if (status === 415) return "The API accepts a PDF only.";
  if (status === 503) return "The service is temporarily unavailable; try again shortly.";
  return `The API answered with status ${status}.`;
}

/** What every page talks to; tests pass a fake, the app passes `createClient`. */
export interface RippleApi {
  me(): Promise<MeOut>;
  listMemories(query?: ListMemoriesQuery): Promise<MemoriesOut>;
  getMemory(memoryId: string, options?: { history?: boolean }): Promise<MemoryDetailOut>;
  editMemory(memoryId: string, body: EditIn): Promise<IntakeOut>;
  forgetMemory(memoryId: string): Promise<ForgetOut>;
  /** Visible memories and the links between them, for the map (ADR-0087). */
  getGraph(): Promise<GraphOut>;
  /** The domain adapter's kinds, attributes and link types. */
  getVocabulary(): Promise<VocabularyOut>;
  listQuestions(): Promise<QuestionsOut>;
  answerQuestion(memoryId: string, body: AnswerIn): Promise<AnswerOut>;
  listRecommendations(limit?: number): Promise<RecommendationsOut>;
  exportMe(): Promise<ExportOut>;
  deleteMe(): Promise<void>;
  /** Pilot feedback (ADR-0105). The first statement of a (target, kind) wins: a repeat
   * answers 200 with the first row, which `created: false` reports. */
  recordFeedback(body: FeedbackIn): Promise<FeedbackReceipt>;
  /** The user's own feedback rows, oldest first; all of them when no target is given. */
  listFeedback(targetMemoryId?: string): Promise<FeedbackListOut>;
  /** A one-time code the student sends to the bot as `/link CODE` (ADR-0025). */
  createTelegramLink(): Promise<LinkCodeOut>;
  /** A statement through Intake; the answer carries the completed ripple (ADR-0131). */
  postStatement(body: StatementIn): Promise<IntakeOut>;
  /** A pasted JD or forwarded email becomes an opening with derived beliefs (FR-2). */
  postOpening(body: OpeningIn): Promise<OpeningOut>;
  /** The PDF is parsed into pending candidates; nothing is a memory yet (I5). */
  uploadResume(file: File): Promise<ResumeUploadOut>;
  listCandidates(status?: CandidateFilter): Promise<CandidatesOut>;
  confirmCandidate(candidateId: string): Promise<ConfirmOut>;
  rejectCandidate(candidateId: string): Promise<CandidateOut>;
  /** Newest ChangeEvents with the content and status of every memory they name. */
  listEvents(options?: { limit?: number; rippledOnly?: boolean }): Promise<EventsOut>;
}

export interface FeedbackReceipt {
  feedback: Feedback;
  /** true for 201 (a new statement), false for 200 (already recorded). */
  created: boolean;
}

export interface ClientOptions {
  /** Where the API lives. In production Caddy proxies `/api/*` to the API (ADR-0029). */
  baseUrl: string;
  token: string;
  fetchImpl?: typeof fetch;
}

type Query = Record<string, string | number | boolean | null | undefined>;

export function createClient(options: ClientOptions): RippleApi {
  const fetchImpl = options.fetchImpl ?? ((input, init) => fetch(input, init));
  const base = options.baseUrl.replace(/\/+$/, "");

  async function request<T>(
    method: "GET" | "POST" | "DELETE",
    path: string,
    init: { query?: Query; body?: unknown; form?: FormData } = {},
  ): Promise<T> {
    return (await send<T>(method, path, init)).body;
  }

  /** `request` plus the status code, for the one endpoint whose 200 and 201 differ. */
  async function send<T>(
    method: "GET" | "POST" | "DELETE",
    path: string,
    init: { query?: Query; body?: unknown; form?: FormData } = {},
  ): Promise<{ status: number; body: T }> {
    const url = base + path + encodeQuery(init.query);
    const headers: Record<string, string> = {
      Authorization: `Bearer ${options.token}`,
      Accept: "application/json",
    };
    // A multipart body sets its own Content-Type with the boundary; only JSON is ours.
    if (init.body !== undefined) headers["Content-Type"] = "application/json";
    const response = await fetchImpl(url, {
      method,
      headers,
      body: init.form ?? (init.body === undefined ? undefined : JSON.stringify(init.body)),
      // Tokens travel in the header only; never cookies (ADR-0086).
      credentials: "omit",
    });
    if (!response.ok) {
      const body = await readBody(response);
      throw new ApiError(response.status, detailOf(body), body);
    }
    if (response.status === 204) return { status: 204, body: undefined as T };
    return { status: response.status, body: (await response.json()) as T };
  }

  return {
    me: () => request<MeOut>("GET", "/me"),
    listMemories: (query) => request<MemoriesOut>("GET", "/memories", { query }),
    getMemory: (memoryId, options) =>
      request<MemoryDetailOut>("GET", `/memories/${encodeURIComponent(memoryId)}`, {
        query: options?.history ? { history: true } : undefined,
      }),
    editMemory: (memoryId, body) =>
      request<IntakeOut>("POST", `/memories/${encodeURIComponent(memoryId)}/edit`, { body }),
    forgetMemory: (memoryId) =>
      request<ForgetOut>("POST", `/memories/${encodeURIComponent(memoryId)}/forget`),
    getGraph: () => request<GraphOut>("GET", "/graph"),
    getVocabulary: () => request<VocabularyOut>("GET", "/vocabulary"),
    listQuestions: () => request<QuestionsOut>("GET", "/questions"),
    answerQuestion: (memoryId, body) =>
      request<AnswerOut>("POST", `/questions/${encodeURIComponent(memoryId)}/answer`, {
        body,
      }),
    listRecommendations: (limit) =>
      request<RecommendationsOut>("GET", "/recommendations", {
        query: limit === undefined ? undefined : { limit },
      }),
    exportMe: () => request<ExportOut>("GET", "/me/export"),
    deleteMe: () => request<void>("DELETE", "/me"),
    recordFeedback: async (body) => {
      const { status, body: feedback } = await send<Feedback>("POST", "/feedback", { body });
      return { feedback, created: status === 201 };
    },
    listFeedback: (targetMemoryId) =>
      request<FeedbackListOut>("GET", "/feedback", {
        query: { target_memory_id: targetMemoryId },
      }),
    createTelegramLink: () => request<LinkCodeOut>("POST", "/me/telegram/link"),
    postStatement: (body) => request<IntakeOut>("POST", "/statements", { body }),
    postOpening: (body) => request<OpeningOut>("POST", "/openings", { body }),
    uploadResume: (file) => {
      const form = new FormData();
      form.append("file", file, file.name);
      return request<ResumeUploadOut>("POST", "/resume", { form });
    },
    listCandidates: (status) =>
      request<CandidatesOut>("GET", "/resume/candidates", {
        query: status === undefined ? undefined : { status },
      }),
    confirmCandidate: (candidateId) =>
      request<ConfirmOut>(
        "POST",
        `/resume/candidates/${encodeURIComponent(candidateId)}/confirm`,
      ),
    rejectCandidate: (candidateId) =>
      request<CandidateOut>(
        "POST",
        `/resume/candidates/${encodeURIComponent(candidateId)}/reject`,
      ),
    listEvents: (options) =>
      request<EventsOut>("GET", "/events", {
        query: { limit: options?.limit, rippled_only: options?.rippledOnly },
      }),
  };
}

function encodeQuery(query: Query | undefined): string {
  if (!query) return "";
  const params = new URLSearchParams();
  for (const [key, value] of Object.entries(query)) {
    if (value === undefined || value === null) continue;
    params.set(key, String(value));
  }
  const encoded = params.toString();
  return encoded ? `?${encoded}` : "";
}

async function readBody(response: Response): Promise<unknown> {
  try {
    return (await response.json()) as unknown;
  } catch {
    return undefined;
  }
}

function detailOf(body: unknown): unknown {
  return body && typeof body === "object" && "detail" in body
    ? (body as { detail: unknown }).detail
    : body;
}
