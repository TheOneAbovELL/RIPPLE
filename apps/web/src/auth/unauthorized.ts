import { ApiError } from "@/api/client";
import type { RippleApi } from "@/api/client";

/** Wraps a client so that any 401 runs `onUnauthorized` before the error reaches the
 * page. Works for the real client and for test fakes alike, so every mutation path is
 * covered without each page remembering to check. */
export function withUnauthorizedLogout(api: RippleApi, onUnauthorized: () => void): RippleApi {
  const wrapped = {} as Record<keyof RippleApi, unknown>;
  for (const name of Object.keys(api) as (keyof RippleApi)[]) {
    const method = api[name] as (...args: unknown[]) => Promise<unknown>;
    wrapped[name] = async (...args: unknown[]) => {
      try {
        return await method.apply(api, args);
      } catch (error) {
        if (error instanceof ApiError && error.status === 401) onUnauthorized();
        throw error;
      }
    };
  }
  return wrapped as unknown as RippleApi;
}
