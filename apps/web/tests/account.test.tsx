import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import type { ExportOut, MeOut } from "@/api/types";
import { TOKEN_KEY } from "@/auth/token";
import { AccountView, DELETE_PHRASE } from "@/features/account/AccountView";

import { deferred, fakeApi, renderSignedIn, router } from "./helpers";

const me: MeOut = {
  id: "u1",
  display_name: "Asha",
  created_at: "2026-10-01T00:00:00Z",
  telegram_linked: true,
};

const exportOut: ExportOut = {
  exported_at: "2026-10-24T12:00:00Z",
  user: {
    id: "u1",
    display_name: "Asha",
    created_at: "2026-10-01T00:00:00Z",
    telegram_chat_id: 42,
  },
  memories: [],
  links: [],
  change_events: [],
  forget_events: [],
  resume_candidates: [],
};

describe("AccountView states", () => {
  it("shows a loading status first", async () => {
    const pending = deferred<MeOut>();
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(() => pending.promise) }));
    expect(await screen.findByRole("status")).toHaveTextContent("Loading your account");
    pending.resolve(me);
  });

  it("shows the API error", async () => {
    renderSignedIn(
      <AccountView />,
      fakeApi({ me: vi.fn(async () => Promise.reject(new ApiError(500, undefined))) }),
    );
    expect(await screen.findByRole("alert")).toHaveTextContent("status 500");
  });

  it("renders the profile as the API returned it", async () => {
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(async () => me) }));
    expect(await screen.findByRole("heading", { name: "Asha" })).toBeInTheDocument();
    expect(screen.getByText("Linked")).toBeInTheDocument();
  });
});

describe("Telegram linking (ADR-0025)", () => {
  const unlinked: MeOut = { ...me, telegram_linked: false };

  it("mints a code and shows it with its expiry and the exact /link instruction", async () => {
    const createTelegramLink = vi.fn(async () => ({
      code: "3F9A2C7B1D0E",
      expires_at: "2026-10-31T10:15:00Z",
    }));
    renderSignedIn(
      <AccountView />,
      fakeApi({ me: vi.fn(async () => unlinked), createTelegramLink }),
    );
    expect(await screen.findByText("Not linked")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Get a link code" }));
    expect(await screen.findByText("3F9A2C7B1D0E")).toHaveClass("code-display");
    expect(screen.getByText("/link 3F9A2C7B1D0E")).toBeInTheDocument();
    expect(screen.getByText(/Works once, until 31 Oct 2026/)).toBeInTheDocument();
    expect(createTelegramLink).toHaveBeenCalledTimes(1);
  });

  it("copies the command for the bot", async () => {
    const writeText = vi.fn(async () => undefined);
    Object.defineProperty(navigator, "clipboard", { value: { writeText }, configurable: true });
    renderSignedIn(
      <AccountView />,
      fakeApi({
        me: vi.fn(async () => unlinked),
        createTelegramLink: vi.fn(async () => ({
          code: "ABC123",
          expires_at: "2026-10-31T10:15:00Z",
        })),
      }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Get a link code" }));
    await userEvent.click(await screen.findByRole("button", { name: "Copy “/link ABC123”" }));
    expect(writeText).toHaveBeenCalledWith("/link ABC123");
    expect(await screen.findByText(/Copied/)).toBeInTheDocument();
  });

  it("says a linked chat is linked and offers to move it", async () => {
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(async () => me) }));
    expect(await screen.findByText(/Your Telegram chat is linked/)).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Link another chat" })).toBeInTheDocument();
  });

  it("shows the API error when no code could be minted", async () => {
    renderSignedIn(
      <AccountView />,
      fakeApi({
        me: vi.fn(async () => unlinked),
        createTelegramLink: vi.fn(async () => Promise.reject(new ApiError(429, "slow down"))),
      }),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Get a link code" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("slow down");
  });
});

describe("export", () => {
  const createObjectURL = vi.fn(() => "blob:export");
  const revokeObjectURL = vi.fn();
  let clicked: string[] = [];

  beforeEach(() => {
    clicked = [];
    vi.stubGlobal("URL", { ...URL, createObjectURL, revokeObjectURL });
    vi.spyOn(HTMLAnchorElement.prototype, "click").mockImplementation(function (
      this: HTMLAnchorElement,
    ) {
      clicked.push(this.download);
    });
  });
  afterEach(() => {
    vi.restoreAllMocks();
    vi.unstubAllGlobals();
  });

  it("downloads the export as a JSON file named by its date", async () => {
    const api = fakeApi({ me: vi.fn(async () => me), exportMe: vi.fn(async () => exportOut) });
    renderSignedIn(<AccountView />, api);
    await userEvent.click(await screen.findByRole("button", { name: "Download export" }));
    await waitFor(() => expect(clicked).toEqual(["ripple-export-2026-10-24.json"]));
    expect(createObjectURL).toHaveBeenCalledTimes(1);
    expect(revokeObjectURL).toHaveBeenCalledWith("blob:export");
    expect(screen.getByRole("status")).toHaveTextContent("Your export was downloaded.");
  });

  it("shows the error when the export fails", async () => {
    const api = fakeApi({
      me: vi.fn(async () => me),
      exportMe: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
    });
    renderSignedIn(<AccountView />, api);
    await userEvent.click(await screen.findByRole("button", { name: "Download export" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(clicked).toEqual([]);
  });
});

describe("delete everything", () => {
  it("requires the exact phrase before the delete button arms", async () => {
    const deleteMe = vi.fn(async () => undefined);
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(async () => me), deleteMe }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete my account and data…" }),
    );
    const dialog = screen.getByRole("dialog", { name: /Delete everything for Asha\?/ });
    const confirm = within(dialog).getByRole("button", { name: "Delete everything" });
    expect(confirm).toBeDisabled();
    await userEvent.type(within(dialog).getByLabelText(/to confirm/), "delete");
    expect(confirm).toBeDisabled();
    await userEvent.clear(within(dialog).getByLabelText(/to confirm/));
    await userEvent.type(within(dialog).getByLabelText(/to confirm/), DELETE_PHRASE);
    expect(confirm).toBeEnabled();
    expect(deleteMe).not.toHaveBeenCalled();
  });

  it("deletes through the API, clears the token and returns to the login page", async () => {
    const deleteMe = vi.fn(async () => undefined);
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(async () => me), deleteMe }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete my account and data…" }),
    );
    const dialog = screen.getByRole("dialog", { name: /Delete everything for Asha\?/ });
    await userEvent.type(within(dialog).getByLabelText(/to confirm/), DELETE_PHRASE);
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete everything" }));
    await waitFor(() => expect(deleteMe).toHaveBeenCalledTimes(1));
    await waitFor(() => expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull());
    expect(router.replace).toHaveBeenCalledWith("/");
  });

  it("keeps the session and shows the error when the delete fails", async () => {
    const deleteMe = vi.fn(async () => Promise.reject(new ApiError(503, undefined)));
    renderSignedIn(<AccountView />, fakeApi({ me: vi.fn(async () => me), deleteMe }));
    await userEvent.click(
      await screen.findByRole("button", { name: "Delete my account and data…" }),
    );
    const dialog = screen.getByRole("dialog", { name: /Delete everything for Asha\?/ });
    await userEvent.type(within(dialog).getByLabelText(/to confirm/), DELETE_PHRASE);
    await userEvent.click(within(dialog).getByRole("button", { name: "Delete everything" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("temporarily unavailable");
    expect(window.sessionStorage.getItem(TOKEN_KEY)).toBe("test-token");
  });
});
