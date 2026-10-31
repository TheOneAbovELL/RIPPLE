import { describe, expect, it, vi } from "vitest";

import { ApiError, createClient } from "@/api/client";

function fetchReturning(status: number, body: unknown) {
  return vi.fn(
    async () =>
      new Response(body === undefined ? null : JSON.stringify(body), {
        status,
        headers: { "Content-Type": "application/json" },
      }),
  ) as unknown as typeof fetch;
}

describe("createClient", () => {
  it("sends the bearer token in the Authorization header and no cookies", async () => {
    const fetchImpl = fetchReturning(200, { memories: [] });
    const api = createClient({ baseUrl: "/api/", token: "tok-1", fetchImpl });
    await api.listMemories();
    const [url, init] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toBe("/api/memories");
    expect((init.headers as Record<string, string>).Authorization).toBe("Bearer tok-1");
    expect(init.credentials).toBe("omit");
  });

  it("encodes query parameters and skips null ones", async () => {
    const fetchImpl = fetchReturning(200, { memories: [] });
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await api.listMemories({ kind: "opening", status: null, flagged: false });
    const [url] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [string];
    expect(url).toBe("/api/memories?kind=opening&flagged=false");
  });

  it("posts JSON bodies and escapes the memory id in the path", async () => {
    const fetchImpl = fetchReturning(200, {});
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await api.editMemory("a/b", { content: "new" });
    const [url, init] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
      string,
      RequestInit,
    ];
    expect(url).toBe("/api/memories/a%2Fb/edit");
    expect(init.method).toBe("POST");
    expect(init.body).toBe(JSON.stringify({ content: "new" }));
  });

  it("turns a non-2xx response into an ApiError carrying status and detail", async () => {
    const fetchImpl = fetchReturning(409, { detail: "memory has an open question" });
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    const error = await api.editMemory("m", { content: "x" }).catch((e: unknown) => e);
    expect(error).toBeInstanceOf(ApiError);
    expect((error as ApiError).status).toBe(409);
    expect((error as ApiError).message).toBe("memory has an open question");
  });

  it("resolves a 204 with no body", async () => {
    const fetchImpl = fetchReturning(204, undefined);
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await expect(api.deleteMe()).resolves.toBeUndefined();
  });

  it("asks for the history and the recommendation limit through the query string", async () => {
    const fetchImpl = fetchReturning(200, {});
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await api.getMemory("m1", { history: true });
    await api.getMemory("m1");
    await api.listRecommendations(50);
    const urls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls.map(
      (call) => (call as [string])[0],
    );
    expect(urls).toEqual([
      "/api/memories/m1?history=true",
      "/api/memories/m1",
      "/api/recommendations?limit=50",
    ]);
  });

  it("reads the graph and the vocabulary with one GET each", async () => {
    const fetchImpl = fetchReturning(200, {});
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await api.getGraph();
    await api.getVocabulary();
    const calls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls as [
      string,
      RequestInit,
    ][];
    expect(calls.map(([url, init]) => `${init.method} ${url}`)).toEqual([
      "GET /api/graph",
      "GET /api/vocabulary",
    ]);
  });

  it("sends an explicit null valid_to and leaves an omitted one out of the edit body", async () => {
    // EditIn tells "make permanent" (null) from "keep" (absent); JSON must keep that apart.
    const fetchImpl = fetchReturning(200, {});
    const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
    await api.editMemory("m1", { content: "x", valid_to: null });
    await api.editMemory("m1", { content: "x" });
    const bodies = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls.map(
      (call) => (call as [string, RequestInit])[1].body,
    );
    expect(bodies).toEqual(['{"content":"x","valid_to":null}', '{"content":"x"}']);
  });

  describe("pilot feedback (ADR-0105)", () => {
    const row = {
      id: "fb-1",
      user_id: "u1",
      target_memory_id: "opening-1",
      kind: "saved",
      note: null,
      created_at: "2026-10-30T09:00:00Z",
    };

    it("posts the target and kind and reports a 201 as a new statement", async () => {
      const fetchImpl = fetchReturning(201, row);
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const receipt = await api.recordFeedback({
        target_memory_id: "opening-1",
        kind: "saved",
      });
      const [url, init] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
        string,
        RequestInit,
      ];
      expect(`${init.method} ${url}`).toBe("POST /api/feedback");
      expect(init.body).toBe('{"target_memory_id":"opening-1","kind":"saved"}');
      expect(receipt).toEqual({ feedback: row, created: true });
    });

    it("reports a 200 as already recorded, with the first row", async () => {
      const fetchImpl = fetchReturning(200, row);
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const receipt = await api.recordFeedback({
        target_memory_id: "opening-1",
        kind: "saved",
      });
      expect(receipt).toEqual({ feedback: row, created: false });
    });

    it("turns a refused statement into an ApiError", async () => {
      const fetchImpl = fetchReturning(422, { detail: "kind does not fit the target" });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const error = await api
        .recordFeedback({ target_memory_id: "m1", kind: "applied" })
        .catch((e: unknown) => e);
      expect(error).toBeInstanceOf(ApiError);
      expect((error as ApiError).status).toBe(422);
      expect((error as ApiError).message).toBe("kind does not fit the target");
    });

    it("lists every row, or one target's rows through the query string", async () => {
      const fetchImpl = fetchReturning(200, { feedback: [row] });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await expect(api.listFeedback()).resolves.toEqual({ feedback: [row] });
      await api.listFeedback("a/b");
      const calls = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls as [
        string,
        RequestInit,
      ][];
      expect(calls.map(([url, init]) => `${init.method} ${url}`)).toEqual([
        "GET /api/feedback",
        "GET /api/feedback?target_memory_id=a%2Fb",
      ]);
    });
  });

  describe("student write flows (ADR-0131)", () => {
    const calls = (fetchImpl: typeof fetch) =>
      (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls as [string, RequestInit][];

    it("mints a Telegram link code with one POST and no body", async () => {
      const fetchImpl = fetchReturning(201, {
        code: "AB12CD",
        expires_at: "2026-10-31T10:15:00Z",
      });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await expect(api.createTelegramLink()).resolves.toEqual({
        code: "AB12CD",
        expires_at: "2026-10-31T10:15:00Z",
      });
      const [url, init] = calls(fetchImpl)[0]!;
      expect(`${init.method} ${url}`).toBe("POST /api/me/telegram/link");
      expect(init.body).toBeUndefined();
    });

    it("posts statements and openings as JSON", async () => {
      const fetchImpl = fetchReturning(201, {});
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await api.postStatement({
        content: "My CGPA is 8.6",
        kind: "fact",
        origin: "conversation",
        sensitivity: "low",
      });
      await api.postOpening({ text: "SDE intern at Acme", source: "paste" });
      expect(
        calls(fetchImpl).map(([url, init]) => [`${init.method} ${url}`, init.body]),
      ).toEqual([
        [
          "POST /api/statements",
          JSON.stringify({
            content: "My CGPA is 8.6",
            kind: "fact",
            origin: "conversation",
            sensitivity: "low",
          }),
        ],
        ["POST /api/openings", JSON.stringify({ text: "SDE intern at Acme", source: "paste" })],
      ]);
    });

    it("uploads the resume as multipart form data and leaves the Content-Type to the browser", async () => {
      const fetchImpl = fetchReturning(201, { upload_id: "up-1", candidates: [] });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const file = new File(["%PDF-1.7"], "cv.pdf", { type: "application/pdf" });
      await api.uploadResume(file);
      const [url, init] = calls(fetchImpl)[0]!;
      expect(`${init.method} ${url}`).toBe("POST /api/resume");
      expect(init.body).toBeInstanceOf(FormData);
      expect((init.body as FormData).get("file")).toBeInstanceOf(File);
      expect((init.headers as Record<string, string>)["Content-Type"]).toBeUndefined();
    });

    it("lists, confirms and rejects candidates with escaped ids", async () => {
      const fetchImpl = fetchReturning(200, { candidates: [] });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await api.listCandidates();
      await api.listCandidates("all");
      await api.confirmCandidate("c/1");
      await api.rejectCandidate("c/2");
      expect(calls(fetchImpl).map(([url, init]) => `${init.method} ${url}`)).toEqual([
        "GET /api/resume/candidates",
        "GET /api/resume/candidates?status=all",
        "POST /api/resume/candidates/c%2F1/confirm",
        "POST /api/resume/candidates/c%2F2/reject",
      ]);
    });

    it("names a refused file type in plain words", async () => {
      const fetchImpl = fetchReturning(415, {});
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await expect(api.uploadResume(new File(["x"], "cv.txt"))).rejects.toThrow(
        "The API accepts a PDF only.",
      );
    });
  });

  describe("events and error bodies", () => {
    it("asks for the newest rippled events through the query string", async () => {
      const fetchImpl = fetchReturning(200, { events: [], memories: {}, total: 0 });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      await api.listEvents({ limit: 5, rippledOnly: true });
      const [url] = (fetchImpl as unknown as ReturnType<typeof vi.fn>).mock.calls[0] as [
        string,
      ];
      expect(url).toBe("/api/events?limit=5&rippled_only=true");
    });

    it("keeps the whole error body: the error name and the open ripples", async () => {
      const fetchImpl = fetchReturning(503, {
        detail: "LLMUnavailableError; see server logs",
        error: "LLMUnavailableError",
        open_change_event_ids: ["e1", "e2"],
      });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const error = (await api
        .postOpening({ text: "x", source: "paste" })
        .catch((e: unknown) => e)) as ApiError;
      expect(error.errorName).toBe("LLMUnavailableError");
      expect(error.openChangeEventIds).toEqual(["e1", "e2"]);
    });

    it("reports no open ripples when the body names none", async () => {
      const fetchImpl = fetchReturning(503, { detail: "down" });
      const api = createClient({ baseUrl: "/api", token: "t", fetchImpl });
      const error = (await api.listEvents().catch((e: unknown) => e)) as ApiError;
      expect(error.openChangeEventIds).toEqual([]);
      expect(error.errorName).toBeNull();
    });
  });
});
