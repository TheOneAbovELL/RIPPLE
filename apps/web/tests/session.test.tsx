import { screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { TOKEN_KEY } from "@/auth/token";
import { Shell } from "@/components/Shell";
import { LoginView } from "@/features/login/LoginView";

import { fakeApi, renderSignedIn, renderSignedOut, router } from "./helpers";

const me = {
  id: "u1",
  display_name: "Asha",
  created_at: "2026-10-01T00:00:00Z",
  telegram_linked: false,
};

describe("token login", () => {
  it("stores an accepted token in sessionStorage only and moves to the memories page", async () => {
    const api = fakeApi({ me: vi.fn(async () => me) });
    renderSignedOut(<LoginView />, api);
    await userEvent.type(screen.getByLabelText("Access token"), "  secret-token ");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/home/"));
    expect(window.sessionStorage.getItem(TOKEN_KEY)).toBe("secret-token");
    expect(window.localStorage.length).toBe(0);
    expect(document.cookie).toBe("");
  });

  it("keeps a rejected token out of storage and shows the error", async () => {
    const api = fakeApi({
      me: vi.fn(async () => Promise.reject(new ApiError(401, undefined))),
    });
    renderSignedOut(<LoginView />, api);
    await userEvent.type(screen.getByLabelText("Access token"), "bad");
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Your token was not accepted.");
    expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(router.replace).not.toHaveBeenCalled();
  });

  it("refuses an empty token without calling the API", async () => {
    const api = fakeApi();
    renderSignedOut(<LoginView />, api);
    await userEvent.click(screen.getByRole("button", { name: "Sign in" }));
    expect(await screen.findByRole("alert")).toHaveTextContent("Paste the token");
    expect(api.me).not.toHaveBeenCalled();
  });

  it("sends an already signed-in visitor straight to the memories page", async () => {
    renderSignedIn(<LoginView />, fakeApi());
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/home/"));
  });
});

describe("Shell", () => {
  it("redirects to the login page when no token is stored", async () => {
    renderSignedOut(
      <Shell title="Memories">
        <p>secret content</p>
      </Shell>,
      fakeApi(),
    );
    await waitFor(() => expect(router.replace).toHaveBeenCalledWith("/"));
    expect(screen.queryByText("secret content")).not.toBeInTheDocument();
  });

  it("renders navigation landmarks and the page for a signed-in user", async () => {
    renderSignedIn(
      <Shell title="Memories">
        <p>page body</p>
      </Shell>,
      fakeApi(),
    );
    expect(await screen.findByRole("main")).toHaveTextContent("page body");
    expect(screen.getByRole("navigation", { name: "Main" })).toBeInTheDocument();
    expect(screen.getByRole("link", { name: "Beliefs" })).toHaveAttribute(
      "aria-current",
      "page",
    );
    expect(screen.getByRole("link", { name: "Home" })).not.toHaveAttribute("aria-current");
    expect(screen.getByRole("link", { name: "Skip to content" })).toHaveAttribute(
      "href",
      "#main",
    );
  });

  it("groups the navigation by what the student wants to do, with a lede under the title", async () => {
    renderSignedIn(
      <Shell title="Home" lede="What needs you.">
        <p>body</p>
      </Shell>,
      fakeApi(),
    );
    const nav = await screen.findByRole("navigation", { name: "Main" });
    expect(
      within(nav)
        .getAllByRole("heading")
        .map((h) => h.textContent),
    ).toEqual(["Today", "Tell Ripple", "What Ripple knows", "You"]);
    for (const name of [
      "Say what changed",
      "Add an opening",
      "Resume",
      "Account and Telegram",
    ]) {
      expect(within(nav).getByRole("link", { name })).toBeInTheDocument();
    }
    expect(screen.getByRole("heading", { level: 1, name: "Home" })).toBeInTheDocument();
    expect(screen.getByText("What needs you.")).toBeInTheDocument();
  });

  it("opens and closes the phone menu with aria-expanded", async () => {
    renderSignedIn(
      <Shell title="Home">
        <p>body</p>
      </Shell>,
      fakeApi(),
    );
    const toggle = await screen.findByRole("button", { name: "Menu" });
    expect(toggle).toHaveAttribute("aria-expanded", "false");
    await userEvent.click(toggle);
    expect(screen.getByRole("button", { name: "Close menu" })).toHaveAttribute(
      "aria-expanded",
      "true",
    );
  });

  it("logout clears the stored token and returns to the login page", async () => {
    renderSignedIn(
      <Shell title="Memories">
        <p>page body</p>
      </Shell>,
      fakeApi(),
    );
    await userEvent.click(await screen.findByRole("button", { name: "Log out" }));
    expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull();
    expect(router.replace).toHaveBeenCalledWith("/");
  });
});
