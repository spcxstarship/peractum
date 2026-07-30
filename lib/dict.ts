import { type DictEntry } from "@/lib/bible";

/**
 * Client for the global dictionary tier (public/dict/s<n>.json, built by
 * scripts/build_dict.py from Whitaker's Words). One dictionary for the whole
 * corpus, hash-sharded so a tap fetches ~1/64th of it; shards are memoized
 * here and cached by the service worker like any other static file.
 */

const SHARDS = 64;

export interface DictForm {
  n: number;
  e: DictEntry[];
}

/** djb2 over UTF-16 code units — must match scripts/build_dict.py shard_of. */
function dictShard(key: string): number {
  let h = 5381;
  for (let i = 0; i < key.length; i++) {
    // stays under 2^53 before the >>>0 truncation, so no precision loss
    h = (h * 33 + key.charCodeAt(i)) >>> 0;
  }
  return h % SHARDS;
}

const shardCache = new Map<number, Promise<Record<string, DictForm>>>();

/** The dictionary entry for a cleaned form (glossFormKey), or null. */
export function lookupDict(formKey: string): Promise<DictForm | null> {
  const s = dictShard(formKey);
  let shard = shardCache.get(s);
  if (!shard) {
    shard = fetch(`/dict/s${s}.json`)
      .then((r) => (r.ok ? r.json() : {}))
      .catch(() => ({}));
    shardCache.set(s, shard);
  }
  return shard.then((m) => m[formKey] ?? null);
}
