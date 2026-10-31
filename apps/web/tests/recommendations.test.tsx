import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError, type FeedbackReceipt, type RippleApi } from "@/api/client";
import type { RecommendationsOut } from "@/api/types";
import { RecommendationsView } from "@/features/recommendations/RecommendationsView";

import { deferred, fakeApi, feedbackRow, recommendation, renderSignedIn } from "./helpers";

/** The page always asks GET /feedback too; these tests start with nothing recorded. */
function withFeedback(overrides: Partial<RippleApi> = {}): RippleApi {
  return fakeApi({ listFeedback: vi.fn(async () => ({ feedback: [] })), ...overrides });
}

describe("RecommendationsView states", () => {
  it("shows a loading status first", async () => {
    const pending = deferred<RecommendationsOut>();
    renderSignedIn(
      <RecommendationsView />,
      withFeedback({ listRecommendations: vi.fn(() => pending.promise) }),
    );
    expect(await screen.findByRole("status")).toHaveTextContent("Loading recommendations");
    pending.resolve({ recommendations: [] });
  });

  it("shows an empty message when there is nothing ranked", async () => {
    const api = withFeedback({
      listRecommendations: vi.fn(async () => ({ recommendations: [] })),
    });
    renderSignedIn(<RecommendationsView />, api);
    expect(await screen.findByText(/No recommendations yet/)).toBeInTheDocument();
  });

  it("shows the API error", async () => {
    const api = withFeedback({
      listRecommendations: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
    });
    renderSignedIn(<RecommendationsView />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
  });

  it("renders title, company, fit reasons, deadline and the flag", async () => {
    const api = withFeedback({
      listRecommendations: vi.fn(async () => ({
        recommendations: [recommendation({ opening_memory_id: "o1", flagged: true })],
      })),
    });
    renderSignedIn(<RecommendationsView />, api);
    const list = await screen.findByRole("list", { name: "Recommendations" });
    expect(within(list).getByRole("link", { name: /SDE intern at Acme/ })).toHaveAttribute(
      "href",
      "/memories/detail?id=o1",
    );
    const reasons = within(list).getByRole("list", { name: "Fit reasons" });
    expect(
      within(reasons)
        .getAllByRole("listitem")
        .map((li) => li.textContent),
    ).toEqual(["Knows Python", "Batch 2028 matches"]);
    expect(within(list).getByText(/Deadline:/)).not.toHaveTextContent("none recorded");
    // A flagged verdict waits on an answer: amber, with a way to answer, not a red flag.
    expect(within(list).getByText("Eligible · waiting on your answer")).toHaveClass(
      "chip-verdict-waiting",
    );
    expect(within(list).queryByText("Flagged")).not.toBeInTheDocument();
    expect(within(list).getByRole("link", { name: "Answer" })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/questions\/?$/),
    );
  });

  it("says when no deadline was recorded", async () => {
    const api = withFeedback({
      listRecommendations: vi.fn(async () => ({
        recommendations: [recommendation({ deadline: null })],
      })),
    });
    renderSignedIn(<RecommendationsView />, api);
    expect(await screen.findByText(/Deadline: none recorded/)).toBeInTheDocument();
  });
});

describe("no client-side rules", () => {
  it("prints the API's eligibility verdict even when the fit score would suggest otherwise", async () => {
    const api = withFeedback({
      listRecommendations: vi.fn(async () => ({
        recommendations: [
          recommendation({ title: "High fit, ineligible", eligible: false, fit_score: 0.99 }),
          recommendation({ title: "Low fit, eligible", eligible: true, fit_score: 0.01 }),
        ],
      })),
    });
    renderSignedIn(<RecommendationsView />, api);
    const items = await screen.findAllByRole("listitem", { name: "" });
    const cards = items.filter((li) => li.classList.contains("card"));
    expect(within(cards[0]!).getByText("Not eligible")).toBeInTheDocument();
    expect(within(cards[0]!).getByText("fit 99%")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("Eligible")).toBeInTheDocument();
    expect(within(cards[1]!).getByText("fit 1%")).toBeInTheDocument();
  });
});

describe("pilot feedback (ADR-0105)", () => {
  function card(title: string): HTMLElement {
    const link = screen.getByRole("link", { name: new RegExp(title) });
    return link.closest("li.card") as HTMLElement;
  }

  function receipt(kind: "saved" | "applied" | "dismissed", created: boolean): FeedbackReceipt {
    return { feedback: feedbackRow({ target_memory_id: "o1", kind }), created };
  }

  function oneOpening(overrides: Partial<RippleApi> = {}): RippleApi {
    return withFeedback({
      listRecommendations: vi.fn(async () => ({
        recommendations: [recommendation({ opening_memory_id: "o1", title: "First" })],
      })),
      ...overrides,
    });
  }

  it("asks GET /feedback once for the page and shows each card its own statements", async () => {
    const listFeedback = vi.fn(async () => ({
      feedback: [
        feedbackRow({ target_memory_id: "o1", kind: "saved" }),
        feedbackRow({ target_memory_id: "o2", kind: "dismissed" }),
        feedbackRow({ target_memory_id: "o1", kind: "applied" }),
        feedbackRow({ target_memory_id: "q9", kind: "question_useful" }),
      ],
    }));
    const api = fakeApi({
      listRecommendations: vi.fn(async () => ({
        recommendations: [
          recommendation({ opening_memory_id: "o1", title: "First" }),
          recommendation({ opening_memory_id: "o2", title: "Second" }),
          recommendation({ opening_memory_id: "o3", title: "Third" }),
        ],
      })),
      listFeedback,
    });
    renderSignedIn(<RecommendationsView />, api);
    await waitFor(() =>
      expect(within(card("First")).getByText("Recorded: Saved, Applied.")).toBeInTheDocument(),
    );
    expect(within(card("Second")).getByText("Recorded: Not interested.")).toBeInTheDocument();
    expect(within(card("Third")).queryByText(/^Recorded:/)).toBeNull();
    expect(listFeedback).toHaveBeenCalledTimes(1);
    expect(listFeedback).toHaveBeenCalledWith();
  });

  it("names every button and says under Applied that nothing is submitted (I6)", async () => {
    renderSignedIn(<RecommendationsView />, oneOpening());
    const group = await screen.findByRole("group", {
      name: "What did you do with First at Acme?",
    });
    expect(
      within(group)
        .getAllByRole("button")
        .map((button) => button.textContent),
    ).toEqual(["Saved", "Applied", "Not interested"]);
    expect(within(group).getByRole("button", { name: "Applied" })).toHaveAccessibleDescription(
      "Applied: Only tells Ripple. Nothing is submitted anywhere.",
    );
    // The note sits on its own line under the whole row, not inside it.
    const row = group.querySelector(".feedback-options")!;
    expect(row).not.toHaveTextContent("Only tells Ripple");
  });

  it("sends the opening id and kind, then shows the new statement", async () => {
    const recordFeedback = vi.fn(async () => receipt("saved", true));
    renderSignedIn(<RecommendationsView />, oneOpening({ recordFeedback }));
    await userEvent.click(await screen.findByRole("button", { name: "Saved" }));
    expect(recordFeedback).toHaveBeenCalledWith({ target_memory_id: "o1", kind: "saved" });
    expect(await screen.findByText("Noted: Saved.")).toHaveAttribute("role", "status");
    expect(within(card("First")).getByText("Recorded: Saved.")).toBeInTheDocument();
  });

  it("says when the statement was already recorded", async () => {
    const recordFeedback = vi.fn(async () => receipt("applied", false));
    renderSignedIn(<RecommendationsView />, oneOpening({ recordFeedback }));
    await userEvent.click(await screen.findByRole("button", { name: "Applied" }));
    expect(await screen.findByText("Already recorded: Applied.")).toBeInTheDocument();
    expect(recordFeedback).toHaveBeenCalledWith({ target_memory_id: "o1", kind: "applied" });
    expect(within(card("First")).getByText("Recorded: Applied.")).toBeInTheDocument();
  });

  it("disables the buttons while a statement is in flight", async () => {
    const pending = deferred<FeedbackReceipt>();
    renderSignedIn(
      <RecommendationsView />,
      oneOpening({ recordFeedback: vi.fn(() => pending.promise) }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Not interested" }));
    for (const name of ["Saved", "Applied", "Not interested"]) {
      expect(screen.getByRole("button", { name })).toBeDisabled();
    }
    pending.resolve(receipt("dismissed", true));
    await waitFor(() => expect(screen.getByRole("button", { name: "Saved" })).toBeEnabled());
  });

  it("shows a short error and keeps the recorded state when the API refuses", async () => {
    const recordFeedback = vi.fn(async () => Promise.reject(new ApiError(404, "Not found.")));
    renderSignedIn(<RecommendationsView />, oneOpening({ recordFeedback }));
    await userEvent.click(await screen.findByRole("button", { name: "Saved" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Not found.");
    expect(within(card("First")).queryByText(/^Recorded:/)).toBeNull();
    expect(screen.queryByText(/^Noted/)).toBeNull();
    expect(screen.getByRole("button", { name: "Saved" })).toBeEnabled();
  });

  it("still lists the openings and offers the buttons when GET /feedback fails", async () => {
    const api = oneOpening({
      listFeedback: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
    });
    renderSignedIn(<RecommendationsView />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "Could not load the feedback you gave earlier",
    );
    expect(screen.getByRole("button", { name: "Saved" })).toBeEnabled();
  });
});
