import { fireEvent, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";
import type { MemoryDetailOut } from "@/api/types";
import { MemoryDetailView } from "@/features/memories/MemoryDetailView";

import {
  changeEvent,
  deferred,
  detail,
  fakeApi,
  memory,
  parent,
  renderSignedIn,
  router,
} from "./helpers";

describe("MemoryDetailView states", () => {
  it("shows a loading status first", async () => {
    const pending = deferred<MemoryDetailOut>();
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(() => pending.promise) }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Loading this memory");
    pending.resolve(detail());
  });

  it("asks for the history explicitly", async () => {
    const getMemory = vi.fn(async () => detail());
    renderSignedIn(<MemoryDetailView memoryId="m1" />, fakeApi({ getMemory }));
    await screen.findByText("Why this is held");
    expect(getMemory).toHaveBeenCalledWith("m1", { history: true });
  });

  it("shows a not-found error from the API", async () => {
    const api = fakeApi({
      getMemory: vi.fn(async () => Promise.reject(new ApiError(404, undefined))),
    });
    renderSignedIn(<MemoryDetailView memoryId="missing" />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("Not found.");
  });

  it("renders content, status, structured fact and the empty why/history states", async () => {
    const api = fakeApi({
      getMemory: vi.fn(async () =>
        detail(
          {
            content: "CGPA is 8.2",
            status: "SUSPECT",
            structured: { subject: "profile", attribute: "cgpa", value: 8.2 },
          },
          { flagged: true },
        ),
      ),
    });
    renderSignedIn(<MemoryDetailView memoryId="m1" />, api);
    // The content appears as the heading and again as version 1 in the history.
    expect((await screen.findAllByText("CGPA is 8.2"))[0]).toBeInTheDocument();
    expect(screen.getAllByText("Suspect")[0]).toHaveClass("chip-status-suspect");
    expect(screen.getByText("Flagged")).toBeInTheDocument();
    expect(screen.getByText("profile · cgpa = 8.2")).toBeInTheDocument();
    expect(screen.getByText("This belief rests on no other memory.")).toBeInTheDocument();
    expect(
      screen.getByText("No change event has touched this memory yet."),
    ).toBeInTheDocument();
  });
});

describe("why and history", () => {
  it("lists each parent with its link type and a link to the parent", async () => {
    const skill = memory({ id: "skill-1", content: "Knows Python" });
    const api = fakeApi({
      getMemory: vi.fn(async () =>
        detail(
          { kind: "derived", content: "Eligible for Acme" },
          {
            why: [
              parent(skill, {
                link_type: "eligibility_of",
                created_by: "rule",
                confidence: 0.75,
              }),
            ],
          },
        ),
      ),
    });
    renderSignedIn(<MemoryDetailView memoryId="d1" />, api);
    const parents = await screen.findByRole("list", { name: "Parents" });
    expect(within(parents).getByText("eligibility_of")).toBeInTheDocument();
    expect(within(parents).getByRole("link", { name: "Knows Python" })).toHaveAttribute(
      "href",
      "/memories/detail?id=skill-1",
    );
    expect(within(parents).getByText(/Link by rule · confidence 75%/)).toBeInTheDocument();
  });

  it("shows retired versions in the history with their label, and events with reasons and questions", async () => {
    const v1 = memory({ id: "v1", version: 1, status: "RETIRED", content: "CGPA is 7.9" });
    const v2 = memory({
      id: "v2",
      version: 2,
      status: "VALID",
      content: "CGPA is 8.2",
      supersedes_id: "v1",
    });
    const api = fakeApi({
      getMemory: vi.fn(async () => ({
        memory: v2,
        flagged: false,
        why: [],
        history: {
          versions: [v1, v2],
          events: [
            changeEvent({
              trigger_kind: "user_edit",
              trigger_memory_id: "v2",
              decisions: [
                {
                  memory_id: "d1",
                  wave: 1,
                  action: "ask",
                  reason: "Eligibility depends on the CGPA cutoff.",
                  question: "Are you still eligible for Acme?",
                  evidence_refs: ["mem:v2"],
                  new_version_id: null,
                },
              ],
            }),
          ],
        },
      })),
    });
    renderSignedIn(<MemoryDetailView memoryId="v2" />, api);
    const versions = await screen.findByRole("list", { name: "Versions" });
    expect(within(versions).getByText("Retired")).toHaveClass("chip-status-retired");
    expect(within(versions).getByText("Version 2")).toBeInTheDocument();
    const events = screen.getByRole("list", { name: "Change events" });
    expect(within(events).getByText("user edit")).toBeInTheDocument();
    expect(
      within(events).getByText(/Eligibility depends on the CGPA cutoff\./),
    ).toBeInTheDocument();
    expect(
      within(events).getByText(/Question: Are you still eligible for Acme\?/),
    ).toBeInTheDocument();
  });
});

describe("edit and forget", () => {
  it("saves an edit through the API and follows the new version", async () => {
    const current = detail({ id: "m1", content: "CGPA is 8.2" });
    const editMemory = vi.fn(async () => ({
      memory: memory({ id: "m2", content: "CGPA is 8.4", version: 2 }),
      change_kind: "update" as const,
      links_written: 0,
      event: null,
    }));
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(async () => current), editMemory }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    const field = screen.getByLabelText("Content");
    await userEvent.clear(field);
    await userEvent.type(field, "CGPA is 8.4");
    await userEvent.click(screen.getByRole("button", { name: "Save as new version" }));
    await waitFor(() =>
      expect(editMemory).toHaveBeenCalledWith("m1", { content: "CGPA is 8.4" }),
    );
    expect(router.push).toHaveBeenCalledWith("/memories/detail?id=m2");
  });

  function editResult() {
    return {
      memory: memory({ id: "m2", version: 2 }),
      change_kind: "update" as const,
      links_written: 0,
      event: null,
    };
  }

  async function openEditFor(current: MemoryDetailOut, editMemory: RippleApi["editMemory"]) {
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(async () => current), editMemory }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
  }

  it("leaves valid_to out of the edit body when the user keeps the current end", async () => {
    const editMemory = vi.fn(async () => editResult());
    await openEditFor(
      detail({ id: "m1", content: "CGPA is 8.2", valid_to: "2027-01-01T00:00:00Z" }),
      editMemory,
    );
    expect(screen.getByRole("radio", { name: "Keep the current end" })).toBeChecked();
    expect(screen.getByLabelText("End date and time")).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Save as new version" }));
    await waitFor(() => expect(editMemory).toHaveBeenCalledTimes(1));
    // toHaveBeenCalledWith treats a key set to undefined as absent; the API does not
    // (absent keeps, null clears), so check the body's own keys.
    const [memoryId, body] = editMemory.mock.calls[0] as unknown as [string, object];
    expect(memoryId).toBe("m1");
    expect(body).toStrictEqual({ content: "CGPA is 8.2" });
  });

  it("sends the chosen end as an ISO timestamp when the user sets one", async () => {
    const editMemory = vi.fn(async () => editResult());
    await openEditFor(detail({ id: "m1", content: "Available from June" }), editMemory);
    await userEvent.click(screen.getByRole("radio", { name: "End at a date and time" }));
    const save = screen.getByRole("button", { name: "Save as new version" });
    expect(save).toBeDisabled();
    fireEvent.change(screen.getByLabelText("End date and time"), {
      target: { value: "2027-03-01T10:30" },
    });
    await userEvent.click(save);
    await waitFor(() =>
      expect(editMemory).toHaveBeenCalledWith("m1", {
        content: "Available from June",
        valid_to: "2027-03-01T05:00:00.000Z", // 10:30 in Asia/Kolkata (vitest.config.ts)
      }),
    );
  });

  it("pre-fills the end date and time with the memory's current end", async () => {
    const editMemory = vi.fn(async () => editResult());
    // 2027-01-01T00:00Z is 05:30 in the pinned test zone (vitest.config.ts, Asia/Kolkata).
    await openEditFor(detail({ id: "m1", valid_to: "2027-01-01T00:00:00Z" }), editMemory);
    await userEvent.click(screen.getByRole("radio", { name: "End at a date and time" }));
    expect(screen.getByLabelText("End date and time")).toHaveValue("2027-01-01T05:30");
  });

  it("sends an explicit null when the user removes the end", async () => {
    const editMemory = vi.fn(async () => editResult());
    await openEditFor(
      detail({ id: "m1", content: "Prefers Bengaluru", valid_to: "2027-01-01T00:00:00Z" }),
      editMemory,
    );
    await userEvent.click(screen.getByRole("radio", { name: /No end/ }));
    await userEvent.click(screen.getByRole("button", { name: "Save as new version" }));
    await waitFor(() =>
      expect(editMemory).toHaveBeenCalledWith("m1", {
        content: "Prefers Bengaluru",
        valid_to: null,
      }),
    );
  });

  it("disables editing of a memory that awaits an answer and points at the questions page", async () => {
    const current = detail({ id: "m1", status: "PENDING_USER" }, { flagged: true });
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(async () => current) }),
    );
    expect(await screen.findByRole("button", { name: "Edit" })).toBeDisabled();
    // next/link normalises the trailing slash per next.config; both spellings reach the
    // same exported page through Caddy's try_files.
    expect(screen.getByRole("link", { name: "answer it" }).getAttribute("href")).toMatch(
      /^\/questions\/?$/,
    );
  });

  it("surfaces the API's 409 when an edit is refused", async () => {
    const current = detail({ id: "m1" });
    const editMemory = vi.fn(async () =>
      Promise.reject(new ApiError(409, "memory has an open question")),
    );
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(async () => current), editMemory }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    await userEvent.click(screen.getByRole("button", { name: "Save as new version" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("memory has an open question");
  });

  it("forgets only after confirmation, then returns to the list", async () => {
    const current = detail({ id: "m1" });
    const forgetMemory = vi.fn(async () => ({
      event: {
        id: "f1",
        user_id: "user-1",
        root_memory_id: "m1",
        deleted_ids: ["m1"],
        created_at: "2026-10-23T00:00:00Z",
      },
    }));
    renderSignedIn(
      <MemoryDetailView memoryId="m1" />,
      fakeApi({ getMemory: vi.fn(async () => current), forgetMemory }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Forget…" }));
    expect(forgetMemory).not.toHaveBeenCalled();
    const dialog = screen.getByRole("dialog", { name: "Forget this memory?" });
    await userEvent.click(within(dialog).getByRole("button", { name: "Cancel" }));
    expect(forgetMemory).not.toHaveBeenCalled();
    await userEvent.click(screen.getByRole("button", { name: "Forget…" }));
    await userEvent.click(within(dialog).getByRole("button", { name: "Forget permanently" }));
    await waitFor(() => expect(forgetMemory).toHaveBeenCalledWith("m1"));
    expect(router.push).toHaveBeenCalledWith("/memories/");
  });
});
