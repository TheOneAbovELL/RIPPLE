import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { CandidatesOut, ConfirmOut } from "@/api/types";
import { ResumeView } from "@/features/resume/ResumeView";

import { candidate, deferred, detail, fakeApi, intake, renderSignedIn } from "./helpers";

const pdf = () => new File(["%PDF-1.7 resume"], "cv.pdf", { type: "application/pdf" });

describe("ResumeView states", () => {
  it("shows a loading status while the candidates load", async () => {
    const pending = deferred<CandidatesOut>();
    renderSignedIn(<ResumeView />, fakeApi({ listCandidates: vi.fn(() => pending.promise) }));
    expect(await screen.findByRole("status")).toHaveTextContent(
      "Loading your resume candidates",
    );
    pending.resolve({ candidates: [] });
  });

  it("shows the API error with a retry", async () => {
    renderSignedIn(
      <ResumeView />,
      fakeApi({
        listCandidates: vi.fn(async () => Promise.reject(new ApiError(500, undefined))),
      }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("status 500");
    expect(screen.getByRole("button", { name: "Try again" })).toBeInTheDocument();
  });

  it("says nothing is waiting and asks for the resume when there are no candidates", async () => {
    renderSignedIn(
      <ResumeView />,
      fakeApi({ listCandidates: vi.fn(async () => ({ candidates: [] })) }),
    );
    expect(await screen.findByText(/Nothing is waiting for review/)).toBeInTheDocument();
  });
});

describe("invariant I5 at the UI: nothing is a belief before confirmation", () => {
  it("says so above the list and marks each pending row as not saved, with its source span", async () => {
    const listCandidates = vi.fn(async () => ({
      candidates: [candidate({ content: "Knows Python", span_text: "Skills: Python, SQL" })],
    }));
    renderSignedIn(<ResumeView />, fakeApi({ listCandidates }));
    expect(await screen.findByRole("note")).toHaveTextContent(
      "Nothing from your resume becomes a belief until you confirm it.",
    );
    const list = screen.getByRole("list", { name: "Waiting for your review" });
    const row = within(list).getByRole("listitem");
    expect(within(row).getByText("Not saved yet")).toBeInTheDocument();
    expect(within(row).getByLabelText("From your resume")).toHaveTextContent(
      "Skills: Python, SQL",
    );
    expect(listCandidates).toHaveBeenCalledWith("all");
  });

  it("uploads the PDF, reports how many facts wait for review and reloads the list", async () => {
    const listCandidates = vi
      .fn()
      .mockResolvedValueOnce({ candidates: [] })
      .mockResolvedValueOnce({
        candidates: [candidate(), candidate({ content: "Batch 2028" })],
      });
    const uploadResume = vi.fn(async () => ({
      upload_id: "up-1",
      candidates: [candidate(), candidate()],
    }));
    renderSignedIn(<ResumeView />, fakeApi({ listCandidates, uploadResume }));
    await userEvent.upload(await screen.findByLabelText(/Your resume \(PDF/), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Upload and read" }));
    expect(await screen.findByText(/Ripple found 2 facts to review below/)).toBeInTheDocument();
    expect(uploadResume).toHaveBeenCalledWith(expect.any(File));
    await waitFor(() => expect(listCandidates).toHaveBeenCalledTimes(2));
    expect(await screen.findByText("Batch 2028")).toBeInTheDocument();
  });

  it("refuses to upload without a file", async () => {
    const uploadResume = vi.fn();
    renderSignedIn(
      <ResumeView />,
      fakeApi({ listCandidates: vi.fn(async () => ({ candidates: [] })), uploadResume }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Upload and read" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Choose your resume as a PDF first.");
    expect(uploadResume).not.toHaveBeenCalled();
  });

  it("explains a 503 on upload as the missing model and says nothing was stored", async () => {
    renderSignedIn(
      <ResumeView />,
      fakeApi({
        listCandidates: vi.fn(async () => ({ candidates: [] })),
        uploadResume: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
      }),
    );
    await userEvent.upload(await screen.findByLabelText(/Your resume \(PDF/), pdf());
    await userEvent.click(screen.getByRole("button", { name: "Upload and read" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent("Ripple needs its language model to read your resume");
    expect(alert).toHaveTextContent("Nothing was stored.");
  });

  it("confirms through the API, shows the saved belief and moves the row to decided", async () => {
    const pendingRow = candidate({ id: "cand-py", content: "Knows Python" });
    const confirmedRow = { ...pendingRow, status: "confirmed" as const, memory_id: "mem-py" };
    const listCandidates = vi
      .fn()
      .mockResolvedValueOnce({ candidates: [pendingRow] })
      .mockResolvedValueOnce({ candidates: [confirmedRow] });
    const confirmed: ConfirmOut = {
      candidate: confirmedRow,
      intake: intake({ change_kind: "new", event: null }),
    };
    const confirmCandidate = vi.fn(async () => confirmed);
    renderSignedIn(
      <ResumeView />,
      fakeApi({ listCandidates, confirmCandidate, getMemory: vi.fn(async () => detail()) }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Confirm: Knows Python" }));
    expect(confirmCandidate).toHaveBeenCalledWith("cand-py");
    // Focus moves to the result: the button that had it is gone with the row.
    expect(await screen.findByRole("heading", { name: "Saved: Knows Python" })).toHaveFocus();
    const decided = await screen.findByRole("list", { name: "Already decided" });
    expect(within(decided).getByText("Confirmed")).toBeInTheDocument();
    expect(within(decided).getByRole("link", { name: "Knows Python" })).toHaveAttribute(
      "href",
      "/memories/detail?id=mem-py",
    );
  });

  it("rejects through the API and lists the row as rejected without a belief link", async () => {
    const pendingRow = candidate({ id: "cand-sql", content: "Knows SQL" });
    const listCandidates = vi
      .fn()
      .mockResolvedValueOnce({ candidates: [pendingRow] })
      .mockResolvedValueOnce({ candidates: [{ ...pendingRow, status: "rejected" }] });
    const rejectCandidate = vi.fn(async () => ({ candidate: pendingRow }));
    renderSignedIn(<ResumeView />, fakeApi({ listCandidates, rejectCandidate }));
    await userEvent.click(await screen.findByRole("button", { name: "Reject: Knows SQL" }));
    expect(rejectCandidate).toHaveBeenCalledWith("cand-sql");
    const decided = await screen.findByRole("list", { name: "Already decided" });
    expect(within(decided).getByText("Rejected")).toBeInTheDocument();
    expect(within(decided).queryByRole("link")).not.toBeInTheDocument();
  });

  it("reloads when another tab decided first, so the row shows that outcome", async () => {
    const row = candidate({ id: "cand-py", content: "Knows Python" });
    const listCandidates = vi
      .fn()
      .mockResolvedValueOnce({ candidates: [row] })
      .mockResolvedValueOnce({
        candidates: [{ ...row, status: "confirmed", memory_id: "m-1" }],
      });
    renderSignedIn(
      <ResumeView />,
      fakeApi({
        listCandidates,
        confirmCandidate: vi.fn(async () =>
          Promise.reject(new ApiError(409, "candidate already confirmed")),
        ),
      }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Confirm: Knows Python" }));
    const decided = await screen.findByRole("list", { name: "Already decided" });
    expect(within(decided).getByText("Confirmed")).toBeInTheDocument();
    expect(
      screen.queryByRole("button", { name: "Confirm: Knows Python" }),
    ).not.toBeInTheDocument();
  });

  it("shows any other refusal next to the row", async () => {
    renderSignedIn(
      <ResumeView />,
      fakeApi({
        listCandidates: vi.fn(async () => ({
          candidates: [candidate({ content: "Knows Python" })],
        })),
        confirmCandidate: vi.fn(async () => Promise.reject(new ApiError(500, undefined))),
      }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Confirm: Knows Python" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("status 500");
  });
});
