import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import type { MemoriesOut } from "@/api/types";
import { TOKEN_KEY } from "@/auth/token";
import { MemoriesView } from "@/features/memories/MemoriesView";

import { ApiError } from "@/api/client";

import { deferred, fakeApi, listed, renderSignedIn } from "./helpers";

describe("MemoriesView states", () => {
  it("shows a loading status while the list is in flight", async () => {
    const pending = deferred<MemoriesOut>();
    const api = fakeApi({ listMemories: vi.fn(() => pending.promise) });
    renderSignedIn(<MemoriesView />, api);
    expect(await screen.findByRole("status")).toHaveTextContent("Loading memories");
    pending.resolve({ memories: [] });
  });

  it("shows an empty message when the API returns no memories", async () => {
    const api = fakeApi({ listMemories: vi.fn(async () => ({ memories: [] })) });
    renderSignedIn(<MemoriesView />, api);
    expect(await screen.findByText("No memories match these filters.")).toBeInTheDocument();
  });

  it("shows the error and a retry button when the API fails", async () => {
    const listMemories = vi
      .fn<() => Promise<MemoriesOut>>()
      .mockRejectedValueOnce(new ApiError(503, undefined))
      .mockResolvedValueOnce({ memories: [listed({ content: "Back again" })] });
    const api = fakeApi({ listMemories });
    renderSignedIn(<MemoriesView />, api);
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    await userEvent.click(screen.getByRole("button", { name: "Try again" }));
    expect(await screen.findByText("Back again")).toBeInTheDocument();
  });

  it("logs out when the token is rejected", async () => {
    const api = fakeApi({
      listMemories: vi.fn(async () => Promise.reject(new ApiError(401, undefined))),
    });
    renderSignedIn(<MemoriesView />, api);
    await waitFor(() => expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull());
  });

  it("renders every memory with a status chip that carries text and a colour class", async () => {
    const api = fakeApi({
      listMemories: vi.fn(async () => ({
        memories: [
          listed({ content: "Python", status: "VALID" }),
          listed({ content: "CGPA 8.2", status: "SUSPECT" }, true),
          listed({ content: "Batch 2028", status: "PENDING_USER" }, true),
        ],
      })),
    });
    renderSignedIn(<MemoriesView />, api);
    const list = await screen.findByRole("list", { name: "Memories" });
    const items = within(list).getAllByRole("listitem");
    expect(items).toHaveLength(3);
    expect(within(items[0]!).getByText("Valid")).toHaveClass("chip-status-valid");
    expect(within(items[1]!).getByText("Suspect")).toHaveClass("chip-status-suspect");
    expect(within(items[2]!).getByText("Awaiting your answer")).toHaveClass(
      "chip-status-pending_user",
    );
    expect(within(items[0]!).queryByText("Flagged")).not.toBeInTheDocument();
    expect(within(items[1]!).getByText("Flagged")).toBeInTheDocument();
    expect(within(items[2]!).getByText("Flagged")).toBeInTheDocument();
  });

  it("links each memory to its detail page by id", async () => {
    const api = fakeApi({
      listMemories: vi.fn(async () => ({
        memories: [listed({ id: "mem a", content: "Python" })],
      })),
    });
    renderSignedIn(<MemoriesView />, api);
    expect(await screen.findByRole("link", { name: "Python" })).toHaveAttribute(
      "href",
      "/memories/detail?id=mem%20a",
    );
  });
});

describe("MemoriesView filters", () => {
  it("offers the kinds GET /vocabulary lists, not a built-in list", async () => {
    const getVocabulary = vi.fn(async () => ({
      domain: "recipes",
      kinds: ["ingredient", "dish"],
      attributes: [],
      link_types: [],
      profile_subject: "student",
      profile_attributes: [],
    }));
    const listMemories = vi.fn(async () => ({ memories: [] }));
    renderSignedIn(<MemoriesView />, fakeApi({ listMemories, getVocabulary }));
    await screen.findByRole("option", { name: "Dish" });
    const options = within(screen.getByLabelText("Kind")).getAllByRole("option");
    expect(options.map((option) => option.textContent)).toEqual([
      "Any kind",
      "Ingredient",
      "Dish",
    ]);
    expect(screen.getByLabelText("Kind")).toBeEnabled();
  });

  it("falls back to every kind, filter disabled, when the vocabulary fails to load", async () => {
    const getVocabulary = vi.fn(async () => Promise.reject(new ApiError(503, undefined)));
    const listMemories = vi.fn(async () => ({ memories: [listed({ content: "Knows Go" })] }));
    renderSignedIn(<MemoriesView />, fakeApi({ listMemories, getVocabulary }));
    expect(await screen.findByText(/Kind choices could not be loaded/)).toBeInTheDocument();
    const kind = screen.getByLabelText("Kind");
    expect(kind).toBeDisabled();
    expect(within(kind).getAllByRole("option")).toHaveLength(1);
    // The list itself is unaffected: still loaded, still unfiltered by kind.
    expect(await screen.findByText("Knows Go")).toBeInTheDocument();
    expect(listMemories).toHaveBeenLastCalledWith({ kind: null, status: null, flagged: true });
  });

  it("asks the API for the chosen kind instead of filtering locally", async () => {
    const listMemories = vi.fn(async () => ({ memories: [] }));
    const getVocabulary = vi.fn(async () => ({
      domain: "jobs",
      kinds: ["fact", "opening"],
      attributes: [],
      link_types: [],
      profile_subject: "student",
      profile_attributes: [],
    }));
    renderSignedIn(<MemoriesView />, fakeApi({ listMemories, getVocabulary }));
    await screen.findByText("No memories match these filters.");
    await screen.findByRole("option", { name: "Opening" });
    await userEvent.selectOptions(screen.getByLabelText("Kind"), "opening");
    await waitFor(() =>
      expect(listMemories).toHaveBeenLastCalledWith({
        kind: "opening",
        status: null,
        flagged: true,
      }),
    );
  });

  it("sends flagged=false when the flagged toggle is off", async () => {
    const listMemories = vi.fn(async () => ({ memories: [] }));
    renderSignedIn(<MemoriesView />, fakeApi({ listMemories }));
    await screen.findByText("No memories match these filters.");
    await userEvent.click(screen.getByLabelText(/Include flagged/));
    await waitFor(() =>
      expect(listMemories).toHaveBeenLastCalledWith({
        kind: null,
        status: null,
        flagged: false,
      }),
    );
  });

  it("offers only the statuses the list endpoint accepts: never RETIRED", () => {
    renderSignedIn(
      <MemoriesView />,
      fakeApi({ listMemories: vi.fn(async () => ({ memories: [] })) }),
    );
    const options = within(screen.getByLabelText("Status")).getAllByRole("option");
    expect(options.map((o) => o.textContent)).toEqual([
      "Any status",
      "Valid",
      "Suspect",
      "Awaiting your answer",
    ]);
  });
});

describe("invariant I1 at the UI", () => {
  it("never renders a RETIRED memory in the list even if the API returned one", async () => {
    const api = fakeApi({
      listMemories: vi.fn(async () => ({
        memories: [
          listed({ content: "Still valid", status: "VALID" }),
          listed({ content: "Old CGPA", status: "RETIRED" }),
        ],
      })),
    });
    renderSignedIn(<MemoriesView />, api);
    await screen.findByText("Still valid");
    expect(screen.queryByText("Old CGPA")).not.toBeInTheDocument();
    expect(screen.queryByText("Retired")).not.toBeInTheDocument();
  });

  it("shows the empty state when every returned memory is RETIRED", async () => {
    const api = fakeApi({
      listMemories: vi.fn(async () => ({ memories: [listed({ status: "RETIRED" })] })),
    });
    renderSignedIn(<MemoriesView />, api);
    expect(await screen.findByText("No memories match these filters.")).toBeInTheDocument();
  });
});
