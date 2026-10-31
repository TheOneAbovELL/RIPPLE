import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";
import type { IntakeOut, ProfileAttributeOut, VocabularyOut } from "@/api/types";
import { TellView, parseValue } from "@/features/tell/TellView";

import {
  changeEvent,
  decision,
  deferred,
  detail,
  fakeApi,
  intake,
  listed,
  renderSignedIn,
} from "./helpers";

const vocabulary: VocabularyOut = {
  domain: "jobs",
  kinds: ["fact"],
  attributes: ["cgpa", "batch", "skill", "project", "cgpa_cutoff", "deadline", "title"],
  link_types: [],
  profile_subject: "student",
  profile_attributes: [
    fact("cgpa", "number"),
    fact("batch", "integer"),
    fact("skill", "text", { multi_valued: true }),
    fact("project", "text", { multi_valued: true }),
    fact("looking", "bool", { permanent: false }),
    fact("resume", "text", { stated_by_user: false }),
  ],
};

function fact(
  name: string,
  value_type: ProfileAttributeOut["value_type"],
  overrides: Partial<ProfileAttributeOut> = {},
): ProfileAttributeOut {
  return {
    name,
    value_type,
    permanent: true,
    multi_valued: false,
    stated_by_user: true,
    ...overrides,
  };
}

function api(overrides: Parameters<typeof fakeApi>[0] = {}) {
  return fakeApi({
    listMemories: vi.fn(async () => ({
      memories: [
        listed({
          content: "CGPA is 8.1",
          structured: { subject: "student", attribute: "cgpa", value: 8.1 },
        }),
        listed({
          kind: "criteria",
          content: "search openings with batch 2028",
          structured: { subject: "student", attribute: "criteria", value: "batch 2028" },
        }),
      ],
    })),
    getVocabulary: vi.fn(async () => vocabulary),
    getMemory: vi.fn(async (id: string) => detail({ id, content: `content of ${id}` })),
    ...overrides,
  });
}

describe("TellView", () => {
  it("refuses an empty statement without calling the API", async () => {
    const postStatement = vi.fn();
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.click(await screen.findByRole("button", { name: "Tell Ripple" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Write what changed first.");
    expect(postStatement).not.toHaveBeenCalled();
  });

  it("sends free text as a conversation statement with no structured fact", async () => {
    const postStatement = vi.fn<RippleApi["postStatement"]>(async () =>
      intake({ event: null }),
    );
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "I accepted an offer");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    await waitFor(() => expect(postStatement).toHaveBeenCalledTimes(1));
    expect(postStatement.mock.calls[0]![0]).toEqual({
      content: "I accepted an offer",
      kind: "fact",
      origin: "conversation",
      sensitivity: "low",
    });
  });

  it("offers the facts Ripple holds with today's value and sends a structured number", async () => {
    const postStatement = vi.fn<RippleApi["postStatement"]>(async () => intake());
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA is 8.6 now");
    const select = screen.getByLabelText("Fact");
    await waitFor(() => expect(select).toBeEnabled());
    expect(within(select).getByRole("option", { name: "CGPA (now: 8.1)" })).toBeInTheDocument();
    // An attribute the profile already holds is not offered twice.
    expect(within(select).queryByRole("option", { name: "CGPA" })).not.toBeInTheDocument();
    // Opening attributes from the shared vocabulary are never offered as profile facts.
    for (const name of ["CGPA cutoff", "Deadline", "Title"]) {
      expect(within(select).queryByRole("option", { name })).not.toBeInTheDocument();
    }
    expect(within(select).getByRole("option", { name: "Batch" })).toBeInTheDocument();
    // Only what the student states: the resume fact is Ripple's, not the student's to type.
    expect(within(select).queryByRole("option", { name: "Resume" })).not.toBeInTheDocument();
    // A derived belief about the student is Ripple's conclusion, not a fact to restate.
    expect(within(select).queryByRole("option", { name: /Criteria/ })).not.toBeInTheDocument();
    await userEvent.selectOptions(select, "cgpa");
    await userEvent.type(screen.getByLabelText("New value"), "8.6");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    await waitFor(() => expect(postStatement).toHaveBeenCalledTimes(1));
    expect(postStatement.mock.calls[0]![0].structured).toEqual({
      subject: "student",
      attribute: "cgpa",
      value: 8.6,
    });
  });

  it("shows the change and every decision of the ripple with its reason", async () => {
    const event = changeEvent({
      trigger_memory_id: "cgpa-v2",
      decisions: [
        decision({
          memory_id: "elig-beta",
          action: "update",
          new_version_id: "elig-beta-v2",
          reason: "recomputed from current parents; changed",
        }),
        decision({ memory_id: "elig-acme", action: "keep", wave: 1 }),
        decision({
          memory_id: "remind-gamma",
          action: "ask",
          wave: 2,
          reason: "rules declined",
          question: "Is the deadline still 5 Nov?",
        }),
      ],
    });
    const result: IntakeOut = intake({ event });
    renderSignedIn(<TellView />, api({ postStatement: vi.fn(async () => result) }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA is 8.6");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));

    expect(await screen.findByRole("status")).toHaveTextContent(
      "Recorded as a new version of a belief Ripple already held.",
    );
    const trace = screen.getByRole("region", { name: "The ripple" });
    expect(within(trace).getByText("1 belief updated")).toBeInTheDocument();
    expect(within(trace).getByText("1 belief needs your answer")).toBeInTheDocument();
    expect(within(trace).getByText("Wave 1")).toBeInTheDocument();
    expect(within(trace).getByText("Wave 2")).toBeInTheDocument();
    expect(within(trace).getByText("rules declined")).toBeInTheDocument();
    expect(within(trace).getByText(/Is the deadline still 5 Nov\?/)).toBeInTheDocument();
    // The updated belief reads as its new version, with the old one underneath.
    expect(
      await within(trace).findByRole("link", { name: "content of elig-beta-v2" }),
    ).toHaveAttribute("href", "/memories/detail?id=elig-beta-v2");
    expect(within(trace).getByText("Was: content of elig-beta")).toBeInTheDocument();
  });

  it("says when nothing changed because Ripple already knew it", async () => {
    renderSignedIn(
      <TellView />,
      api({
        postStatement: vi.fn(async () => intake({ change_kind: "unchanged", event: null })),
      }),
    );
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA is 8.1");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Ripple already knew exactly this",
    );
    expect(screen.queryByRole("region", { name: "The ripple" })).not.toBeInTheDocument();
  });

  it("sends a text fact as typed, even when it is made of digits", async () => {
    const postStatement = vi.fn<RippleApi["postStatement"]>(async () => intake());
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "I built 2048");
    const select = screen.getByLabelText("Fact");
    await waitFor(() => expect(select).toBeEnabled());
    await userEvent.selectOptions(select, "project");
    await userEvent.type(screen.getByLabelText("New value"), "2048");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    await waitFor(() => expect(postStatement).toHaveBeenCalledTimes(1));
    expect(postStatement.mock.calls[0]![0].structured?.value).toBe("2048");
  });

  it("refuses text for a numeric fact before calling the API", async () => {
    const postStatement = vi.fn();
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA changed");
    const select = screen.getByLabelText("Fact");
    await waitFor(() => expect(select).toBeEnabled());
    await userEvent.selectOptions(select, "cgpa");
    await userEvent.type(screen.getByLabelText("New value"), "eight");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    expect(screen.getByRole("alert")).toHaveTextContent("CGPA: A number");
    expect(postStatement).not.toHaveBeenCalled();
  });

  it("says the fact is saved and the ripple will finish when the 503 names open events", async () => {
    const body = {
      detail: "LLMUnavailableError; see server logs",
      error: "LLMUnavailableError",
      open_change_event_ids: ["evt-open"],
    };
    renderSignedIn(
      <TellView />,
      api({
        postStatement: vi.fn(async () => Promise.reject(new ApiError(503, body.detail, body))),
      }),
    );
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA is 8.6");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Saved. Ripple couldn't finish re-checking because the model is unavailable; it will finish automatically.",
    );
  });

  it("asks yes or no for a bool fact, notes it may need the model, and sends a bool", async () => {
    const postStatement = vi.fn<RippleApi["postStatement"]>(async () => intake());
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "I stopped looking");
    const select = screen.getByLabelText("Fact");
    await waitFor(() => expect(select).toBeEnabled());
    await userEvent.selectOptions(select, "looking");
    expect(
      screen.getByText("Ripple may ask a model whether this is temporary."),
    ).toBeInTheDocument();
    const answer = screen.getByLabelText("New value");
    expect(answer.tagName).toBe("SELECT");
    await userEvent.selectOptions(answer, "false");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    await waitFor(() => expect(postStatement).toHaveBeenCalledTimes(1));
    expect(postStatement.mock.calls[0]![0].structured).toEqual({
      subject: "student",
      attribute: "looking",
      value: false,
    });
  });

  it("refuses a decimal for a whole-number fact", async () => {
    const postStatement = vi.fn();
    renderSignedIn(<TellView />, api({ postStatement }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "Batch changed");
    const select = screen.getByLabelText("Fact");
    await waitFor(() => expect(select).toBeEnabled());
    await userEvent.selectOptions(select, "batch");
    await userEvent.type(screen.getByLabelText("New value"), "2028.5");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    expect(screen.getByRole("alert")).toHaveTextContent("A whole number");
    expect(postStatement).not.toHaveBeenCalled();
  });

  it("explains a 503 as the missing language model, not as a passing outage", async () => {
    renderSignedIn(
      <TellView />,
      api({ postStatement: vi.fn(async () => Promise.reject(new ApiError(503, undefined))) }),
    );
    await userEvent.type(await screen.findByLabelText("What changed?"), "I learnt Rust");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Ripple needs its language model");
    expect(alert).toHaveTextContent("ANTHROPIC_API_KEY");
    // No open events: nothing was written, so no "Saved." message.
    expect(alert).not.toHaveTextContent("Saved.");
  });

  it("keeps the button busy while the statement is in flight", async () => {
    const pending = deferred<IntakeOut>();
    renderSignedIn(<TellView />, api({ postStatement: vi.fn(() => pending.promise) }));
    await userEvent.type(await screen.findByLabelText("What changed?"), "CGPA is 8.6");
    await userEvent.click(screen.getByRole("button", { name: "Tell Ripple" }));
    expect(screen.getByRole("button", { name: "Telling Ripple…" })).toBeDisabled();
    pending.resolve(intake({ event: null }));
    expect(await screen.findByRole("button", { name: "Tell Ripple" })).toBeEnabled();
  });
});

describe("parseValue", () => {
  it("reads numbers, whole numbers and yes/no by the vocabulary's value type", () => {
    expect(parseValue(" 8.6 ", "number")).toBe(8.6);
    expect(parseValue("eight", "number")).toBeNull();
    expect(parseValue("2028", "integer")).toBe(2028);
    expect(parseValue("2028.5", "integer")).toBeNull();
    expect(parseValue("true", "bool")).toBe(true);
    expect(parseValue("false", "bool")).toBe(false);
    expect(parseValue("maybe", "bool")).toBeNull();
  });

  it("keeps a text fact exactly as typed, digits included", () => {
    expect(parseValue("2048", "text")).toBe("2048");
    expect(parseValue(" Python ", "text")).toBe("Python");
  });
});
