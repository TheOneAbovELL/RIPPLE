"use client";

import { useRouter } from "next/navigation";
import { useEffect, useId, useState } from "react";

import { useSession } from "@/auth/SessionProvider";
import { BrandMark } from "@/components/BrandMark";
import { HOME } from "@/components/Shell";
import { toError } from "@/lib/useRequest";

/** Token login (ADR-0086). The admin mints a token with `ripple.api.admin`; the student
 * pastes it here. It is checked against GET /me before being kept for this tab. */
export function LoginView() {
  const { ready, api, login } = useSession();
  const router = useRouter();
  const inputId = useId();
  const [token, setToken] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    if (ready && api) router.replace(HOME);
  }, [ready, api, router]);

  async function submit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = token.trim();
    if (!trimmed) {
      setError(new Error("Paste the token you were given."));
      return;
    }
    setBusy(true);
    setError(null);
    try {
      await login(trimmed);
      router.replace(HOME);
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <main className="login-frame" id="main">
      <section className="login-art" aria-label="About Ripple">
        <span className="brand">
          <BrandMark />
          Ripple
        </span>
        <div>
          <h1>When one fact changes, everything that depended on it is re-checked.</h1>
          <p>
            Ripple keeps your placement search honest: a new CGPA, an accepted offer or a moved
            deadline updates every recommendation built on it, and asks you when it is not sure.
          </p>
        </div>
        <p className="login-foot">
          No tracking, no third-party scripts. Your token stays in this tab only.
        </p>
      </section>
      <section className="login" aria-labelledby="sign-in-heading">
        <h2 id="sign-in-heading">Sign in</h2>
        <p>Paste the access token you were given.</p>
        <form onSubmit={submit} noValidate>
          <div className="field">
            <label htmlFor={inputId}>Access token</label>
            <input
              id={inputId}
              type="password"
              autoComplete="off"
              spellCheck={false}
              value={token}
              onChange={(event) => setToken(event.target.value)}
              aria-describedby={`${inputId}-help`}
              aria-invalid={error ? true : undefined}
            />
            <p id={`${inputId}-help`} className="meta">
              Kept only for this browser tab; closing the tab logs you out.
            </p>
          </div>
          {error ? (
            <p className="notice notice-error" role="alert">
              {error.message}
            </p>
          ) : null}
          <button type="submit" disabled={busy}>
            {busy ? "Checking…" : "Sign in"}
          </button>
        </form>
      </section>
    </main>
  );
}
