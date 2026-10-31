/** Presentation helpers. They format what the API returned; none derives a fact. */

const dateTime = new Intl.DateTimeFormat("en-IN", {
  dateStyle: "medium",
  timeStyle: "short",
});

export function formatDateTime(iso: string | null | undefined): string {
  if (!iso) return "—";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return iso;
  return dateTime.format(date);
}

/** An API timestamp as the value a `datetime-local` input shows (the browser's zone,
 * minutes precision); "" when there is none. */
export function toDateTimeLocal(iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  const pad = (n: number) => String(n).padStart(2, "0");
  return (
    `${date.getFullYear()}-${pad(date.getMonth() + 1)}-${pad(date.getDate())}` +
    `T${pad(date.getHours())}:${pad(date.getMinutes())}`
  );
}

/** A `datetime-local` value (read in the browser's zone) as the ISO timestamp the API takes. */
export function fromDateTimeLocal(value: string): string {
  return new Date(value).toISOString();
}

export function formatPercent(fraction: number): string {
  return `${Math.round(fraction * 100)}%`;
}

export function shortId(id: string): string {
  return id.length > 10 ? `${id.slice(0, 8)}…` : id;
}

export function structuredToText(
  structured:
    { subject: string; attribute: string; value: string | number | boolean } | null | undefined,
): string | null {
  if (!structured) return null;
  return `${structured.subject} · ${structured.attribute} = ${String(structured.value)}`;
}

const relative = new Intl.RelativeTimeFormat("en-IN", { numeric: "auto" });
const UNITS: [Intl.RelativeTimeFormatUnit, number][] = [
  ["day", 86_400_000],
  ["hour", 3_600_000],
  ["minute", 60_000],
];

/** "in 3 days", "yesterday", "in 5 hours": how far a timestamp is from the reader's
 * clock, for display next to the date itself. It decides nothing (no threshold). */
export function formatRelative(iso: string | null | undefined, nowMs = Date.now()): string {
  if (!iso) return "";
  const at = new Date(iso).getTime();
  if (Number.isNaN(at)) return "";
  const delta = at - nowMs;
  for (const [unit, size] of UNITS) {
    if (Math.abs(delta) >= size || unit === "minute") {
      return relative.format(Math.round(delta / size), unit);
    }
  }
  return "";
}
