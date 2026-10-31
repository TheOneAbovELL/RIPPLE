import { act, renderHook } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import { useRequest } from "@/lib/useRequest";

import { deferred } from "./helpers";

describe("useRequest", () => {
  it("shows the result of the newest key even when an older request resolves last", async () => {
    const first = deferred<string>();
    const second = deferred<string>();
    const loads: Record<string, Promise<string>> = { a: first.promise, b: second.promise };
    const { result, rerender } = renderHook(({ key }) => useRequest(() => loads[key]!, key), {
      initialProps: { key: "a" },
    });
    expect(result.current.state.status).toBe("loading");
    rerender({ key: "b" });
    expect(result.current.state.status).toBe("loading");
    await act(async () => second.resolve("B"));
    expect(result.current.state).toEqual({ status: "data", data: "B" });
    await act(async () => first.resolve("A"));
    expect(result.current.state).toEqual({ status: "data", data: "B" });
  });

  it("keeps the last data on screen while a reload is in flight, then swaps it", async () => {
    const calls: ReturnType<typeof deferred<number>>[] = [];
    const { result } = renderHook(() =>
      useRequest(() => {
        const d = deferred<number>();
        calls.push(d);
        return d.promise;
      }),
    );
    await act(async () => calls[0]!.resolve(1));
    expect(result.current.state).toEqual({ status: "data", data: 1 });
    expect(result.current.reloading).toBe(false);
    act(() => result.current.reload());
    expect(result.current.state).toEqual({ status: "data", data: 1 });
    expect(result.current.reloading).toBe(true);
    await act(async () => calls[1]!.resolve(2));
    expect(result.current.state).toEqual({ status: "data", data: 2 });
    expect(result.current.reloading).toBe(false);
  });

  it("goes back to loading, then data, when reloading after an error", async () => {
    const calls: ReturnType<typeof deferred<number>>[] = [];
    const { result } = renderHook(() =>
      useRequest(() => {
        const d = deferred<number>();
        calls.push(d);
        return d.promise;
      }),
    );
    await act(async () => calls[0]!.reject(new Error("boom")));
    expect(result.current.state.status).toBe("error");
    act(() => result.current.reload());
    expect(result.current.state.status).toBe("loading");
    await act(async () => calls[1]!.resolve(3));
    expect(result.current.state).toEqual({ status: "data", data: 3 });
  });

  it("shows loading again, not stale data, when the key changes", async () => {
    const loads: Record<string, ReturnType<typeof deferred<string>>> = {
      a: deferred<string>(),
      b: deferred<string>(),
    };
    const { result, rerender } = renderHook(
      ({ key }) => useRequest(() => loads[key]!.promise, key),
      { initialProps: { key: "a" } },
    );
    await act(async () => loads.a!.resolve("A"));
    expect(result.current.state).toEqual({ status: "data", data: "A" });
    rerender({ key: "b" });
    expect(result.current.state.status).toBe("loading");
    expect(result.current.reloading).toBe(false);
  });
});
