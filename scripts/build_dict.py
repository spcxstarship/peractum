#!/usr/bin/env python3
"""Build the dictionary tier: one global dictionary over every wordform in
the corpus, sharded for lazy loading.

    python3 scripts/build_dict.py                # whole corpus -> public/dict/
    python3 scripts/build_dict.py --with-curated # overlay registry entries

Every distinct form in public/bible/**/*.json goes through Whitaker's Words
(the real Ada program, in the `whitakers` Docker image built from
mk270/whitakers-words). The parsed candidate analyses land in
public/dict/s<0..63>.json, keyed by the cleaned form (lib/bible.ts
glossFormKey); the shard for a form is djb2(form) % 64, mirrored in
lib/dict.ts. The hand-written entries in docs/dict/custom-vocabulary.json
fill the forms Words does not know.

This is the machine tier: for each form it records *candidate* analyses —
citation, class, senses, possible parses — with no judgement about which
reading a given verse uses. The per-chapter gloss.json (hand-annotated,
LLM-assisted) always wins over it in the app. By default the dictionary is
pure Whitaker's; --with-curated overlays the citation/definition strings of
lemmas the annotated chapters have settled (docs/gloss/lemmas.json).
"""

import collections
import json
import os
import re
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHARDS = 64

# A word Words will never know, fed between every real word so its UNKNOWN
# echo delimits the output blocks; prompt counting alone is unreliable.
SENTINEL = "qqzzqx"


# Clementine spelling -> the classical spellings Words knows.
def normalize(w: str) -> str:
    return (w.replace("æ", "ae").replace("œ", "oe").replace("j", "i")
             .replace("ë", "e").replace("ï", "i"))


def form_key(display: str) -> str:
    """Strip punctuation and lowercase — must match lib/bible.ts glossFormKey."""
    return re.sub(r"^[^\wÆæŒœëï]+|[^\wÆæŒœëï]+$", "", display).lower()


def shard_of(key: str) -> int:
    """djb2 over UTF-16 code units — must match lib/dict.ts dictShard."""
    h = 5381
    for ch in key:
        h = (h * 33 + ord(ch)) & 0xFFFFFFFF
    return h % SHARDS


# ---------- Words output -> structured candidates ----------

POS_KIND = {"N": "noun", "V": "verb", "VPAR": "verb", "SUPINE": "verb",
            "ADJ": "adjective", "ADV": "adverb", "PREP": "preposition",
            "CONJ": "conjunction", "PRON": "pronoun", "PACK": "pronoun",
            "NUM": "numeral", "INTERJ": "interjection"}
CASES = {"NOM": "nominative", "GEN": "genitive", "DAT": "dative",
         "ACC": "accusative", "ABL": "ablative", "VOC": "vocative",
         "LOC": "locative"}
NUMS = {"S": "singular", "P": "plural"}
GENDS = {"M": "masculine", "F": "feminine", "N": "neuter", "C": "common"}
TENSES = {"PRES": "present", "IMPF": "imperfect", "FUT": "future",
          "PERF": "perfect", "PLUP": "pluperfect", "FUTP": "future perfect"}
PERSONS = {"1": "first", "2": "second", "3": "third"}
ORDINAL = {"(1st)": "I", "(2nd)": "II", "(3rd)": "III", "(4th)": "IV",
           "(5th)": "V"}
# flags are [AGE AREA GEO FREQ SOURCE]; candidates sort by FREQ, commonest
# first (X means unflagged, which in practice is ordinary vocabulary)
FREQ_RANK = {"A": 0, "X": 1, "B": 2, "C": 3, "D": 4, "E": 5, "F": 6}
CASE_WORDS = ("nominative", "genitive", "dative", "accusative", "ablative",
              "vocative")

INFL_RE = re.compile(
    r"^(\S+)\s{2,}(N|V|VPAR|ADJ|ADV|PREP|CONJ|PRON|NUM|INTERJ|SUPINE|PACK)"
    r"\s+(.*?)\s*$")
FLAGS_RE = re.compile(r"\[([A-Z]{5})\]")


def parse_infl(pos: str, codes: str) -> str | None:
    """One inflection line's codes -> a house-style parse phrase."""
    toks = codes.split()
    # the first two tokens are declension/conjugation + variant digits;
    # drop them or a verb's conjugation number reads as its person
    if len(toks) >= 2 and toks[0].isdigit() and toks[1].isdigit():
        toks = toks[2:]
    case = next((CASES[t] for t in toks if t in CASES), None)
    if case == "locative":          # noise for a Vulgate reader
        return None
    num = next((NUMS[t] for t in toks if t in NUMS), None)
    gend = next((GENDS[t] for t in toks if t in GENDS), None)
    if pos == "N":
        return f"{case} {num}" if case else None
    if pos in ("ADJ", "PRON", "NUM", "PACK"):
        bits = " ".join(b for b in (case, num, gend) if b)
        if "COMP" in toks:
            bits += ", comparative"
        if "SUPER" in toks:
            bits += ", superlative"
        return bits or None
    if pos == "VPAR":
        tense = next((TENSES[t] for t in toks if t in TENSES), "")
        ppl = {"present": "present participle", "perfect": "perfect participle",
               "future": "future participle"}.get(tense, "participle")
        if "PASSIVE" in toks and tense == "future":
            ppl = "gerundive"
        bits = " ".join(b for b in (case, num, gend) if b)
        return f"{bits}, {ppl}" if bits else ppl
    if pos == "SUPINE":
        return f"{case} supine"
    if pos == "V":
        tense = next((TENSES[t] for t in toks if t in TENSES), None)
        if tense is None:
            return None
        passive = "PASSIVE" in toks
        if "INF" in toks:
            return f"{tense}{' passive' if passive else ''} infinitive"
        mood = "subjunctive" if "SUB" in toks else \
               "imperative" if "IMP" in toks else ""
        pers = next((PERSONS[t] for t in toks if t in PERSONS), None)
        head = tense + (" passive" if passive else "") + \
            (f" {mood}" if mood else "")
        if pers and num:
            return f"{head}, {pers} {num}"
        return head
    if pos == "PREP":
        abl = "ABL" in toks
        return f"preposition with the {'ablative' if abl else 'accusative'}"
    if pos == "ADV":
        return "adverb"
    return None


def merge_parses(ps):
    """["dative plural, x", "ablative plural, x"] -> ["dative or ablative
    plural, x"] — one line per reading, not one per case."""
    order, buckets, other = [], {}, []
    for p in ps:
        head, _, rest = p.partition(" ")
        if head in CASE_WORDS:
            if rest not in buckets:
                order.append(rest)
            buckets.setdefault(rest, []).append(head)
        else:
            other.append(p)
    merged = [(" or ".join(buckets[rest]) + " " + rest).strip()
              for rest in order]
    return merged + other


def parse_dict_line(line: str):
    """'abyssus, abyssi  N (2nd) F   [EEXDX]  Later' -> (cite, kind, cls, flags)."""
    m = FLAGS_RE.search(line)
    flags = m.group(1) if m else "XXXXX"
    left = line[: m.start()].rstrip() if m else line.rstrip()
    m2 = re.match(
        r"^(.*?)\s*\b(N|V|VPAR|ADJ|ADV|PREP|CONJ|PRON|NUM|INTERJ|PACK)\b\s*(.*)$",
        left)
    if not m2:
        return left, "", "", flags
    cite, pos, tail = m2.group(1).strip(" ,"), m2.group(2), m2.group(3).split()
    kind = POS_KIND.get(pos, "")
    cls = ""
    ordn = next((ORDINAL[t] for t in tail if t in ORDINAL), None)
    gend = next((GENDS[t] for t in tail if t in GENDS), None)
    if pos == "N":
        cls = " · ".join(
            b for b in (gend and f"{gend}", ordn and f"{ordn} declension") if b)
    elif pos == "V":
        cls = f"{ordn} conjugation" if ordn else "verb"
        if "DEP" in tail:
            cls += " · deponent"
        if "IMPERS" in tail:
            cls += " · impersonal"
    elif pos == "ADJ":
        cls = "adjective"
    elif pos == "PREP":
        cls = "preposition with the " + \
            ("ablative" if "ABL" in tail else "accusative")
    else:
        cls = kind
    return cite, kind, cls, flags


def parse_block(lines):
    """One word's output block -> ordered candidate entries.

    Words prints, per candidate lemma: its inflection lines, then a
    dictionary line (with [FLAGS]), then meaning lines. Spelling variants of
    one lemma share the inflection lines above the group, and the group's
    meaning is printed once, after its last variant — hence the pending
    buffer and the backfill of empty senses below. The pronoun packons print
    later groups with no dictionary line at all, hence the synthesized
    citation-less candidates.
    """
    entries, pending, senses, cur = [], [], [], None
    last_pos = ""

    def finalize():
        nonlocal cur, senses
        if cur:
            cur["d"] = " ".join(senses).strip()
            cur["p"] = list(pending)
            entries.append(cur)
        cur, senses = None, []

    for raw in lines:
        line = raw.rstrip()
        if not line or line == "=>":
            continue
        if line.startswith("=>"):
            line = line[2:].strip()
            if not line:
                continue
        if "========" in line and "UNKNOWN" in line:
            continue
        # dictionary lines first: a one-word citation ("propter  PREP ...")
        # also matches the inflection shape, but only dictionary lines carry
        # the [FLAGS] bracket
        if FLAGS_RE.search(line) or re.match(r"^\S.*\s(N|V|ADJ)\s+\(\d", line):
            finalize()                 # keeps pending: variants share it
            cite, kind, cls, flags = parse_dict_line(line)
            if "abb." in cite:         # Roman abbreviation entries are noise
                cur = None
                continue
            cur = {"l": cite, "k": kind, "c": cls, "_f": flags}
            continue
        m = INFL_RE.match(line)
        if m:
            if cur:                    # a new group starts: close the old one
                finalize()
                pending.clear()
            last_pos = m.group(2)
            p = parse_infl(m.group(2), m.group(3))
            if p and p not in pending:
                pending.append(p)
            continue
        if cur is None and pending:
            kind = POS_KIND.get(last_pos, "")
            cur = {"l": "", "k": kind, "c": kind, "_f": "XXXAX"}
        if cur is not None:
            senses.append(line)
    finalize()
    # a variant group's meaning sits on its last member: backfill the others
    for i in range(len(entries) - 2, -1, -1):
        if not entries[i]["d"]:
            entries[i]["d"] = entries[i + 1]["d"]
    # trim senses to the first three sweeps of the semicolon
    for e in entries:
        e["d"] = "; ".join(s.strip() for s in e["d"].split(";")[:3]).rstrip(";")
        e["p"] = merge_parses(e["p"])
    entries.sort(key=lambda e: FREQ_RANK.get(e["_f"][3], 9))
    for e in entries:
        del e["_f"]
    # collapse duplicate lemmas (Words often lists spelling variants); the
    # citation-less packon candidates all share an empty head and must stay
    seen, out = set(), []
    for e in entries:
        head = normalize(e["l"].split(",")[0].lower())
        if head and head in seen:
            continue
        seen.add(head)
        out.append(e)
    return out


def run_words(queries):
    """Feed queries through the Docker image, sentinel-delimited.

    File mode (bin/words IN OUT) matters: it disables the screen pager,
    whose "MORE - hit RETURN" prompt would otherwise eat input lines.
    """
    with tempfile.TemporaryDirectory() as td:
        feed = SENTINEL + "\n" + \
            "".join(q + "\n" + SENTINEL + "\n" for q in queries)
        open(os.path.join(td, "in.txt"), "w").write(feed)
        subprocess.run(
            ["docker", "run", "--rm", "-v", f"{td}:/io", "whitakers", "sh",
             "-c", "cd /w && bin/words /io/in.txt /io/out.txt"],
            capture_output=True, check=True)
        out = open(os.path.join(td, "out.txt"), errors="replace").read()
    blocks, cur = [], None
    for line in out.splitlines():
        if SENTINEL in line:
            if cur is not None:
                blocks.append(cur)
            cur = []
        elif cur is not None:
            cur.append(line)
    if len(blocks) != len(queries):
        sys.exit(f"block count {len(blocks)} != query count {len(queries)}")
    return blocks


# ---------- corpus + overlays ----------

def kind_of_class(c):
    """Part of speech for the card chip, from a curated class string."""
    lc = c.lower()
    if "conjugation" in lc or lc in ("irregular", "defective"):
        return "verb"
    if any(g in lc for g in ("masculine", "feminine", "neuter", "common")):
        return "noun"
    if "declension" in lc or lc in ("comparative", "possessive"):
        return "adjective"
    if lc in ("relative", "personal", "reflexive", "interrogative",
              "pronoun", "demonstrative"):
        return "pronoun"
    for w in ("preposition", "conjunction", "adverb", "interjection",
              "numeral"):
        if w in lc:
            return w
    if "indeclinable" in lc:
        return "noun"
    return ""


def corpus_freq():
    freq = collections.Counter()
    base = os.path.join(ROOT, "public/bible")
    for slug in os.listdir(base):
        p = os.path.join(base, slug)
        if not os.path.isdir(p):
            continue
        for f in os.listdir(p):
            if not re.fullmatch(r"\d+\.json", f):
                continue
            d = json.load(open(os.path.join(p, f)))
            for v in d["verses"]:
                for latin, _ in v["pairs"]:
                    for w in latin.split():
                        k = form_key(w)
                        if k:
                            freq[k] += 1
    return freq


def main():
    with_curated = "--with-curated" in sys.argv

    freq = corpus_freq()
    forms = sorted(freq)
    print(f"{len(forms):,} distinct forms over {sum(freq.values()):,} tokens")

    blocks = run_words([normalize(f) for f in forms])

    custom = json.load(open(os.path.join(ROOT, "docs/dict/custom-vocabulary.json")))
    reg = json.load(open(os.path.join(ROOT, "docs/gloss/lemmas.json"))) \
        if with_curated else {"forms": {}, "lemmas": {}}

    shards = [dict() for _ in range(SHARDS)]
    known = unknown = 0
    for f, block in zip(forms, blocks):
        entries = parse_block(block)
        if f in custom["forms"]:
            cf = custom["forms"][f]
            lem = custom["lemmas"][cf["l"]]
            entries = [{"l": cf["l"], "k": kind_of_class(lem["c"]),
                        "c": lem["c"], "d": lem["d"], "p": [cf["p"]]}] + entries
        if with_curated and f in reg["forms"]:
            heads = set()
            curated = []
            for c in reg["forms"][f]:
                heads.add(normalize(c.split(",")[0].lower()))
                curated.append({"l": c, "k": kind_of_class(reg["lemmas"][c]["c"]),
                                "c": reg["lemmas"][c]["c"],
                                "d": reg["lemmas"][c]["d"], "src": "curated"})
            match = next((e for e in entries if not e["l"] or
                          normalize(e["l"].split(",")[0].lower()) in heads),
                         None)
            if match:
                pool = [match] if match["l"] else \
                    [e for e in entries if not e["l"]]
                ps = []
                for e in pool:
                    ps += [p for p in e["p"] if p not in ps]
                for c in curated:
                    c["p"] = merge_parses(ps)
                extra = [e for e in entries if e["l"] and
                         normalize(e["l"].split(",")[0].lower()) not in heads]
            else:
                extra = []
            entries = curated + extra
        if not entries:
            unknown += 1
            continue
        known += 1
        shards[shard_of(f)][f] = {"n": freq[f], "e": entries}

    dest = os.path.join(ROOT, "public/dict")
    os.makedirs(dest, exist_ok=True)
    for f in os.listdir(dest):
        os.remove(os.path.join(dest, f))
    total = 0
    for i, shard in enumerate(shards):
        path = os.path.join(dest, f"s{i}.json")
        json.dump(shard, open(path, "w"), ensure_ascii=False,
                  separators=(",", ":"))
        total += os.path.getsize(path)
    json.dump({"shards": SHARDS, "forms": known, "curated": with_curated},
              open(os.path.join(dest, "index.json"), "w"))
    print(f"wrote {SHARDS} shards to public/dict/: {known:,} forms with "
          f"entries, {unknown:,} unknown, {total // 1024:,} KB total"
          f"{' (curated overlay ON)' if with_curated else ''}")


if __name__ == "__main__":
    main()
