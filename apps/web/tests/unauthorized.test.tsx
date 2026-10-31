import { screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { describe, expect, it, vi } from "vitest";

import { ApiError } from "@/api/client";
import { TOKEN_KEY } from "@/auth/token";
import { withUnauthorizedLogout } from "@/auth/unauthorized";
import { MemoryDetailView } from "@/features/memories/MemoryDetailView";
import { QuestionsView } from "@/features/questions/QuestionsView";

import { detail, fakeApi, question, renderSignedIn } from "./helpers";

describe("withUnauthorizedLogout", () => {
  it("calls the handler on a 401 and rethrows; leaves other errors alone", async () => {
    const onUnauthorized = vi.fn();
    const api = withUnauthorizedLogout(
      fakeApi({
        me: vi.fn(async () => Promise.reject(new ApiError(401, undefined))),
        listQuestions: vi.fn(async () => Promise.reject(new ApiError(503, undefined))),
      }),
      onUnauthorized,
    );
    await expect(api.me()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
    await expect(api.listQuestions()).rejects.toBeInstanceOf(ApiError);
    expect(onUnauthorized).toHaveBeenCalledTimes(1);
  });
});

describe("a 401 on a mutation logs out (ADR-0086)", () => {
  it("edit", async () => {
    const api = fakeApi({
      getMemory: vi.fn(async () => detail({ id: "m1" })),
      editMemory: vi.fn(async () => Promise.reject(new ApiError(401, undefined))),
    });
    renderSignedIn(<MemoryDetailView memoryId="m1" />, api);
    await userEvent.click(await screen.findByRole("button", { name: "Edit" }));
    await userEvent.click(screen.getByRole("button", { name: "Save as new version" }));
    await waitFor(() => expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull());
  });

  it("answer", async () => {
    const api = fakeApi({
      listQuestions: vi.fn(async () => ({ questions: [question()] })),
      answerQuestion: vi.fn(async () => Promise.reject(new ApiError(401, undefined))),
    });
    renderSignedIn(<QuestionsView />, api);
    await userEvent.click(await screen.findByRole("button", { name: "Still holds" }));
    await waitFor(() => expect(window.sessionStorage.getItem(TOKEN_KEY)).toBeNull());
  });
});
