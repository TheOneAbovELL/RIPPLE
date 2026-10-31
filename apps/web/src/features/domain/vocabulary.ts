/** The domain vocabulary as the API publishes it (GET /vocabulary), so the dashboard
 * hardcodes no domain's kinds. The UI offers these as filter choices and orders map
 * nodes by them; it attaches no rule to any of them. */
import type { RippleApi } from "@/api/client";
import type { VocabularyOut } from "@/api/types";

/** What a page knows about kinds: the API's list, or nothing when the request failed. */
export interface KnownKinds {
  kinds: readonly string[];
  /** false when GET /vocabulary failed and `kinds` is the fallback. */
  fromApi: boolean;
}

/** Used when GET /vocabulary fails: no kinds rather than a guessed list, so the page
 * keeps working (every kind, unfiltered) and never offers a value the API does not know. */
export const NO_KINDS: KnownKinds = { kinds: [], fromApi: false };

export function kindsOf(vocabulary: VocabularyOut): KnownKinds {
  return { kinds: vocabulary.kinds, fromApi: true };
}

/** The vocabulary is a convenience for the page, not its content: a failure degrades to
 * NO_KINDS instead of failing the page. A 401 has already logged the user out by the
 * time it reaches here (withUnauthorizedLogout). */
export async function loadKinds(api: RippleApi): Promise<KnownKinds> {
  try {
    return kindsOf(await api.getVocabulary());
  } catch {
    return NO_KINDS;
  }
}

/** "derived" → "Derived", "accepted_offer" → "Accepted offer". Display only. */
export function kindLabel(kind: string): string {
  const words = kind.replace(/_/g, " ").trim();
  return words ? words.charAt(0).toUpperCase() + words.slice(1) : kind;
}

/** "cgpa_cutoff" → "Cgpa cutoff"; "cgpa" → "CGPA". Display only. */
export function attributeLabel(attribute: string): string {
  return attribute
    .split("_")
    .map((word, index) => (word === "cgpa" ? "CGPA" : index === 0 ? kindLabel(word) : word))
    .join(" ");
}
