import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";
import { OpeningsView } from "@/features/openings/OpeningsView";

import { detail, fakeApi, openingOut, recommendation, renderSignedIn } from "./helpers";

const JD = "SDE intern at Acme. CGPA of 7.5 and above. Apply by 5 Nov.";

describe("OpeningsView", () => {
  it("refuses an empty paste without calling the API", async () => {
    const postOpening = vi.fn();
    renderSignedIn(<OpeningsView />, fakeApi({ postOpening }));
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    expect(screen.getByRole("alert")).toHaveTextContent("Paste the job description first.");
    expect(postOpening).not.toHaveBeenCalled();
  });

  it("posts the pasted text, and marks a forwarded email as such", async () => {
    const postOpening = vi.fn<RippleApi["postOpening"]>(async () => openingOut());
    renderSignedIn(
      <OpeningsView />,
      fakeApi({
        postOpening,
        listRecommendations: vi.fn(async () => ({ recommendations: [] })),
        getMemory: vi.fn(async (id: string) => detail({ id })),
      }),
    );
    await userEvent.click(screen.getByLabelText(/forwarded placement email/));
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    await waitFor(() =>
      expect(postOpening).toHaveBeenCalledWith({ text: JD, source: "email" }),
    );
  });

  it("reads a dropped-in text file into the box", async () => {
    renderSignedIn(<OpeningsView />, fakeApi());
    const file = new File([JD], "jd.txt", { type: "text/plain" });
    await userEvent.upload(screen.getByLabelText(/Or drop a .txt or .eml file/), file);
    expect(await screen.findByDisplayValue(JD)).toBeInTheDocument();
  });

  it("shows each recorded field with the words it came from, and the API's verdict for it", async () => {
    const listRecommendations = vi.fn(async () => ({
      recommendations: [
        recommendation({ opening_memory_id: "other", title: "Other" }),
        recommendation({
          opening_memory_id: "opening-1",
          title: "SDE intern",
          company: "Acme",
          eligible: false,
          fit_score: 0.42,
          fit_reasons: ["needs React; you have not said you know it"],
        }),
      ],
    }));
    renderSignedIn(
      <OpeningsView />,
      fakeApi({
        postOpening: vi.fn(async () => openingOut()),
        listRecommendations,
        getMemory: vi.fn(async (id: string) => detail({ id, content: `belief ${id}` })),
      }),
    );
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));

    expect(
      await screen.findByRole("heading", { name: "Recorded: SDE intern at Acme" }),
    ).toBeInTheDocument();
    const fields = screen.getByRole("list", { name: "Recorded fields" });
    expect(within(fields).getByText("CGPA cutoff")).toBeInTheDocument();
    expect(within(fields).getByLabelText("From the text")).toHaveTextContent(
      "CGPA of 7.5 and above",
    );
    // The verdict is the ranking entry for this opening id, printed as given.
    expect(await screen.findByText("Not eligible")).toBeInTheDocument();
    expect(screen.getByText("fit 42%")).toBeInTheDocument();
    expect(screen.getByText("needs React; you have not said you know it")).toBeInTheDocument();
    expect(listRecommendations).toHaveBeenCalledWith(50);
    expect(await screen.findByRole("link", { name: "belief belief-1" })).toHaveAttribute(
      "href",
      "/memories/detail?id=belief-1",
    );
  });

  it("says plainly when the ranking has no entry for the new opening", async () => {
    renderSignedIn(
      <OpeningsView />,
      fakeApi({
        postOpening: vi.fn(async () => openingOut({ memory_ids: ["opening-1"] })),
        listRecommendations: vi.fn(async () => ({ recommendations: [] })),
      }),
    );
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    expect(
      await screen.findByText(/Ripple has no ranking for this opening yet/),
    ).toBeInTheDocument();
  });

  it("explains a 503 as the missing model and says nothing was stored", async () => {
    renderSignedIn(
      <OpeningsView />,
      fakeApi({ postOpening: vi.fn(async () => Promise.reject(new ApiError(503, undefined))) }),
    );
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    const alert = await screen.findByRole("alert");
    expect(alert).toHaveTextContent(
      "Ripple needs its language model to read a job description",
    );
    expect(alert).toHaveTextContent("Nothing was stored.");
  });

  it("says the opening is already saved and links to it on a 409", async () => {
    const detail = "opening from 'paste:abc' is already recorded as 'opening-9'";
    const body = { detail, error: "OpeningAlreadyRecordedError" };
    renderSignedIn(
      <OpeningsView />,
      fakeApi({
        postOpening: vi.fn(async () => Promise.reject(new ApiError(409, detail, body))),
      }),
    );
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste(JD);
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    expect(await screen.findByRole("alert")).toHaveTextContent(
      "You already saved this opening.",
    );
    expect(screen.getByRole("link", { name: "Open it" })).toHaveAttribute(
      "href",
      "/memories/detail?id=opening-9",
    );
  });

  it("shows the API's own message for a refused description", async () => {
    renderSignedIn(
      <OpeningsView />,
      fakeApi({
        postOpening: vi.fn(async () =>
          Promise.reject(new ApiError(422, "no title or company found")),
        ),
      }),
    );
    await userEvent.click(screen.getByLabelText("Job description or placement email"));
    await userEvent.paste("hello");
    await userEvent.click(screen.getByRole("button", { name: "Record this opening" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("no title or company found");
  });
});
