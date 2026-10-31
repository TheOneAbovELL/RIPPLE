import { screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";
import type { EventsOut, MeOut } from "@/api/types";
import { HomeView } from "@/features/home/HomeView";

import {
  changeEvent,
  decision,
  deferred,
  fakeApi,
  listed,
  question,
  recommendation,
  renderSignedIn,
} from "./helpers";

const me: MeOut = {
  id: "u1",
  display_name: "Asha",
  created_at: "2026-10-01T00:00:00Z",
  telegram_linked: false,
};

function eventsWith(overrides: Partial<EventsOut> = {}): EventsOut {
  return { events: [], memories: {}, total: 0, ...overrides };
}

function quiet(overrides: Partial<RippleApi> = {}): RippleApi {
  return fakeApi({
    me: vi.fn(async () => me),
    listQuestions: vi.fn(async () => ({ questions: [] })),
    listRecommendations: vi.fn(async () => ({ recommendations: [] })),
    listEvents: vi.fn(async () => eventsWith()),
    listMemories: vi.fn(async () => ({ memories: [] })),
    ...overrides,
  });
}

describe("HomeView", () => {
  it("gives every block an empty state that names the next step", async () => {
    renderSignedIn(<HomeView />, quiet());
    expect(await screen.findByText(/No open questions/)).toBeInTheDocument();
    expect(await screen.findByText(/No deadlines recorded yet/)).toBeInTheDocument();
    expect(await screen.findByText(/Nothing has changed yet/)).toBeInTheDocument();
    expect(await screen.findByText(/Ripple knows nothing about you yet/)).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Link Telegram" })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/account\/?$/),
    );
  });

  it("loads each block on its own: failed events leave the questions visible", async () => {
    const slow = deferred<EventsOut>();
    renderSignedIn(
      <HomeView />,
      quiet({
        listQuestions: vi.fn(async () => ({ questions: [question()] })),
        listEvents: vi.fn(() => slow.promise),
      }),
    );
    expect(await screen.findByText("Is your CGPA still 8.2?")).toBeInTheDocument();
    expect(screen.getByText("Loading recent ripples…")).toBeInTheDocument();
    slow.reject(new ApiError(500, undefined));
    const ripples = screen.getByRole("region", { name: "Recent ripples" });
    expect(await within(ripples).findByRole("alert")).toHaveTextContent("status 500");
    expect(screen.getByText("Is your CGPA still 8.2?")).toBeInTheDocument();
  });

  it("lists recommended openings with a deadline, soonest first, with the API's verdict", async () => {
    renderSignedIn(
      <HomeView />,
      quiet({
        listRecommendations: vi.fn(async () => ({
          recommendations: [
            recommendation({ title: "Late", deadline: "2026-11-20T18:30:00Z", eligible: true }),
            recommendation({ title: "None", deadline: null }),
            // 2 Nov 22:00 IST is 16:30 UTC: earlier than "Mid", though it sorts later as text.
            recommendation({
              title: "Soon",
              deadline: "2026-11-02T22:00:00+05:30",
              eligible: false,
            }),
            recommendation({ title: "Mid", deadline: "2026-11-02T17:00:00Z" }),
          ],
        })),
      }),
    );
    const list = await screen.findByRole("list", { name: "Upcoming deadlines" });
    const rows = within(list).getAllByRole("listitem");
    expect(rows.map((row) => within(row).getByRole("link").textContent)).toEqual([
      "Soon at Acme",
      "Mid at Acme",
      "Late at Acme",
    ]);
    expect(within(rows[0]!).getByText("Not eligible")).toBeInTheDocument();
  });

  it("asks the API for the newest ripples only and shows what each one did", async () => {
    const newer = changeEvent({
      trigger_memory_id: "m-new",
      created_at: "2026-10-30T10:00:00Z",
      decisions: [
        decision({ action: "update", new_version_id: "v2" }),
        decision({ action: "keep" }),
        decision({ action: "keep" }),
      ],
    });
    // `rippled_only` leaves writes that re-checked nothing out on the server.
    const listEvents = vi.fn(async () =>
      eventsWith({
        events: [newer],
        memories: { "m-new": { content: "CGPA is 8.6", status: "VALID" } },
        total: 2,
      }),
    );
    renderSignedIn(<HomeView />, quiet({ listEvents }));
    const list = await screen.findByRole("list", { name: "Recent ripples" });
    // Direct rows only: each collapsed trace holds lists of its own.
    const rows = [...list.querySelectorAll<HTMLElement>(":scope > li")];
    // The trigger is named in the row; the collapsed trace names it again inside.
    expect(within(rows[0]!).getAllByRole("link", { name: "CGPA is 8.6" })[0]).toBeVisible();
    expect(rows[0]).toHaveTextContent("1 belief updated · 2 beliefs kept");
    expect(rows).toHaveLength(1);
    expect(listEvents).toHaveBeenCalledWith({ limit: 5, rippledOnly: true });
    await userEvent.click(within(rows[0]!).getByText("Show the waves"));
    expect(within(rows[0]!).getByText("Wave 1")).toBeInTheDocument();
  });

  it("shows a version the ripple retired as the past, struck through", async () => {
    const event = changeEvent({
      trigger_memory_id: "cgpa-v1",
      decisions: [
        decision({ memory_id: "elig-v1", action: "update", new_version_id: "elig-v2" }),
      ],
    });
    renderSignedIn(
      <HomeView />,
      quiet({
        listEvents: vi.fn(async () =>
          eventsWith({
            events: [event],
            memories: {
              "cgpa-v1": { content: "CGPA is 8.1", status: "RETIRED" },
              "elig-v1": { content: "not eligible for Beta", status: "RETIRED" },
              "elig-v2": { content: "eligible for Beta", status: "VALID" },
            },
            total: 1,
          }),
        ),
      }),
    );
    const list = await screen.findByRole("list", { name: "Recent ripples" });
    const struck = within(list).getAllByText("CGPA is 8.1")[0]!;
    expect(struck.tagName).toBe("DEL");
    expect(within(list).getAllByText("(earlier version)").length).toBeGreaterThan(0);
    // The new version reads as current; the old one appears only as "Was:".
    expect(within(list).getByText("eligible for Beta").tagName).not.toBe("DEL");
    expect(within(list).getByText("not eligible for Beta").tagName).toBe("DEL");
  });

  it("says no change has reached another belief when events exist but none rippled", async () => {
    renderSignedIn(
      <HomeView />,
      quiet({ listEvents: vi.fn(async () => eventsWith({ total: 4 })) }),
    );
    expect(
      await screen.findByText(/No change has reached another belief yet/),
    ).toBeInTheDocument();
  });

  it("counts current beliefs and the API's flags by kind", async () => {
    renderSignedIn(
      <HomeView />,
      quiet({
        listMemories: vi.fn(async () => ({
          memories: [
            listed({ kind: "fact" }),
            listed({ kind: "fact", status: "SUSPECT" }, true),
            listed({ kind: "opening" }),
          ],
        })),
      }),
    );
    // Totals on one row, the per-kind counts on the next: two lists on one grid.
    const totals = await screen.findByRole("list", { name: "Totals" });
    expect(totals).toHaveTextContent("3current beliefs");
    expect(totals).toHaveTextContent("1flagged");
    const kinds = screen.getByRole("list", { name: "Beliefs by kind" });
    expect(kinds).toHaveTextContent("2fact");
    expect(kinds).toHaveTextContent("1opening");
    expect(kinds).not.toHaveTextContent("current beliefs");
  });

  it("points open questions at the questions page", async () => {
    renderSignedIn(
      <HomeView />,
      quiet({ listQuestions: vi.fn(async () => ({ questions: [question(), question()] })) }),
    );
    expect(await screen.findByText("2 questions")).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Answer them" })).toHaveAttribute(
      "href",
      expect.stringMatching(/^\/questions\/?$/),
    );
  });
});
