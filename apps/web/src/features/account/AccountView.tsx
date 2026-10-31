"use client";

import { useRouter } from "next/navigation";
import { useState } from "react";

import { useApi, useSession } from "@/auth/SessionProvider";
import { ConfirmDialog } from "@/components/ConfirmDialog";
import { RequestView } from "@/components/RequestView";
import type { LinkCodeOut } from "@/api/types";
import { formatDateTime } from "@/lib/format";
import { toError, useRequest } from "@/lib/useRequest";

export const DELETE_PHRASE = "delete everything";

/** Export and delete-everything (FR-15, ADR-0044). Export first, then delete: the
 * dialog says so, and the delete needs the phrase typed in full. */
export function AccountView() {
  const api = useApi();
  const request = useRequest(() => api.me());
  return (
    <RequestView request={request} what="your account">
      {(me) => (
        <>
          <section className="card" aria-labelledby="who">
            <h2 id="who" className="card-title">
              {me.display_name}
            </h2>
            <dl className="facts">
              <dt>User id</dt>
              <dd>
                <code>{me.id}</code>
              </dd>
              <dt>Since</dt>
              <dd>{formatDateTime(me.created_at)}</dd>
              <dt>Telegram</dt>
              <dd>{me.telegram_linked ? "Linked" : "Not linked"}</dd>
            </dl>
          </section>
          <TelegramSection linked={me.telegram_linked} />
          <ExportSection />
          <DeleteSection displayName={me.display_name} />
        </>
      )}
    </RequestView>
  );
}

/** Telegram linking (ADR-0025): the API mints a one-time code; the student sends
 * `/link CODE` to the bot, which consumes it. The page only shows what the API returned. */
function TelegramSection({ linked }: { linked: boolean }) {
  const api = useApi();
  const [code, setCode] = useState<LinkCodeOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [copied, setCopied] = useState(false);

  async function mint() {
    setBusy(true);
    setError(null);
    setCopied(false);
    try {
      setCode(await api.createTelegramLink());
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  async function copy(command: string) {
    try {
      await navigator.clipboard.writeText(command);
      setCopied(true);
    } catch {
      setCopied(false); // no clipboard permission: the command stays selectable on screen
    }
  }

  return (
    <section aria-labelledby="telegram-heading">
      <h2 id="telegram-heading">Telegram</h2>
      {linked ? (
        <p>
          Your Telegram chat is linked. The daily digest and deadline alerts arrive there, and
          you can tell Ripple things by message. Linking again moves the link to another chat.
        </p>
      ) : (
        <p>
          Link Telegram to get the daily digest and deadline alerts, and to tell Ripple what
          changed from your phone.
        </p>
      )}
      {code ? (
        <div className="panel" aria-live="polite">
          <ol className="steps">
            <li>Open the Ripple bot in Telegram.</li>
            <li>
              Send this message: <code>/link {code.code}</code>
            </li>
          </ol>
          <p>
            Your code: <span className="code-display">{code.code}</span>
          </p>
          <p className="meta">
            Works once, until {formatDateTime(code.expires_at)}. After that, get a new code.
          </p>
          <div className="actions">
            <button
              type="button"
              className="quiet"
              onClick={() => void copy(`/link ${code.code}`)}
            >
              Copy “/link {code.code}”
            </button>
            <button type="button" className="quiet" onClick={() => void mint()} disabled={busy}>
              Get a new code
            </button>
          </div>
          {copied ? (
            <p className="notice notice-ok" role="status">
              Copied. Paste it into the chat with the bot.
            </p>
          ) : null}
        </div>
      ) : (
        <button type="button" onClick={() => void mint()} disabled={busy}>
          {busy ? "Getting a code…" : linked ? "Link another chat" : "Get a link code"}
        </button>
      )}
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
    </section>
  );
}

function ExportSection() {
  const api = useApi();
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);
  const [done, setDone] = useState(false);

  async function download() {
    setBusy(true);
    setError(null);
    setDone(false);
    try {
      const data = await api.exportMe();
      saveJson(`ripple-export-${data.exported_at.slice(0, 10)}.json`, data);
      setDone(true);
    } catch (caught) {
      setError(toError(caught));
    } finally {
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="export-heading">
      <h2 id="export-heading">Export everything</h2>
      <p>
        One JSON file with every memory (including retired versions), link, change event,
        deletion record and resume candidate Ripple holds about you.
      </p>
      <button type="button" onClick={download} disabled={busy}>
        {busy ? "Preparing…" : "Download export"}
      </button>
      {done ? (
        <p className="notice" role="status">
          Your export was downloaded.
        </p>
      ) : null}
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
    </section>
  );
}

function DeleteSection({ displayName }: { displayName: string }) {
  const api = useApi();
  const { logout } = useSession();
  const router = useRouter();
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<Error | null>(null);

  async function deleteEverything() {
    setBusy(true);
    setError(null);
    try {
      await api.deleteMe();
      logout();
      router.replace("/");
    } catch (caught) {
      setError(toError(caught));
      setBusy(false);
    }
  }

  return (
    <section aria-labelledby="delete-heading">
      <h2 id="delete-heading">Delete everything</h2>
      <p>
        Removes every memory, link, question, resume candidate and your account. Your token
        stops working at once. Deletion records with ids only are kept as proof that it
        happened.
      </p>
      <button type="button" className="danger" onClick={() => setOpen(true)}>
        Delete my account and data…
      </button>
      {error ? (
        <p className="notice notice-error" role="alert">
          {error.message}
        </p>
      ) : null}
      <ConfirmDialog
        open={open}
        title={`Delete everything for ${displayName}?`}
        confirmLabel="Delete everything"
        typedPhrase={DELETE_PHRASE}
        busy={busy}
        onConfirm={deleteEverything}
        onCancel={() => setOpen(false)}
      >
        <p>
          There is no grace period and no undo. Download your export first if you want a copy.
        </p>
      </ConfirmDialog>
    </section>
  );
}

function saveJson(filename: string, data: unknown): void {
  const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}
