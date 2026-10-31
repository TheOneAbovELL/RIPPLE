import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError, type FeedbackReceipt } from "@/api/client";
import type { AnswerOut, QuestionsOut } from "@/api/types";
import { QuestionsView } from "@/features/questions/QuestionsView";

import {
  changeEvent,
  deferred,
  fakeApi,
  feedbackRow,
  memory,
  question,
  renderSignedIn,
} from "./helpers";

function receipt(status: AnswerOut["status"]): AnswerOut {
  return {
    memory_id: "m1",
    status,
    memory: status === "RETIRED" ? null : memory({ id: "m1", status }),
    event: changeEvent({ trigger_kind: "user_answer" }),
  };
}

describe("QuestionsView states", () => {
  it("shows a loading status first", async () => {
    const pending = deferred<QuestionsOut>();
    renderSignedIn(<QuestionsView />, fakeApi({ listQuestions: vi.fn(() => pending.promise) }));
    expect(await screen.findByRole("status")).toHaveTextContent("Loading questions");
    pending.resolve({ questions: [] });
  });

  it("shows an empty message when nothing is pending", async () => {
    renderSignedIn(
      <QuestionsView />,
      fakeApi({ listQuestions: vi.fn(async () => ({ questions: [] })) }),
    );
    expect(await screen.findByText(/Nothing to answer/)).toBeInTheDocument();
  });

  it("shows the API error", async () => {
    const api = fakeApi({
      listQuestions: vi.fn(async () => Promise.reject(new ApiError(500, undefined))),
    });
    renderSignedIn(<QuestionsView />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("status 500");
  });

  it("renders the question, the reason and the memory it is about", async () => {
    const q = question({
      memory: memory({ id: "m1", status: "PENDING_USER", content: "CGPA is 8.2" }),
    });
    renderSignedIn(
      <QuestionsView />,
      fakeApi({ listQuestions: vi.fn(async () => ({ questions: [q] })) }),
    );
    expect(await screen.findByText("Is your CGPA still 8.2?")).toBeInTheDocument();
    expect(screen.getByText(/A newer transcript was recorded\./)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "CGPA is 8.2" })).toHaveAttribute(
      "href",
      "/memories/detail?id=m1",
    );
    expect(screen.getByText("Awaiting your answer")).toHaveClass("chip-status-pending_user");
  });
});

describe("answering", () => {
  function setup(answerQuestion: ReturnType<typeof vi.fn>) {
    const q = question({
      memory: memory({ id: "m1", status: "PENDING_USER", content: "CGPA is 8.2" }),
    });
    const listQuestions = vi
      .fn<() => Promise<QuestionsOut>>()
      .mockResolvedValueOnce({ questions: [q] })
      .mockResolvedValue({ questions: [] });
    renderSignedIn(
      <QuestionsView />,
      fakeApi({ listQuestions, answerQuestion: answerQuestion as never }),
    );
    return { listQuestions };
  }

  it("sends still_holds", async () => {
    const answerQuestion = vi.fn(async () => receipt("VALID"));
    setup(answerQuestion);
    await userEvent.click(await screen.findByRole("button", { name: "Still holds" }));
    await waitFor(() =>
      expect(answerQuestion).toHaveBeenCalledWith("m1", { answer: "still_holds" }),
    );
  });

  it("sends no_longer_holds and keeps the receipt visible after the list reloads", async () => {
    const answerQuestion = vi.fn(async () => receipt("RETIRED"));
    const { listQuestions } = setup(answerQuestion);
    await userEvent.click(await screen.findByRole("button", { name: "No longer holds" }));
    await waitFor(() =>
      expect(answerQuestion).toHaveBeenCalledWith("m1", { answer: "no_longer_holds" }),
    );
    await waitFor(() => expect(listQuestions).toHaveBeenCalledTimes(2));
    expect(await screen.findByText(/Nothing to answer/)).toBeInTheDocument();
    const receipts = screen.getByRole("list", { name: "Answers recorded" });
    expect(receipts).toHaveTextContent("Is your CGPA still 8.2?");
    expect(receipts).toHaveTextContent("The memory is now retired.");
  });

  it("sends a correction with content and valid_to", async () => {
    const answerQuestion = vi.fn(async () => receipt("VALID"));
    setup(answerQuestion);
    await userEvent.click(await screen.findByRole("button", { name: "Correct it" }));
    const content = screen.getByLabelText("Corrected content");
    await userEvent.clear(content);
    await userEvent.type(content, "CGPA is 8.4");
    await userEvent.click(screen.getByRole("button", { name: "Save correction" }));
    await waitFor(() =>
      expect(answerQuestion).toHaveBeenCalledWith("m1", {
        answer: "correction",
        content: "CGPA is 8.4",
        valid_to: null,
      }),
    );
  });

  it("shows the API error when an answer is refused", async () => {
    const answerQuestion = vi.fn(async () =>
      Promise.reject(new ApiError(409, "memory is not pending")),
    );
    setup(answerQuestion);
    await userEvent.click(await screen.findByRole("button", { name: "Still holds" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("memory is not pending");
  });
});

describe("was this question useful (ADR-0105)", () => {
  function answeredOnce(recordFeedback: ReturnType<typeof vi.fn>) {
    const q = question({
      memory: memory({ id: "m1", status: "PENDING_USER", content: "CGPA is 8.2" }),
    });
    const listQuestions = vi
      .fn<() => Promise<QuestionsOut>>()
      .mockResolvedValueOnce({ questions: [q] })
      .mockResolvedValue({ questions: [] });
    renderSignedIn(
      <QuestionsView />,
      fakeApi({
        listQuestions,
        answerQuestion: vi.fn(async () => receipt("VALID")),
        recordFeedback: recordFeedback as never,
      }),
    );
  }

  async function answerAndFindPrompt() {
    expect(screen.queryByRole("group", { name: "Was this question useful?" })).toBeNull();
    await userEvent.click(await screen.findByRole("button", { name: "Still holds" }));
    return screen.findByRole("group", { name: "Was this question useful?" });
  }

  function said(kind: "question_useful" | "question_not_useful", created: boolean) {
    return { feedback: feedbackRow({ target_memory_id: "m1", kind }), created };
  }

  it("asks only after the answer and sends question_useful about the asked memory", async () => {
    const recordFeedback = vi.fn(async () => said("question_useful", true));
    answeredOnce(recordFeedback);
    const prompt = await answerAndFindPrompt();
    await userEvent.click(within(prompt).getByRole("button", { name: "Yes" }));
    expect(recordFeedback).toHaveBeenCalledWith({
      target_memory_id: "m1",
      kind: "question_useful",
    });
    expect(await within(prompt).findByText("Noted: Yes.")).toBeInTheDocument();
    expect(within(prompt).getByText("Recorded: Yes.")).toBeInTheDocument();
  });

  it("sends question_not_useful and says when it was already recorded", async () => {
    const recordFeedback = vi.fn(async () => said("question_not_useful", false));
    answeredOnce(recordFeedback);
    const prompt = await answerAndFindPrompt();
    await userEvent.click(within(prompt).getByRole("button", { name: "No" }));
    expect(recordFeedback).toHaveBeenCalledWith({
      target_memory_id: "m1",
      kind: "question_not_useful",
    });
    expect(await within(prompt).findByText("Already recorded: No.")).toBeInTheDocument();
  });

  it("disables Yes and No while the statement is in flight", async () => {
    const pending = deferred<FeedbackReceipt>();
    answeredOnce(vi.fn(() => pending.promise));
    const prompt = await answerAndFindPrompt();
    await userEvent.click(within(prompt).getByRole("button", { name: "Yes" }));
    expect(within(prompt).getByRole("button", { name: "Yes" })).toBeDisabled();
    expect(within(prompt).getByRole("button", { name: "No" })).toBeDisabled();
    pending.resolve(said("question_useful", true));
    await waitFor(() =>
      expect(within(prompt).getByRole("button", { name: "No" })).toBeEnabled(),
    );
  });

  it("shows a short error and records nothing when the API refuses", async () => {
    const recordFeedback = vi.fn(async () =>
      Promise.reject(new ApiError(422, "kind does not fit the target")),
    );
    answeredOnce(recordFeedback);
    const prompt = await answerAndFindPrompt();
    await userEvent.click(within(prompt).getByRole("button", { name: "Yes" }));
    expect(await within(prompt).findByRole("alert")).toHaveTextContent(
      "kind does not fit the target",
    );
    expect(within(prompt).queryByText(/^Recorded:/)).toBeNull();
    expect(within(prompt).getByRole("button", { name: "Yes" })).toBeEnabled();
  });
});
