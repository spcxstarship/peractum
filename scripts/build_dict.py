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
    last_pron = None

    def finalize():
        nonlocal cur, senses
        if cur:
            cur["d"] = " ".join(senses).strip()
            cur["p"] = list(pending)
            if cur["k"] == "pronoun" and last_pron:
                cur["_pm"] = last_pron
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
            if not kind:               # citation-less pronoun dictionary
                kind = POS_KIND.get(last_pos, "")   # lines carry no POS token
                cls = cls or kind
            cur = {"l": cite, "k": kind, "c": cls, "_f": flags}
            continue
        m = INFL_RE.match(line)
        if m:
            if cur:                    # a new group starts: close the old one
                finalize()
                pending.clear()
            last_pos = m.group(2)
            if m.group(2) in ("PRON", "PACK"):
                ct = m.group(3).split()
                if len(ct) >= 2 and ct[0].isdigit():
                    last_pron = (ct[0], ct[1], m.group(1).split(".")[0].lower())
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



# ---------- declension tables from Words' own stem + endings data ----------
#
# INFLECTS.LAT is the endings table Words recognizes forms WITH; DICTLINE.GEN
# carries each lemma's stems and its declension/variant codes (the variant is
# where i-stems and the other third-declension facts live). Running them
# forward instead of backward yields the full paradigm at the analyzer's own
# accuracy. Nouns and adjectives only: a verb's conjugation is mood-by-mood
# and stays a curated-tier feature for now.

TABLE_CASES = ["Nom", "Gen", "Dat", "Acc", "Abl"]
CASE_CODE = {"Nom": "NOM", "Gen": "GEN", "Dat": "DAT", "Acc": "ACC",
             "Abl": "ABL"}
INFLECT_FREQ = {"A": 0, "B": 1, "C": 2, "D": 3, "E": 4, "F": 5, "X": 1}


def load_inflects():
    """(pos, decl, var, case, num, gender[, degree]) -> [(rank, stem#, ending)]."""
    rows = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, ".cache/whitakers/INFLECTS.LAT")):
        line = line.split("--")[0].rstrip()
        t = line.split()
        if not t or t[0] not in ("N", "ADJ", "PRON"):
            continue
        if t[0] in ("N", "PRON"):
            pos, decl, var, case, num, gend = t[0], t[1], t[2], t[3], t[4], t[5]
            rest = t[6:]
            key_extra = ()
        else:
            pos, decl, var, case, num, gend, deg = \
                t[0], t[1], t[2], t[3], t[4], t[5], t[6]
            if deg != "POS":
                continue
            rest = t[7:]
            key_extra = ()
        stem_no, size = int(rest[0]), int(rest[1])
        ending = rest[2] if size > 0 else ""
        age, fr = rest[-2], rest[-1]
        if age not in ("X", "A", "B"):
            continue
        rank = (INFLECT_FREQ.get(fr, 9), 0 if var != "0" else 1)
        rows[(pos, decl, var, case, num, gend)].append((rank, stem_no, ending))
    return rows


def load_dictline(inflects):
    """Headword index: (pos, nominative headword, decl[, gender]) -> entries.

    The headword is GENERATED (stem + nominative ending) because DICTLINE
    stores bare stems: superbia is filed under 'superbi'."""
    idx = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, ".cache/whitakers/DICTLINE.GEN"),
                     errors="replace"):
        stems = [line[i:i + 19].strip() for i in (0, 19, 38, 57)]
        t = line[76:].split()
        if not t:
            continue
        if t[0] == "N" and len(t) >= 4:
            decl, var, gend = t[1], t[2], t[3]
            got = pick_ending(inflects, "N", decl, var, "NOM", "S", gend)
            if got is None:
                continue
            _, stem_no, ending = got
            stem = stems[stem_no - 1]
            if not stem or stem == "zzz":
                continue
            head = (stem + ending).lower()
            idx[("N", head, decl, gend)].append((decl, var, gend, stems))
        elif t[0] == "ADJ" and len(t) >= 4 and t[3] in ("POS", "X"):
            decl, var = t[1], t[2]
            got = pick_ending(inflects, "ADJ", decl, var, "NOM", "S", "M")
            if got is None:
                continue
            _, stem_no, ending = got
            stem = stems[stem_no - 1]
            if not stem or stem == "zzz":
                continue
            head = (stem + ending).lower()
            idx[("ADJ", head, decl)].append((decl, var, "", stems))
    return idx


def pick_ending(inflects, pos, decl, var, case, num, gend):
    """Best ending for one paradigm slot, wildcarding variant and gender."""
    cands = []
    for v in (var, "0"):
        for g in (gend, "C", "X"):
            cands += inflects.get((pos, decl, v, case, num, g), [])
    if not cands:
        return None
    return min(cands)


def slot_form(inflects, pos, decl, var, gend, stems, case, num):
    got = pick_ending(inflects, pos, decl, var, CASE_CODE[case], num, gend)
    if got is None:
        return None
    _, stem_no, ending = got
    stem = stems[stem_no - 1]
    if not stem or stem == "zzz":
        return None
    return stem + ending


def ligature(w):
    """Classical -> the app's Clementine display (ligatures only; the j/i
    difference is left alone rather than guessed)."""
    return w.replace("ae", "æ").replace("oe", "œ")


GENDER_WORD = {"masculine": "M", "feminine": "F", "neuter": "N", "common": "C"}
ROMAN_DECL = {"I": "1", "II": "2", "III": "3", "IV": "4", "V": "5"}


def noun_table(entry, dictline, inflects, nfreq):
    """A GlossTable-shaped declension for a noun candidate, or None."""
    head = normalize(entry["l"].split(",")[0].lower())
    gw = next((g for g in GENDER_WORD if g in entry["c"]), None)
    rn = next((ROMAN_DECL[r]
               for r in sorted(ROMAN_DECL, key=len, reverse=True)
               if f"{r} declension" in entry["c"]), None)
    if not head or not gw or not rn:
        return None
    hits = dictline.get(("N", head, rn, GENDER_WORD[gw]), [])
    if not hits:
        for g2 in ("C", "M", "F", "N", "X"):
            hits = dictline.get(("N", head, rn, g2), [])
            if hits:
                break
    variants = {(h[0], h[1]) for h in hits}
    if len(variants) != 1:
        return None                      # unknown or ambiguous paradigm
    decl, var, _, stems = hits[0]
    rows = []
    for case in TABLE_CASES:
        cells = []
        for num in ("S", "P"):
            f = slot_form(inflects, "N", decl, var, GENDER_WORD[gw], stems,
                          case, num)
            cells.append([ligature(f), nfreq.get(f, 0)] if f else None)
        if cells[0] is None and cells[1] is None:
            return None
        rows.append([case, cells[0], cells[1]])
    return {"l": entry["l"], "c": entry["c"], "rows": rows}


def adj_table(entry, dictline, inflects, nfreq):
    """A gender-chipped declension for an adjective candidate, or None."""
    head = normalize(entry["l"].split(",")[0].lower())
    hits = []
    for decl in ("1", "2", "3"):
        hits += dictline.get(("ADJ", head, decl), [])
    variants = {(h[0], h[1]) for h in hits}
    if len(variants) != 1:
        return None
    decl, var, _, stems = hits[0]
    chips = []
    for chip, g in (("masc", "M"), ("fem", "F"), ("neut", "N")):
        rows = []
        for case in TABLE_CASES:
            cells = []
            for num in ("S", "P"):
                f = slot_form(inflects, "ADJ", decl, var, g, stems, case, num)
                cells.append([ligature(f), nfreq.get(f, 0)] if f else None)
            rows.append([case, cells[0], cells[1]])
        if all(r[1] is None and r[2] is None for r in rows):
            return None
        chips.append([chip, rows])
    return {"l": entry["l"], "c": entry["c"], "g": chips}




def load_dictline_p():
    """Analyzed stem -> the PRON entries holding it (each with both stems)."""
    idx = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, ".cache/whitakers/DICTLINE.GEN"),
                     errors="replace"):
        stems = [line[i:i + 19].strip() for i in (0, 19)]
        stems = ["" if s in (".", "zzz") else s for s in stems]
        t = line[76:].split()
        if not t or t[0] != "PRON" or len(t) < 4:
            continue
        decl, var = t[1], t[2]
        for s in set(stems):
            if s:
                idx[s.lower()].append((decl, var, stems))
    return idx


# The personals pair suppletively (ego with nos, tu with vos) — separate
# lemmas in Words' data, one paradigm to a learner. Hand-pinned like the
# curated tier's PERSONAL_BLOCKS.
PERS_HAND = {
    ("5", "1"): ("ego", [["Nom", "ego", "nos"], ["Gen", "mei", "nostri"],
                         ["Dat", "mihi", "nobis"], ["Acc", "me", "nos"],
                         ["Abl", "me", "nobis"]]),
    ("5", "2"): ("tu", [["Nom", "tu", "vos"], ["Gen", "tui", "vestri"],
                        ["Dat", "tibi", "vobis"], ["Acc", "te", "vos"],
                        ["Abl", "te", "vobis"]]),
    ("5", "4"): ("sui", [["Nom", None, None], ["Gen", "sui", "sui"],
                         ["Dat", "sibi", "sibi"], ["Acc", "se", "se"],
                         ["Abl", "se", "se"]]),
}

QUI_HAND = {
    "masc": [["Nom", "qui", "qui"], ["Gen", "cujus", "quorum"],
             ["Dat", "cui", "quibus"], ["Acc", "quem", "quos"],
             ["Abl", "quo", "quibus"]],
    "fem": [["Nom", "quæ", "quæ"], ["Gen", "cujus", "quarum"],
            ["Dat", "cui", "quibus"], ["Acc", "quam", "quas"],
            ["Abl", "qua", "quibus"]],
    "neut": [["Nom", "quod", "quæ"], ["Gen", "cujus", "quorum"],
             ["Dat", "cui", "quibus"], ["Acc", "quod", "quæ"],
             ["Abl", "quo", "quibus"]],
}


def pron_table(entry, dictline_p, inflects, nfreq):
    """A declension for a pronoun candidate, matched by its analyzed stem
    (pronoun analyses carry no citation). Gendered classes get chips; the
    genderless personals (ego, tu) collapse to one block."""
    pm = entry.get("_pm")
    if not pm:
        return None
    decl, var, stem = pm
    # the personals: ego/tu/sui by class, nos/vos (both 5 3) by stem
    pers_key = (decl, var) if (decl, var) != ("5", "3") else \
        (("5", "1") if stem.startswith("n") else ("5", "2"))
    if decl == "5" and pers_key in PERS_HAND:
        cite, rows = PERS_HAND[pers_key]
        return {"l": cite, "c": "pronoun",
                "rows": [[c,
                          s and [s, nfreq.get(normalize(s), 0)],
                          p and [p, nfreq.get(normalize(p), 0)]]
                         for c, s, p in rows]}
    hits = [(d, v, tuple(s)) for d, v, s in dictline_p.get(stem, [])
            if d == decl and v == var]
    if not hits or len(set(hits)) != 1:
        return None
    d, v, stems = hits[0]
    if stems[0] == "qu" and d == "1":
        chips = [[chip, [[c, [s, nfreq.get(normalize(s), 0)],
                          [p, nfreq.get(normalize(p), 0)]]
                         for c, s, p in rows]]
                 for chip, rows in QUI_HAND.items()]
        return {"l": "qui, quæ, quod", "c": "pronoun", "g": chips}
    def slot(case, num, g):
        got = pick_ending(inflects, "PRON", d, v, CASE_CODE[case], num, g)
        if got is None:              # the personals mark number X = both
            got = pick_ending(inflects, "PRON", d, v, CASE_CODE[case], "X", g)
        if got is None:
            return None
        _, stem_no, ending = got
        s = stems[stem_no - 1] if stem_no <= len(stems) else ""
        if not s and ending == "":
            return None
        f = s + ending
        return [ligature(f), nfreq.get(normalize(f), 0)] if f else None
    chips = []
    for chip, g in (("masc", "M"), ("fem", "F"), ("neut", "N")):
        rows = []
        for case in TABLE_CASES:
            rows.append([case, slot(case, "S", g), slot(case, "P", g)])
        # Words has no feminine ablative row for the ille/is class (it
        # cannot parse illa as an ablative); in these paradigms the
        # feminine ablative is spelled like its nominative
        if rows[4][1] is None and rows[0][1] is not None:
            rows[4][1] = rows[0][1]
        chips.append([chip, rows])
    if all(r[1] is None and r[2] is None for c in chips for r in c[1]):
        return None
    heads = []
    for c in chips:
        nom = c[1][0][1]
        if nom and nom[0] not in heads:
            heads.append(nom[0])
    cite = ", ".join(heads)
    if all(c[1] == chips[0][1] for c in chips[1:]):
        return {"l": cite, "c": "pronoun", "rows": chips[0][1]}
    return {"l": cite, "c": "pronoun", "g": chips}


# ---------- verb conjugation blocks ----------
#
# Finite blocks come straight from stems + INFLECTS rows (the perfect system
# is conjugation-blind: V 0 0 rows; even esse is generated, its compounds
# included). The one hand-written piece is the auxiliary of the periphrastic
# perfect passive — factus SUM/ES/EST — which is syntax, not an ending.

TENSE_WORD = [("future perfect", "FUTP"), ("pluperfect", "PLUP"),
              ("imperfect", "IMPF"), ("perfect", "PERF"),
              ("present", "PRES"), ("future", "FUT")]
AUX = {
    ("PERF", "IND"): ["sum", "es", "est", "sumus", "estis", "sunt"],
    ("PLUP", "IND"): ["eram", "eras", "erat", "eramus", "eratis", "erant"],
    ("FUTP", "IND"): ["ero", "eris", "erit", "erimus", "eritis", "erunt"],
    ("PERF", "SUB"): ["sim", "sis", "sit", "simus", "sitis", "sint"],
    ("PLUP", "SUB"): ["essem", "esses", "esset", "essemus", "essetis",
                      "essent"],
}
TENSE_LABEL = {"PRES": "present", "IMPF": "imperfect", "FUT": "future",
               "PERF": "perfect", "PLUP": "pluperfect",
               "FUTP": "future perfect"}


def load_inflects_v():
    """(conj, var, tense, voice, mood, person, num) -> [(rank, stem#, end)]."""
    rows = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, ".cache/whitakers/INFLECTS.LAT")):
        line = line.split("--")[0].rstrip()
        t = line.split()
        if not t or t[0] != "V" or len(t) < 10:
            continue
        conj, var, tense, voice, mood, pers, num = t[1:8]
        if mood not in ("IND", "SUB"):
            continue
        rest = t[8:]
        stem_no, size = int(rest[0]), int(rest[1])
        ending = rest[2] if size > 0 else ""
        age, fr = rest[-2], rest[-1]
        if age not in ("X", "A", "B"):
            continue
        rank = (INFLECT_FREQ.get(fr, 9), 0 if var != "0" else 1,
                0 if conj != "0" else 1)
        rows[(conj, var, tense, voice, mood, pers, num)].append(
            (rank, stem_no, ending))
    return rows


def load_dictline_v(inflects_v):
    """('V', generated first principal part) -> [(conj, var, kind, stems)]."""
    idx = collections.defaultdict(list)
    for line in open(os.path.join(ROOT, ".cache/whitakers/DICTLINE.GEN"),
                     errors="replace"):
        stems = [line[i:i + 19].strip() for i in (0, 19, 38, 57)]
        stems = ["" if s in (".", "zzz") else s for s in stems]
        t = line[76:].split()
        if not t or t[0] != "V" or len(t) < 4:
            continue
        conj, var, kind = t[1], t[2], t[3]
        dep = kind in ("DEP", "SEMIDEP")
        voice = "PASSIVE" if dep else "ACTIVE"
        got = pick_v(inflects_v, conj, var, "PRES", voice, "IND", "1", "S")
        if got is None:
            continue
        _, stem_no, ending = got
        if not stems[stem_no - 1] and stem_no != 2:
            continue
        head = (stems[stem_no - 1] + ending).lower()
        if not head:
            continue
        idx[("V", head)].append((conj, var, kind, stems))
    # esse itself lives in Words' UNIQUES file, not DICTLINE; one synthetic
    # entry gives est/erat/fuit their table like every other verb
    idx[("V", "sum")] = [("5", "1", "TO_BEING", ["s", "", "fu", "fut"])]
    return idx


def pick_v(rows, conj, var, tense, voice, mood, pers, num):
    cands = []
    for c in (conj, "0"):
        for v in (var, "0"):
            cands += rows.get((c, v, tense, voice, mood, pers, num), [])
    return min(cands) if cands else None


def parse_to_block(p):
    """'imperfect subjunctive, third plural' -> (tense, voice, mood) or the
    periphrastic marker for a perfect participle."""
    if "perfect participle" in p:
        return ("PERF", "PASSIVE", "IND")
    if any(w in p for w in ("infinitive", "imperative", "participle",
                            "supine", "gerund")):
        return None
    tense = next((code for word, code in TENSE_WORD if word in p), None)
    if tense is None:
        return None
    return (tense, "PASSIVE" if "passive" in p else "ACTIVE",
            "SUB" if "subjunctive" in p else "IND")


def verb_table(entry, dictline_v, inflects_v, nfreq, bigram):
    """One conjugation block for a verb candidate: the block of its own
    parse, matching the curated card's behavior."""
    head = normalize(entry["l"].split(",")[0].lower())
    hits = dictline_v.get(("V", head), [])
    variants = {(h[0], h[1], h[2]) for h in hits}
    if len(variants) != 1:
        return None
    conj, var, kind, stems = hits[0]
    dep = kind in ("DEP", "SEMIDEP")
    block = next((b for b in map(parse_to_block, entry.get("p", [])) if b),
                 None)
    if block is None:
        return None
    tense, voice, mood = block
    # a deponent's forms are passive throughout, whatever the parse says
    # (Words leaves the voice column blank on deponent analyses)
    if dep:
        voice = "PASSIVE"
    label = ("indicative" if mood == "IND" else "subjunctive") + " · " +         TENSE_LABEL[tense] +         (" passive" if voice == "PASSIVE" and not dep else "")
    if voice == "PASSIVE" and tense in ("PERF", "PLUP", "FUTP"):
        # periphrastic: participle (stem 4) + the auxiliary, gender-chipped
        if not stems[3] or (tense, mood) not in AUX:
            return None
        aux = AUX[(tense, mood)]
        chips = []
        for chip, sg_e, pl_e in (("masc", "us", "i"), ("fem", "a", "ae"),
                                 ("neut", "um", "a")):
            rows = []
            for i, lab in enumerate(("1st", "2nd", "3rd")):
                sg = f"{stems[3]}{sg_e} {aux[i]}"
                pl = f"{stems[3]}{pl_e} {aux[i + 3]}"
                rows.append([lab,
                             [ligature(sg), bigram.get(sg, 0)],
                             [ligature(pl), bigram.get(pl, 0)]])
            chips.append([chip, rows])
        return {"l": entry["l"], "c": label, "g": chips}
    rows = []
    for i, lab in enumerate(("1st", "2nd", "3rd")):
        cells = []
        for num in ("S", "P"):
            got = pick_v(inflects_v, conj, var, tense, voice, mood,
                         str(i + 1), num)
            if got is None:
                cells.append(None)
                continue
            _, stem_no, ending = got
            stem = stems[stem_no - 1]
            if not stem and stem_no != 2:
                cells.append(None)
                continue
            f = stem + ending
            cells.append([ligature(f), nfreq.get(f, 0)])
        rows.append([lab, cells[0], cells[1]])
    if all(r[1] is None and r[2] is None for r in rows):
        return None
    return {"l": entry["l"], "c": label, "rows": rows}


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
    """Per-spelling counts, plus adjacent-pair counts for the two-word
    periphrastic cells (factum est)."""
    freq = collections.Counter()
    bigram = collections.Counter()
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
                    words = [form_key(w) for w in latin.split()]
                    words = [w for w in words if w]
                    freq.update(words)
                    for a, b in zip(words, words[1:]):
                        bigram[normalize(a) + " " + normalize(b)] += 1
    return freq, bigram


def main():
    with_curated = "--with-curated" in sys.argv

    freq, bigram = corpus_freq()
    forms = sorted(freq)
    print(f"{len(forms):,} distinct forms over {sum(freq.values()):,} tokens")

    blocks = run_words([normalize(f) for f in forms])

    custom = json.load(open(os.path.join(ROOT, "docs/dict/custom-vocabulary.json")))
    reg = json.load(open(os.path.join(ROOT, "docs/gloss/lemmas.json"))) \
        if with_curated else {"forms": {}, "lemmas": {}}

    inflects = load_inflects()
    dictline = load_dictline(inflects)
    inflects_v = load_inflects_v()
    dictline_v = load_dictline_v(inflects_v)
    dictline_p = load_dictline_p()
    nfreq = collections.defaultdict(int)
    for k, v in freq.items():
        nfreq[normalize(k)] += v
    table_cache = {}

    def table_for(entry):
        ck = (entry["k"], entry["l"], entry["c"], tuple(entry.get("p", [])),
              entry.get("_pm"))
        if ck not in table_cache:
            if entry["k"] == "noun":
                table_cache[ck] = noun_table(entry, dictline, inflects, nfreq)
            elif entry["k"] == "adjective":
                table_cache[ck] = adj_table(entry, dictline, inflects, nfreq)
            elif entry["k"] == "verb":
                table_cache[ck] = verb_table(entry, dictline_v, inflects_v,
                                             nfreq, bigram)
            elif entry["k"] == "pronoun":
                table_cache[ck] = pron_table(entry, dictline_p, inflects,
                                             nfreq)
            else:
                table_cache[ck] = None
        return table_cache[ck]

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
        for e in entries:
            t = table_for(e)
            if t:
                e["t"] = t
                if e["k"] == "pronoun" and not e["l"] and t.get("l"):
                    e["l"] = t["l"]     # the generated qui, quæ, quod line
            e.pop("_pm", None)
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
