import { screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";

import { MemoryDetailView } from "@/features/memories/MemoryDetailView";

import { detail, fakeApi, memory, parent, renderSignedIn } from "./helpers";

describe("retired memories on the detail page (I1 at the UI)", () => {
  it("never lists a RETIRED parent under why, even if the API returned one", async () => {
    const live = memory({ id: "p-live", content: "Live parent" });
    const retired = memory({ id: "p-old", content: "Retired snapshot", status: "RETIRED" });
    const api = fakeApi({
      getMemory: vi.fn(async () =>
        detail(
          { id: "d1", kind: "derived" },
          {
            why: [
              parent(live),
              parent(retired, { link_class: "snapshot_of", link_type: "sent_with_resume" }),
            ],
          },
        ),
      ),
    });
    renderSignedIn(<MemoryDetailView memoryId="d1" />, api);
    const parents = await screen.findByRole("list", { name: "Parents" });
    expect(within(parents).getByText("Live parent")).toBeInTheDocument();
    expect(within(parents).queryByText("Retired snapshot")).not.toBeInTheDocument();
  });

  it("shows the empty why state when every parent is RETIRED", async () => {
    const retired = memory({ id: "p-old", content: "Retired snapshot", status: "RETIRED" });
    const api = fakeApi({
      getMemory: vi.fn(async () => detail({ id: "d1" }, { why: [parent(retired)] })),
    });
    renderSignedIn(<MemoryDetailView memoryId="d1" />, api);
    expect(
      await screen.findByText("This belief rests on no other memory."),
    ).toBeInTheDocument();
  });

  it("shows a retired version followed from the history as read-only", async () => {
    const api = fakeApi({
      getMemory: vi.fn(async () =>
        detail({ id: "v1", status: "RETIRED", content: "CGPA is 7.9" }),
      ),
    });
    renderSignedIn(<MemoryDetailView memoryId="v1" />, api);
    expect(await screen.findByText(/This is a retired version/)).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Edit" })).not.toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Forget…" })).not.toBeInTheDocument();
    expect(screen.getAllByText("Retired")[0]).toHaveClass("chip-status-retired");
  });

  it("shows where a resume fact came from when the API returns a source", async () => {
    const api = fakeApi({
      getMemory: vi.fn(async () =>
        detail(
          { id: "r1", content: "CGPA is 8.2" },
          {
            source: {
              upload_id: "up-1",
              filename: "asha.pdf",
              uploaded_at: "2026-10-20T09:00:00Z",
              start: 10,
              end: 18,
              quote: "CGPA 8.2",
              line: "Education: B.Tech CSE, CGPA 8.2",
            },
          },
        ),
      ),
    });
    renderSignedIn(<MemoryDetailView memoryId="r1" />, api);
    expect(await screen.findByText("From your resume")).toBeInTheDocument();
    expect(screen.getByText("CGPA 8.2")).toBeInTheDocument();
    expect(screen.getByText(/asha\.pdf/)).toBeInTheDocument();
  });
});
