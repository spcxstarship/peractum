# Compiles an LLM-authored gloss chapter (the intermediate format defined in
# docs/gloss-generation-prompt.md) into the .gloss.json the reader serves.
#
#   python3 scripts/compile_gloss.py path/to/genesis-2.intermediate.json
#   python3 scripts/compile_gloss.py path/to/... --out /tmp/check.gloss.json
#
# The model supplies only philology (per-token gloss/parse/citation and typed
# links); everything mechanical happens here: reconstruction and consistency
# checks, form deduplication with per-token parse overrides, corpus counts,
# paradigm tables, and expansion of link triples into the symmetric glow
# arrays and card relation lines. Anything doubtful is skipped with a warning
# rather than guessed — silence over error, per the tap-rules charter.
import argparse
import collections
import glob
import json
import os
import re
import sys

import lemma_registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

errors = []
warnings = []


def err(msg):
    errors.append(msg)


def warn(msg):
    warnings.append(msg)


def clean(tok):
    return re.sub(r"[^\wÆæŒœëï]+$", "", re.sub(r"^[^\wÆæŒœëï]+", "", tok)).lower()


def form_key(display):
    return " ".join(clean(w) for w in display.split(" "))


# ---------- corpus frequencies (identical to the Genesis 1 build) ----------
def corpus_counts():
    freq = collections.Counter()
    bigrams = collections.Counter()
    for f in glob.glob(f"{ROOT}/public/bible/*/*.json"):
        if f.endswith(".gloss.json"):
            continue
        d = json.load(open(f))
        for v in d["verses"]:
            toks = [clean(t) for la, _ in v["pairs"] for t in la.split()]
            toks = [t for t in toks if t]
            freq.update(toks)
            bigrams.update(zip(toks, toks[1:]))
    return freq, bigrams


# ---------- class normalization / part of speech ----------
def romanize(cls):
    for a, b in [
        ("first- and second-declension", "I-II declension"),
        ("third-declension", "III declension"),
        ("first declension", "I declension"),
        ("second declension", "II declension"),
        ("third declension", "III declension"),
        ("fourth declension", "IV declension"),
        ("fifth declension", "V declension"),
        ("first conjugation", "I conjugation"),
        ("second conjugation", "II conjugation"),
        ("third conjugation", "III conjugation"),
        ("fourth conjugation", "IV conjugation"),
    ]:
        cls = cls.replace(a, b)
    return cls


def attrs_of(cls):
    a = cls
    for pat, rep in [
        ("III declension adjective", "III declension"),
        ("I-II declension adjective", "I-II declension"),
        ("ordinal adjective", "ordinal"),
        ("possessive adjective", "possessive"),
        ("comparative adjective", "comparative"),
        ("numeral adjective", "numeral"),
        ("irregular verb", "irregular"),
        ("defective verb", "defective"),
        ("indeclinable noun", "indeclinable"),
        ("relative pronoun", "relative"),
        ("personal pronoun", "personal"),
        ("reflexive pronoun", "reflexive"),
        ("demonstrative pronoun", "demonstrative"),
    ]:
        a = a.replace(pat, rep)
    return a.replace(", ", " · ")


VERB_PARSE_WORDS = (
    "perfect", "imperfect", "pluperfect", "present", "future",
    "subjunctive", "imperative", "infinitive", "gerund", "supine",
)


def pos_of(cls, parse, cite):
    """Part of speech from the class string, falling back to the parse and
    citation for bare classes ('irregular', 'relative', 'possessive')."""
    c = cls.lower()
    if "adjective" in c or c in ("comparative", "ordinal", "possessive", "numeral"):
        return "adjective"
    if "pronoun" in c or c in ("relative", "personal", "reflexive", "demonstrative"):
        return "pronoun"
    # function words BEFORE the verb check: "verb" is a substring of "adverb"
    for w in ("preposition", "conjunction", "adverb", "interjection"):
        if w in c:
            return w
    if "conjugation" in c:
        return "verb"
    if "declension" in c:
        # nouns carry a gender word in the class; adjectives do not
        if any(g in c for g in ("masculine", "feminine", "neuter", "common")):
            return "noun"
        return "adjective"
    if "pronoun" in parse:
        return "pronoun"
    if "verb" in c or c in ("irregular", "defective") or any(
        w in parse for w in VERB_PARSE_WORDS
    ):
        return "verb"
    if "noun" in c or "noun" in parse or c == "indeclinable":
        return "noun"
    return ""


# ---------- noun paradigm tables (shared with the Genesis 1 build) ----------
CASES = ["Nom", "Gen", "Dat", "Acc", "Abl"]

# Citations that get no table (mixed or defective paradigms, or paradigms
# whose corpus counts are hopelessly contaminated by a homograph: the string
# "os" is almost always os, oris (mouth), so os, ossis gets no table until
# counting is lemma-aware).
NO_TABLE = {"vesper, vesperis, m.", "cetus, ceti, m.", "os, ossis, n.",
            # proper names of rivers: a real singular, no plural at all, and a
            # five-by-two table would have to invent the second column
            "Tigris, Tigridis, m.", "Euphrates, Euphratis, m."}

# Third-declension facts the citation cannot supply. A third-declension noun
# NOT listed here gets no table (a warning says so) — extend this dict rather
# than let the script guess i-stems and neuter plurals.
THIRD = {
    "avis": {"gp": "avium"},
    "congregatio": {"gp": "congregationum"},
    "homo": {"gp": "hominum"},
    "imago": {"gp": "imaginum"},
    "lux": {"gp": "lucum"},
    "nox": {"gp": "noctium"},
    "sementis": {"gp": "sementium"},
    "similitudo": {"gp": "similitudinum"},
    "volucris": {"gp": "volucrum"},
    "piscis": {"gp": "piscium"},
    "genus": {"gp": "generum", "npl": "genera"},
    "semen": {"gp": "seminum", "npl": "semina"},
    "tempus": {"gp": "temporum", "npl": "tempora"},
    "luminare": {"gp": "luminarium", "npl": "luminaria", "abl": "luminari"},
    "mare": {"gp": "marium", "npl": "maria", "abl": "mari"},
    "reptile": {"gp": "reptilium", "npl": "reptilia", "abl": "reptili"},
    # Genesis 2
    "opus": {"gp": "operum", "npl": "opera"},
    "generatio": {"gp": "generationum"},
    "regio": {"gp": "regionum"},
    "fons": {"gp": "fontium"},
    "voluptas": {"gp": "voluptatum"},
    "caput": {"gp": "capitum", "npl": "capita"},
    "nomen": {"gp": "nominum", "npl": "nomina"},
    "flumen": {"gp": "fluminum", "npl": "flumina"},
    "lapis": {"gp": "lapidum"},
    "mors": {"gp": "mortium"},
    "sopor": {"gp": "soporum"},
    "caro": {"gp": "carnium"},
    "mulier": {"gp": "mulierum"},
    "virago": {"gp": "viraginum"},
    "pater": {"gp": "patrum"},
    "mater": {"gp": "matrum"},
    "uxor": {"gp": "uxorum"},
    "adjutor": {"gp": "adjutorum"},
    # Genesis 3
    "serpens": {"gp": "serpentium"},
    "vox": {"gp": "vocum"},
    "pectus": {"gp": "pectorum", "npl": "pectora"},
    "perizoma": {"gp": "perizomatum", "npl": "perizomata"},
    "dolor": {"gp": "dolorum"},
    "labor": {"gp": "laborum"},
    "sudor": {"gp": "sudorum"},
    "potestas": {"gp": "potestatum"},
    "panis": {"gp": "panum"},
    "pulvis": {"gp": "pulverum"},
    # Genesis 4
    "frater": {"gp": "fratrum"},
    "pastor": {"gp": "pastorum"},
    "ovis": {"gp": "ovium"},
    "munus": {"gp": "munerum", "npl": "munera"},
    "grex": {"gp": "gregum"},
    "adeps": {"gp": "adipum"},
    "foris": {"gp": "forium"},
    "custos": {"gp": "custodum"},
    "sanguis": {"gp": "sanguinum"},
    "iniquitas": {"gp": "iniquitatum"},
    "civitas": {"gp": "civitatum"},
    "malleator": {"gp": "malleatorum"},
    "soror": {"gp": "sororum"},
    "sermo": {"gp": "sermonum"},
    "vulnus": {"gp": "vulnerum", "npl": "vulnera"},
    "livor": {"gp": "livorum"},
    "ultio": {"gp": "ultionum"},
    "æs": {"gp": "ærum", "npl": "æra"},
    "os, oris, n.": {"gp": "orum", "npl": "ora"},
    # Genesis 6
    "gigas": {"gp": "gigantum"},
    "cogitatio": {"gp": "cogitationum"},
    "cor": {"gp": "cordium", "npl": "corda"},
    "finis": {"gp": "finium"},
    "bitumen": {"gp": "bituminum", "npl": "bitumina"},
    "summitas": {"gp": "summitatum"},
    "latus": {"gp": "laterum", "npl": "latera"},
    "fœdus": {"gp": "fœderum", "npl": "fœdera"},
    "longitudo": {"gp": "longitudinum"},
    "latitudo": {"gp": "latitudinum"},
    "altitudo": {"gp": "altitudinum"},
    # Genesis 1
    "animans": {"gp": "animantium"},
}

# Fully irregular tables.
IRREGULAR_TABLES = {
    "deus": [["Deus", "dii"], ["Dei", "deorum"], ["Deo", "diis"],
             ["Deum", "deos"], ["Deo", "diis"]],
    # heteroclites: neuter singular, masculine/neuter plural as the Vulgate uses
    "cælum": [["cælum", "cæli"], ["cæli", "cælorum"], ["cælo", "cælis"],
              ["cælum", "cælos"], ["cælo", "cælis"]],
    "locus": [["locus", "loca"], ["loci", "locorum"], ["loco", "locis"],
              ["locum", "loca"], ["loco", "locis"]],
    # dea/filia-type -abus dative/ablative plural (animis belongs to animus)
    "anima": [["anima", "animæ"], ["animæ", "animarum"], ["animæ", "animabus"],
              ["animam", "animas"], ["anima", "animabus"]],
}

# (table key, form) -> corrected count where the raw string count includes
# a different lexeme (maribus = mas; lucum/luci/lucis partly = lucus).
# Corpus counts, filled in by compile_chapter. Periphrastic cells ("factus
# est") are counted as pairs, not as words; FREQ also decides which of two
# legitimate spellings of a perfect the table should show.
BIGRAMS = collections.Counter()
# form -> lemmas that already own it, so enrichment never steals
# another word's spelling
CLAIMED_ELSEWHERE = {}
FREQ = collections.Counter()

COUNT_OVERRIDES = {
    ("mare", "maribus"): 0,
    ("lux", "lucum"): 0,
    ("lux", "luci"): 2,
    ("lux", "lucis"): 11,
}


def noun_table(cite, cls):
    """cite like 'terra, terræ, f.' -> [[sg, pl] x 5 cases] or None."""
    parts = [p.strip() for p in cite.split(",")]
    if len(parts) != 3:
        return None
    nom, gen = parts[0], parts[1]
    key = nom.lower()
    # the full citation wins where a nominative serves two lexemes
    if cite in IRREGULAR_TABLES or key in IRREGULAR_TABLES:
        return IRREGULAR_TABLES.get(cite) or IRREGULAR_TABLES[key]
    if gen.endswith("arum"):  # first declension, plural only (tenebræ)
        s = gen[:-4]
        return [[None, s + "æ"], [None, s + "arum"], [None, s + "is"],
                [None, s + "as"], [None, s + "is"]]
    if gen.endswith("æ"):  # first declension
        s = gen[:-1]
        return [[s + "a", s + "æ"], [s + "æ", s + "arum"], [s + "æ", s + "is"],
                [s + "am", s + "as"], [s + "a", s + "is"]]
    if gen.endswith("ei"):  # fifth declension
        s = gen[:-2]
        return [[s + "es", s + "es"], [s + "ei", s + "erum"], [s + "ei", s + "ebus"],
                [s + "em", s + "es"], [s + "e", s + "ebus"]]
    if gen.endswith("us") and not gen.endswith("ius"):  # fourth declension
        if "neuter" in cls:
            warn(f"no table for fourth-declension neuter {cite} (add by hand)")
            return None
        s = gen[:-2]
        return [[s + "us", s + "us"], [s + "us", s + "uum"], [s + "ui", s + "ibus"],
                [s + "um", s + "us"], [s + "u", s + "ibus"]]
    if gen.endswith("is"):  # third declension: only with hand-checked facts
        x = THIRD.get(cite) or THIRD.get(key)
        if x is None:
            warn(f"no table for third-declension {cite}: "
                 f"add '{key}' to THIRD (genitive plural, neuter plural, i-stem)")
            return None
        s = gen[:-2]
        gp = x.get("gp", s + "um")
        if "npl" in x:  # neuter
            npl = x["npl"]
            abl = x.get("abl", s + "e")
            return [[nom, npl], [s + "is", gp], [s + "i", s + "ibus"],
                    [nom, npl], [abl, s + "ibus"]]
        return [[nom, s + "es"], [s + "is", gp], [s + "i", s + "ibus"],
                [s + "em", s + "es"], [s + "e", s + "ibus"]]
    if gen.endswith("i"):  # second declension
        s = gen[:-1]
        if nom.endswith("um"):  # neuter
            return [[nom, s + "a"], [s + "i", s + "orum"], [s + "o", s + "is"],
                    [nom, s + "a"], [s + "o", s + "is"]]
        return [[nom, s + "i"], [s + "i", s + "orum"], [s + "o", s + "is"],
                [s + "um", s + "os"], [s + "o", s + "is"]]
    warn(f"unrecognized citation shape, no table: {cite}")
    return None


def ls_cite(cite, cls):
    """Lewis & Short style citation: clipped genitive ending per declension
    ('terra, æ, f.'; third declension keeps the full genitive, as L&S does)."""
    parts = [p.strip() for p in cite.split(",")]
    if len(parts) != 3:
        return cite
    nom, gen, g = parts
    m = re.search(r"\b(I-II|III|IV|V|II|I)\s+declension", cls)
    num = m.group(1) if m else ""
    if num == "I":
        end = "arum" if gen.endswith("arum") else "æ"
    elif num == "II":
        end = "ii" if gen.endswith("ii") else "i"
    elif num == "III":
        return f"{nom}, {gen}, {g}"
    elif num == "IV":
        end = "us"
    elif num == "V":
        end = "ei"
    else:
        return cite
    return f"{nom}, {end}, {g}"


def vocative_sg(nom, gen, cls):
    """The vocative only ever differs from the nominative in the second
    declension: -us takes -e, -ius takes -i. Everything else repeats the
    nominative, so it earns no row. Deus is its own vocative."""
    if "neuter" in cls or not gen.lower().endswith("i"):
        return None
    low = nom.lower()
    if low == "deus":
        return None
    if low.endswith("ius"):
        return nom[:-2]           # filius -> fili
    if low.endswith("us"):
        return nom[:-2] + "e"     # dominus -> domine
    return None


def cell(tkey, form, freq):
    """One table cell: the form and how often that spelling occurs."""
    if form is None:
        return None
    low = form.lower()
    if " " in low:  # periphrastic cell: "factus est" is a bigram, not a word
        return [form, BIGRAMS[tuple(low.split())]]
    return [form, COUNT_OVERRIDES.get((tkey, low), freq.get(low, 0))]


def make_rows(tkey, pairs, freq):
    """[(label, singular, plural)] -> the row shape the reader renders."""
    return [[lab, cell(tkey, sg, freq), cell(tkey, pl, freq)]
            for lab, sg, pl in pairs]


# Two lexemes can share a first word (os, ossis and os, oris; latus, lateris
# and latus, lata, latum). Table keys are per-chapter, so the first citation
# to claim a key keeps it and the next gets its genitive appended.
TKEY_OWNER = {}


def table_key(cite, base):
    owner = TKEY_OWNER.get(base)
    if owner is None or owner == cite:
        TKEY_OWNER[base] = cite
        return base
    parts = [q.strip() for q in cite.split(",")]
    alt = f"{base}~{clean(parts[1]) if len(parts) > 1 else '2'}"
    TKEY_OWNER.setdefault(alt, cite)
    return alt


def attested_table(cite, cls, known, freq):
    """What the Vulgate actually calls this name.

    Proper nouns do not obey one declension. Most Hebrew names in the Vulgate
    are indeclinable; the Greek ones decline in Greek (Euphraten, Tigrin,
    never Euphratem or Tigridem). Generating a paradigm from a citation
    therefore invents forms — so for a name we list the forms the text uses,
    with how often, and claim nothing else. The list comes from the lemma's
    own registered forms, so it grows as more of the Bible is glossed and it
    can never be wrong.
    """
    # Only forms this lemma has actually been glossed under. Guessing the
    # rest from a shared prefix was tried and abandoned: it grouped Salomon
    # with Salome, Ægyptus with the adjective Ægyptius, and Samaria with
    # Samaritana, while missing Israël over a diaeresis. A name's forms are
    # not recoverable by spelling, so the list stays short and true and fills
    # in as more of the Bible is glossed.
    ordered = sorted(set(known), key=lambda w: (-freq.get(w, 0), w))
    if not ordered:
        return None
    return {
        "l": cite,
        "c": cls,
        "h": ["In the Vulgate", ""],
        "rows": [[w, [w, freq.get(w, 0)], None] for w in ordered],
        "note": "A name, not a common noun. These are the forms glossed so "
                "far, with how often each spelling occurs in the Vulgate — "
                "not a declension.",
    }


def build_tables(forms, freq, lemma_forms=None):
    tables = {}
    lemma_forms = lemma_forms or {}
    for key, entry in forms.items():
        cls, cite, kind = entry["c"], entry["l"], entry["k"]
        if kind != "noun" or cite in NO_TABLE:
            continue
        # a name gets the forms the text uses; a common noun gets its paradigm
        if "indeclinable" in cls and cite[:1].isupper():
            t = attested_table(cite, cls, lemma_forms.get(cite, ()), freq)
            if t:
                tkey = table_key(cite, clean(cite.split(",")[0]) + "-name")
                tables.setdefault(tkey, t)
                entry["t"] = tkey
            continue
        if "declension" not in cls:
            continue
        rows = noun_table(cite, cls)
        if rows is None:
            continue
        tkey = table_key(cite, cite.split(",")[0].strip().lower())
        if tkey not in tables:
            parts = [p.strip() for p in cite.split(",")]
            labelled = list(zip(CASES, [r[0] for r in rows], [r[1] for r in rows]))
            voc = vocative_sg(parts[0], parts[1], cls) if len(parts) == 3 else None
            if voc:
                # plural vocative is the plural nominative, in every declension
                labelled.insert(4, ("Voc", voc, rows[0][1]))
            tables[tkey] = {
                "l": ls_cite(cite, cls),
                "c": cls,
                "rows": make_rows(tkey, labelled, freq),
            }
        entry["t"] = tkey
    return tables


# ---------- verb paradigm tables ----------
# The card shows the one block a word sits in, never the whole paradigm, so a
# block is three persons by singular/plural — the noun table's geometry with
# different labels. Block keys are "<mood>-<tense>-<voice>".
PERSONS = ("1st", "2nd", "3rd")
SIX = ("m", "s", "t", "mus", "tis", "nt")

# Perfect-system endings are conjugation-blind: they hang off the third
# principal part, so one set serves appellavit, vidit, fecit and dixit alike.
PERFECT_SYSTEM = {
    "ind-perf-act": ("indicative · perfect",
                     ("i", "isti", "it", "imus", "istis", "erunt")),
    "ind-plup-act": ("indicative · pluperfect",
                     ("eram", "eras", "erat", "eramus", "eratis", "erant")),
    "ind-futperf-act": ("indicative · future perfect",
                        ("ero", "eris", "erit", "erimus", "eritis", "erint")),
    "subj-perf-act": ("subjunctive · perfect",
                      ("erim", "eris", "erit", "erimus", "eritis", "erint")),
    "subj-plup-act": ("subjunctive · pluperfect",
                      ("issem", "isses", "isset", "issemus", "issetis", "issent")),
}

# The perfect passive (and every deponent perfect) is a participle plus sum:
# two words, and the participle agrees, so these blocks carry gender.
COMPOUND = {
    "ind-perf-pass": ("indicative · perfect passive",
                      ("sum", "es", "est", "sumus", "estis", "sunt")),
    "ind-plup-pass": ("indicative · pluperfect passive",
                      ("eram", "eras", "erat", "eramus", "eratis", "erant")),
    # maledictus eris (4:11), operatus fueris (4:12) — the fu- forms
    # (maledictus fuero) are the same tense written the other way round
    "ind-futperf-pass": ("indicative · future perfect passive",
                         ("ero", "eris", "erit", "erimus", "eritis", "erunt")),
    "subj-perf-pass": ("subjunctive · perfect passive",
                       ("sim", "sis", "sit", "simus", "sitis", "sint")),
    "subj-plup-pass": ("subjunctive · pluperfect passive",
                       ("essem", "esses", "esset", "essemus", "essetis", "essent")),
}
GENDER_ENDINGS = (("masc", "us", "i"), ("fem", "a", "æ"), ("neut", "um", "a"))

# Present-system endings, appended to the present stem. Passive is derived
# mechanically except where Latin refuses (the future throughout, and the
# third conjugation's second singular), which are spelled out.
PRESENT_SYSTEM = {
    "I": {
        "inf_act": "are",
        "drop": 1, "inf_pass": "ari", "ger": "and", "imp": ("a", "ate"),
        "imp_pass": ("are", "amini"),
        "ind-pres-act": ("o", "as", "at", "amus", "atis", "ant"),
        "ind-pres-pass": ("or", "aris", "atur", "amur", "amini", "antur"),
        "ind-impf-act": ("abam", "abas", "abat", "abamus", "abatis", "abant"),
        "ind-fut-act": ("abo", "abis", "abit", "abimus", "abitis", "abunt"),
        "ind-fut-pass": ("abor", "aberis", "abitur", "abimur", "abimini", "abuntur"),
        "subj-pres-act": ("em", "es", "et", "emus", "etis", "ent"),
    },
    "II": {
        "inf_act": "ere",
        "drop": 2, "inf_pass": "eri", "ger": "end", "imp": ("e", "ete"),
        "imp_pass": ("ere", "emini"),
        "ind-pres-act": ("eo", "es", "et", "emus", "etis", "ent"),
        "ind-pres-pass": ("eor", "eris", "etur", "emur", "emini", "entur"),
        "ind-impf-act": ("ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"),
        "ind-fut-act": ("ebo", "ebis", "ebit", "ebimus", "ebitis", "ebunt"),
        "ind-fut-pass": ("ebor", "eberis", "ebitur", "ebimur", "ebimini", "ebuntur"),
        "subj-pres-act": ("eam", "eas", "eat", "eamus", "eatis", "eant"),
    },
    "III": {
        "inf_act": "ere",
        "drop": 1, "inf_pass": "i", "ger": "end", "imp": ("e", "ite"),
        "imp_pass": ("ere", "imini"),
        "ind-pres-act": ("o", "is", "it", "imus", "itis", "unt"),
        "ind-pres-pass": ("or", "eris", "itur", "imur", "imini", "untur"),
        "ind-impf-act": ("ebam", "ebas", "ebat", "ebamus", "ebatis", "ebant"),
        "ind-fut-act": ("am", "es", "et", "emus", "etis", "ent"),
        "ind-fut-pass": ("ar", "eris", "etur", "emur", "emini", "entur"),
        "subj-pres-act": ("am", "as", "at", "amus", "atis", "ant"),
    },
    "III-io": {
        "inf_act": "ere",
        "drop": 2, "inf_pass": "i", "ger": "iend", "imp": ("e", "ite"),
        "imp_pass": ("ere", "imini"),
        "ind-pres-act": ("io", "is", "it", "imus", "itis", "iunt"),
        "ind-pres-pass": ("ior", "eris", "itur", "imur", "imini", "iuntur"),
        "ind-impf-act": ("iebam", "iebas", "iebat", "iebamus", "iebatis", "iebant"),
        "ind-fut-act": ("iam", "ies", "iet", "iemus", "ietis", "ient"),
        "ind-fut-pass": ("iar", "ieris", "ietur", "iemur", "iemini", "ientur"),
        "subj-pres-act": ("iam", "ias", "iat", "iamus", "iatis", "iant"),
    },
    "IV": {
        "inf_act": "ire",
        "drop": 2, "inf_pass": "iri", "ger": "iend", "imp": ("i", "ite"),
        "imp_pass": ("ire", "imini"),
        "ind-pres-act": ("io", "is", "it", "imus", "itis", "iunt"),
        "ind-pres-pass": ("ior", "iris", "itur", "imur", "imini", "iuntur"),
        "ind-impf-act": ("iebam", "iebas", "iebat", "iebamus", "iebatis", "iebant"),
        "ind-fut-act": ("iam", "ies", "iet", "iemus", "ietis", "ient"),
        "ind-fut-pass": ("iar", "ieris", "ietur", "iemur", "iemini", "ientur"),
        "subj-pres-act": ("iam", "ias", "iat", "iamus", "iatis", "iant"),
    },
}


def passivize(e):
    """Active personal ending -> passive. Covers everything except the future
    and the third-conjugation present, which PRESENT_SYSTEM spells out."""
    for suf, rep in (("mus", "mur"), ("tis", "mini"), ("nt", "ntur")):
        if e.endswith(suf):
            return e[: -len(suf)] + rep
    if e.endswith("t"):
        return e + "ur"
    if e.endswith("s"):
        return e[:-1] + "ris"
    if e.endswith("o"):
        return e + "r"
    if e.endswith("m"):
        return e[:-1] + "r"
    return e


def syncopate(pstem, ending):
    """A perfect stem in -v drops the -vi-/-ve- before s and r: amavisset ->
    amasset, amaverunt -> amarunt, obdormivisset -> obdormisset. Returns the
    shortened form, or None where the ending does not allow it (amavi,
    amavit, amavimus keep the v)."""
    if not pstem.endswith("v") or len(ending) < 2:
        return None
    if ending[0] in "ie" and ending[1] in "sr":
        return pstem[:-1] + ending[1:]
    return None


def attested(full, short):
    """Both spellings are correct Latin and the Vulgate uses both — it writes
    vocaverunt but audisset. Show whichever one it actually writes; where it
    writes neither, say so and let the caller follow the verb's own habit."""
    if short is None:
        return full, False
    n_full, n_short = FREQ[full.lower()], FREQ[short.lower()]
    if n_full == 0 and n_short == 0:
        return None, False
    return (short, True) if n_short > n_full else (full, False)


def perfect_block(label, pstem, ends):
    """A perfect-system block spelled the way the corpus spells it. Cells the
    Vulgate never writes follow whichever habit the attested cells establish,
    so one block never mixes obdormivissem with obdormisset."""
    resolved, shortened = [], []
    for e in ends:
        form, was_short = attested(pstem + e, syncopate(pstem, e))
        resolved.append((e, form))
        if was_short:
            shortened.append(form)
    prefer_short = bool(shortened)
    forms = []
    for e, form in resolved:
        if form is None:  # unattested either way: follow the verb's habit
            form = (syncopate(pstem, e) or pstem + e) if prefer_short else pstem + e
        forms.append(form)
    b = block(label, tuple(forms))
    if shortened:
        named = list(dict.fromkeys(shortened))
        s = "spelling" if len(named) == 1 else "spellings"
        b["note"] = (f"{', '.join(named)}: the shortened {s} the Vulgate uses "
                     f"here. The longer forms in -vi- are equally correct.")
    return b


def block(label, six):
    """Six forms in person order -> a three-row block."""
    return {"c": label,
            "pairs": [(PERSONS[i], six[i], six[i + 3]) for i in range(3)]}


def gendered(label, sup, aux):
    """Participle + auxiliary, one paradigm per gender."""
    return {"c": label, "g": [
        (chip, [(PERSONS[i], f"{sup}{sg} {aux[i]}", f"{sup}{pl} {aux[i + 3]}")
                for i in range(3)])
        for chip, sg, pl in GENDER_ENDINGS]}


# Verbs whose present system no rule produces. Compounds are derived from
# these by prefix (præsum from sum, affero from fero, circumeo from eo), so
# only the parent needs writing out.
def _sum_blocks():
    b = {
        "ind-pres-act": block("indicative · present",
                              ("sum", "es", "est", "sumus", "estis", "sunt")),
        "ind-impf-act": block("indicative · imperfect",
                              ("eram", "eras", "erat", "eramus", "eratis", "erant")),
        "ind-fut-act": block("indicative · future",
                             ("ero", "eris", "erit", "erimus", "eritis", "erunt")),
        "subj-pres-act": block("subjunctive · present",
                               ("sim", "sis", "sit", "simus", "sitis", "sint")),
        "subj-impf-act": block("subjunctive · imperfect",
                               ("essem", "esses", "esset", "essemus", "essetis", "essent")),
        "imp-pres-act": {"c": "imperative · present", "pairs": [("2nd", "es", "este")]},
        "inf": {"c": "infinitives", "h": ["Active", "Passive"],
                "pairs": [("Pres", "esse", None), ("Perf", "fuisse", None),
                          ("Fut", "futurum esse", None)]},
    }
    for bk, (lab, ends) in PERFECT_SYSTEM.items():
        b[bk] = block(lab, tuple("fu" + e for e in ends))
    return b


def _fero_blocks():
    b = {
        "ind-pres-act": block("indicative · present",
                              ("fero", "fers", "fert", "ferimus", "fertis", "ferunt")),
        "ind-pres-pass": block("indicative · present passive",
                               ("feror", "ferris", "fertur", "ferimur", "ferimini", "feruntur")),
        "ind-impf-act": block("indicative · imperfect",
                              tuple("fereba" + e for e in SIX)),
        "ind-impf-pass": block("indicative · imperfect passive",
                               tuple("fereba" + passivize(e) for e in SIX)),
        "ind-fut-act": block("indicative · future",
                             ("feram", "feres", "feret", "feremus", "feretis", "ferent")),
        "subj-pres-act": block("subjunctive · present",
                               ("feram", "feras", "ferat", "feramus", "feratis", "ferant")),
        "subj-impf-act": block("subjunctive · imperfect",
                               tuple("ferre" + e for e in SIX)),
        "imp-pres-act": {"c": "imperative · present", "pairs": [("2nd", "fer", "ferte")]},
    }
    for bk, (lab, ends) in PERFECT_SYSTEM.items():
        b[bk] = block(lab, tuple("tul" + e for e in ends))
    for bk, (lab, aux) in COMPOUND.items():
        b[bk] = gendered(lab, "lat", aux)
    return b


def _eo_blocks():
    b = {
        "ind-pres-act": block("indicative · present",
                              ("eo", "is", "it", "imus", "itis", "eunt")),
        "ind-impf-act": block("indicative · imperfect", tuple("iba" + e for e in SIX)),
        "ind-fut-act": block("indicative · future",
                             ("ibo", "ibis", "ibit", "ibimus", "ibitis", "ibunt")),
        "subj-pres-act": block("subjunctive · present", tuple("ea" + e for e in SIX)),
        "subj-impf-act": block("subjunctive · imperfect", tuple("ire" + e for e in SIX)),
        "imp-pres-act": {"c": "imperative · present", "pairs": [("2nd", "i", "ite")]},
    }
    for bk, (lab, ends) in PERFECT_SYSTEM.items():
        b[bk] = block(lab, tuple("i" + e for e in ends))
    return b


def _fio_blocks():
    b = {
        "ind-pres-act": block("indicative · present",
                              ("fio", "fis", "fit", "fimus", "fitis", "fiunt")),
        "ind-impf-act": block("indicative · imperfect", tuple("fieba" + e for e in SIX)),
        "ind-fut-act": block("indicative · future",
                             ("fiam", "fies", "fiet", "fiemus", "fietis", "fient")),
        "subj-pres-act": block("subjunctive · present", tuple("fia" + e for e in SIX)),
        "subj-impf-act": block("subjunctive · imperfect", tuple("fiere" + e for e in SIX)),
        "inf": {"c": "infinitives", "h": ["Active", "Passive"],
                "pairs": [("Pres", "fieri", None), ("Perf", "factum esse", None),
                          ("Fut", None, None)]},
    }
    # fio's perfect is factus sum: the compound, with an active meaning
    for bk, (lab, aux) in COMPOUND.items():
        b[bk.replace("-pass", "-act")] = gendered(lab.replace(" passive", ""),
                                                  "fact", aux)
    return b


def _possum_blocks():
    b = {
        "ind-pres-act": block("indicative · present",
                              ("possum", "potes", "potest", "possumus", "potestis", "possunt")),
        "ind-impf-act": block("indicative · imperfect", tuple("potera" + e for e in SIX)),
        "ind-fut-act": block("indicative · future",
                             ("potero", "poteris", "poterit", "poterimus", "poteritis", "poterunt")),
        "subj-pres-act": block("subjunctive · present",
                               ("possim", "possis", "possit", "possimus", "possitis", "possint")),
        "subj-impf-act": block("subjunctive · imperfect", tuple("posse" + e for e in SIX)),
    }
    for bk, (lab, ends) in PERFECT_SYSTEM.items():
        b[bk] = block(lab, tuple("potu" + e for e in ends))
    return b


def _perfect_only_blocks(pstem, inf):
    """A verb that exists only in the perfect system: cœpi, memini, odi.

    Everything hangs off the perfect stem, so the present-system half of the
    card is not missing by accident — there is nothing there to show.
    """
    out = {bk: block(lab, tuple(pstem + e for e in ends))
           for bk, (lab, ends) in PERFECT_SYSTEM.items()}
    out["inf"] = {"c": "infinitives", "h": ["Active", "Passive"], "pairs": [
        ("Pres", None, None), ("Perf", inf, None), ("Fut", None, None)]}
    return out


HAND_VERBS = {
    "cœpi, cœpisse": _perfect_only_blocks("cœp", "cœpisse"),
    "sum, esse, fui": _sum_blocks(),
    "fero, ferre, tuli, latus": _fero_blocks(),
    "eo, ire, ivi, itus": _eo_blocks(),
    "eo, ire, ii, itus": _eo_blocks(),
    "fio, fieri, factus sum": _fio_blocks(),
    "possum, posse, potui": _possum_blocks(),
    "aio": {"ind-pres-act": {"c": "indicative · present", "pairs": [
        ("1st", "aio", None), ("2nd", "ais", None), ("3rd", "ait", "aiunt")]}},
    "inquam": {"ind-pres-act": {"c": "indicative · present", "pairs": [
        ("1st", "inquam", None), ("2nd", "inquis", None),
        ("3rd", "inquit", "inquiunt")]}},
    # impersonal: third singular only, no plural to show
    "pœnitet, pœnitere, pœnituit": {
        "ind-pres-act": {"c": "indicative · present", "pairs": [
            ("1st", None, None), ("2nd", None, None),
            ("3rd", "pœnitet", None)]},
        "ind-perf-act": {"c": "indicative · perfect", "pairs": [
            ("1st", None, None), ("2nd", None, None),
            ("3rd", "pœnituit", None)]},
    },
}

# Compounds inherit their parent's forms: præsum from sum, affero from fero,
# circumeo from eo. Both principal parts must match, or every regular fourth
# conjugation verb in -ire (invenio, audio, custodio) would be read as a
# compound of eo.
COMPOUND_PARENTS = (
    ("sum", "esse", "sum, esse, fui"),
    ("fero", "ferre", "fero, ferre, tuli, latus"),
    ("eo", "ire", "eo, ire, ivi, itus"),
    ("fio", "fieri", "fio, fieri, factus sum"),
)


def prefixed(blocks, prefix):
    """A compound's blocks: the parent's forms with the prefix in front."""
    out = {}
    for bk, b in blocks.items():
        nb = {"c": b["c"]}
        if "h" in b:
            nb["h"] = b["h"]
        if "g" in b:
            nb["g"] = [(chip, [(lab, sg and prefix + sg, pl and prefix + pl)
                               for lab, sg, pl in pairs])
                       for chip, pairs in b["g"]]
        else:
            nb["pairs"] = [(lab, sg and prefix + sg, pl and prefix + pl)
                           for lab, sg, pl in b["pairs"]]
        out[bk] = nb
    return out


def conj_of(cls, p1, inf):
    """(endings key, present stem) for a regular verb, or (None, None)."""
    num = next((n for n in ("IV", "III", "II", "I")
                if f"{n} conjugation" in cls), None)
    if num is None:
        return None, None
    low = p1.lower()
    key = "III-io" if num == "III" and low.endswith(("io", "ior")) else num
    if "deponent" in cls:
        # A deponent has no active first principal part to cut, so the stem
        # comes off the passive infinitive: vesci -> vesc, oriri -> ori.
        tail = PRESENT_SYSTEM[key]["inf_pass"]
        if not inf.endswith(tail):
            return None, None
        return key, inf[: -len(tail)]
    return key, p1[: -PRESENT_SYSTEM[key]["drop"]]


def verb_blocks(cite, cls):
    """Every paradigm block for one verb, keyed by block name."""
    if cite in HAND_VERBS:
        return HAND_VERBS[cite]
    parts = [p.strip() for p in cite.split(",")]
    if len(parts) < 2:
        return {}
    inf = parts[1]
    for p1_tail, inf_tail, parent in COMPOUND_PARENTS:
        if (inf.endswith(inf_tail) and parts[0].endswith(p1_tail)
                and inf != inf_tail):
            return prefixed(HAND_VERBS[parent], parts[0][: -len(p1_tail)])
    key, stem = conj_of(cls, parts[0], inf)
    if key is None:
        return {}
    E = PRESENT_SYSTEM[key]
    dep = "deponent" in cls
    out = {}

    six = {bk: tuple(stem + e for e in E[bk])
           for bk in E if bk.startswith(("ind-", "subj-"))}
    six["ind-impf-pass"] = tuple(stem + passivize(e) for e in E["ind-impf-act"])
    six["subj-pres-pass"] = tuple(stem + passivize(e) for e in E["subj-pres-act"])
    # The imperfect subjunctive is built on the ACTIVE infinitive — which a
    # deponent does not have, so reconstruct it (operari -> operare + endings).
    act_inf = stem + E["inf_act"] if dep else inf
    six["subj-impf-act"] = tuple(act_inf + e for e in SIX)
    six["subj-impf-pass"] = tuple(act_inf + passivize(e) for e in SIX)

    # A deponent has passive forms and an active meaning: one paradigm, whose
    # active half does not exist. Label it so the card can say so.
    def label_for(bk):
        lab = {"ind": "indicative", "subj": "subjunctive"}[bk.split("-")[0]]
        tense = {"pres": "present", "impf": "imperfect", "fut": "future",
                 "perf": "perfect", "plup": "pluperfect",
                 "futperf": "future perfect"}[bk.split("-")[1]]
        suffix = " passive" if bk.endswith("-pass") and not dep else ""
        return f"{lab} · {tense}{suffix}"

    for bk, forms6 in six.items():
        if dep and bk.endswith("-act"):
            continue
        out[bk.replace("-pass", "-act") if dep else bk] = block(label_for(bk), forms6)

    # perfect system off the third principal part
    if len(parts) >= 3 and not dep and parts[2].endswith("i"):
        pstem = parts[2][:-1]
        for bk, (lab, ends) in PERFECT_SYSTEM.items():
            out[bk] = perfect_block(lab, pstem, ends)

    # supine stem: the compound tenses, the future infinitives, the gerundive
    sup = None
    if dep and len(parts) >= 3 and parts[2].lower().endswith(" sum"):
        sup = parts[2].split()[0][:-2]
    elif len(parts) >= 4 and parts[3].endswith("us"):
        sup = parts[3][:-2]
    if sup:
        for bk, (lab, aux) in COMPOUND.items():
            out[bk.replace("-pass", "-act") if dep else bk] = gendered(
                lab.replace(" passive", "") if dep else lab, sup, aux)

    out["imp-pres-act"] = {"c": "imperative · present", "pairs": [
        ("2nd", stem + E["imp"][0], stem + E["imp"][1])]}
    if not dep:
        out["imp-pres-pass"] = {"c": "imperative · present passive", "pairs": [
            ("2nd", stem + E["imp_pass"][0], stem + E["imp_pass"][1])]}

    pinf = None if dep else stem + E["inf_pass"]
    perf_inf = None
    if len(parts) >= 3 and not dep and parts[2].endswith("i"):
        ps = parts[2][:-1]
        perf_inf = attested(ps + "isse", syncopate(ps, "isse"))[0]
    out["inf"] = {"c": "infinitives", "h": ["Active", "Passive"], "pairs": [
        # a deponent's infinitive is passive in form, active in meaning, so it
        # belongs in the column a reader will look for it in
        ("Pres", inf, None if dep else pinf),
        ("Perf", perf_inf, (sup + "um esse") if sup else None),
        ("Fut", (sup + "urum esse") if sup else None,
         (sup + "um iri") if sup and not dep else None)]}

    g = stem + E["ger"]
    out["ger"] = {"c": "gerund", "h": ["Form", ""], "pairs": [
        ("Gen", g + "i", None), ("Dat", g + "o", None),
        ("Acc", g + "um", None), ("Abl", g + "o", None)]}
    return out


def verb_block_key(parse):
    """Which block a parsed form belongs in, or None for the forms that
    decline (participles) and the ones with no paradigm to show."""
    p = parse.lower()
    if "participle" in p or "supine" in p:
        return None
    if "gerund" in p:
        return "ger"
    if "infinitive" in p:
        return "inf"
    voice = "pass" if "passive" in p else "act"
    if "imperative" in p:
        return f"imp-pres-{voice}"
    mood = "subj" if "subjunctive" in p else "ind"
    # order matters: imperfect and pluperfect both contain "perfect"
    for name, tense in (("future perfect", "futperf"), ("pluperfect", "plup"),
                        ("imperfect", "impf"), ("perfect", "perf"),
                        ("present", "pres"), ("future", "fut")):
        if name in p:
            return f"{mood}-{tense}-{voice}"
    return None


def build_verb_tables(forms, tables, freq):
    cache = {}
    for key, entry in forms.items():
        if entry["k"] != "verb":
            continue
        cite, bk = entry["l"], verb_block_key(entry["p"])
        if not bk:
            continue
        if cite not in cache:
            cache[cite] = verb_blocks(cite, entry["c"])
            if not cache[cite]:
                warn(f"no conjugation tables for {cite!r} ({entry['c']}): "
                     f"add it to HAND_VERBS")
        b = cache[cite].get(bk)
        if b is None:
            continue
        tkey = table_key(cite, f"{clean(cite.split(',')[0])}-{bk}")
        if tkey not in tables:
            t = {"l": cite, "c": b["c"]}
            if "h" in b:
                t["h"] = b["h"]
            if "note" in b:
                t["note"] = b["note"]
            if "g" in b:
                t["g"] = [[chip, make_rows(tkey, pairs, freq)]
                          for chip, pairs in b["g"]]
            else:
                t["rows"] = make_rows(tkey, b["pairs"], freq)
            tables[tkey] = t
        entry["t"] = tkey


# ---------- gendered declension tables ----------
# Adjectives, participles and pronouns decline in three genders, which will
# not fit six columns in a 308px card. Gender becomes a chip instead, so the
# table underneath keeps the noun's five-by-two shape.
def _cases(paradigm):
    """[(sg, pl) per case] -> [(case label, sg, pl)]."""
    return [(CASES[i], sg, pl) for i, (sg, pl) in enumerate(paradigm)]


def i_ii_paradigm(stem, nom_m, pronominal=False):
    """bonus, bona, bonum — and the noster type, whose masculine nominative
    is not stem + -us, which is why it is passed in."""
    gen_sg, dat_sg = (stem + "ius", stem + "i") if pronominal else (None, None)
    m = [(nom_m, stem + "i"), (gen_sg or stem + "i", stem + "orum"),
         (dat_sg or stem + "o", stem + "is"), (stem + "um", stem + "os"),
         (stem + "o", stem + "is")]
    f = [(stem + "a", stem + "æ"), (gen_sg or stem + "æ", stem + "arum"),
         (dat_sg or stem + "æ", stem + "is"), (stem + "am", stem + "as"),
         (stem + "a", stem + "is")]
    n = [(stem + "um", stem + "a"), (gen_sg or stem + "i", stem + "orum"),
         (dat_sg or stem + "o", stem + "is"), (stem + "um", stem + "a"),
         (stem + "o", stem + "is")]
    return [("masc", _cases(m)), ("fem", _cases(f)), ("neut", _cases(n))]


def third_paradigm(stem, nom_mf, nom_n, abl, gp, npl):
    """One shape for every third-declension adjective: the one-, two- and
    three-termination types share every ending and differ only in the
    nominative singular, which is why it is a parameter."""
    mf = [(nom_mf, stem + "es"), (stem + "is", gp), (stem + "i", stem + "ibus"),
          (stem + "em", stem + "es"), (abl, stem + "ibus")]
    n = [(nom_n, npl), (stem + "is", gp), (stem + "i", stem + "ibus"),
         (nom_n, npl), (abl, stem + "ibus")]
    return [("m / f", _cases(mf)), ("n", _cases(n))]


# unus nauta: regular except for the genitive -ius and dative -i.
PRONOMINAL_ADJ = {"unus", "solus", "totus", "ullus", "nullus", "alter",
                  "uter", "neuter", "unusquisque"}

PARTICIPLE_NOM = {"I": "ans", "II": "ens", "III": "ens",
                  "III-io": "iens", "IV": "iens"}

# An irregular verb has no conjugation class to generate a participle from, so
# the compounds borrow the parent's: affero -> afferens. Only fero is listed —
# eo's participle is euntis in the oblique cases and would not survive this
# treatment.
IRREGULAR_PARTICIPLE = {("fero", "ferre"): "ferens"}


def participle_blocks(cite, cls, parse):
    parts = [p.strip() for p in cite.split(",")]
    if "perfect" in parse or "past participle" in parse:
        if len(parts) >= 4 and parts[3].endswith("us"):
            stem = parts[3][:-2]
            return i_ii_paradigm(stem, stem + "us")
        # a deponent has no fourth part: its participle is the third,
        # "egressus sum" -> egressus
        if len(parts) >= 3 and parts[2].lower().endswith(" sum"):
            first = parts[2].split()[0]
            if first.endswith("us"):
                return i_ii_paradigm(first[:-2], first)
        return None
    if len(parts) < 2:
        return None
    key, stem = conj_of(cls, parts[0], parts[1])
    if key is None:
        nom = None
        for (p1_tail, inf_tail), parent in IRREGULAR_PARTICIPLE.items():
            if (parts[0].endswith(p1_tail) and parts[1].endswith(inf_tail)
                    and parts[1] != inf_tail):
                nom = parts[0][: -len(p1_tail)] + parent
        if nom is None:
            return None
    else:
        nom = stem + PARTICIPLE_NOM[key]
    obl = nom[:-1] + "t"          # habens -> habent
    # participial ablative is -e; the genitive plural and neuter plural keep
    # the i-stem forms
    return third_paradigm(obl, nom, nom, obl + "e", obl + "ium", obl + "ia")


def adjective_blocks(cite, cls, parse):
    if "participle" in parse:
        return participle_blocks(cite, cls, parse)
    # the irregular numerals and pronominal adjectives are written out, not
    # generated: duo declines like nothing else in the language
    if cite in PRONOUN_BLOCKS:
        return [(chip, _cases(pairs)) for chip, pairs in PRONOUN_BLOCKS[cite]]
    parts = [p.strip() for p in cite.split(",")]
    if "comparative" in cls and len(parts) == 2:
        s = parts[0]              # melior, melius: not an i-stem
        return third_paradigm(s, parts[0], parts[1], s + "e", s + "um", s + "a")
    if len(parts) == 3:
        if parts[1].lower() in ("duæ", "tria"):
            return None           # duo and tres decline unlike anything else
        stem = parts[1][:-1]      # feminine minus -a: handles noster/nostra
        return i_ii_paradigm(stem, parts[0],
                             parts[0].lower() in PRONOMINAL_ADJ)
    if len(parts) == 2 and "III declension" in cls:
        if parts[1].endswith("is"):        # one-termination: felix, felicis
            stem = parts[1][:-2]
            nom_mf = nom_n = parts[0]
        else:                              # two-termination: omnis, omne
            stem = parts[1][:-1]
            nom_mf, nom_n = parts[0], parts[1]
        return third_paradigm(stem, nom_mf, nom_n,
                              stem + "i", stem + "ium", stem + "ia")
    return None


# Pronouns follow no rule; every grammar prints them individually.
PRONOUN_BLOCKS = {
    "qui, quæ, quod": [
        ("masc", [("qui", "qui"), ("cujus", "quorum"), ("cui", "quibus"),
                  ("quem", "quos"), ("quo", "quibus")]),
        ("fem", [("quæ", "quæ"), ("cujus", "quarum"), ("cui", "quibus"),
                 ("quam", "quas"), ("qua", "quibus")]),
        ("neut", [("quod", "quæ"), ("cujus", "quorum"), ("cui", "quibus"),
                  ("quod", "quæ"), ("quo", "quibus")]),
    ],
    "hic, hæc, hoc": [
        ("masc", [("hic", "hi"), ("hujus", "horum"), ("huic", "his"),
                  ("hunc", "hos"), ("hoc", "his")]),
        ("fem", [("hæc", "hæ"), ("hujus", "harum"), ("huic", "his"),
                 ("hanc", "has"), ("hac", "his")]),
        ("neut", [("hoc", "hæc"), ("hujus", "horum"), ("huic", "his"),
                  ("hoc", "hæc"), ("hoc", "his")]),
    ],
    "ille, illa, illud": [
        ("masc", [("ille", "illi"), ("illius", "illorum"), ("illi", "illis"),
                  ("illum", "illos"), ("illo", "illis")]),
        ("fem", [("illa", "illæ"), ("illius", "illarum"), ("illi", "illis"),
                 ("illam", "illas"), ("illa", "illis")]),
        ("neut", [("illud", "illa"), ("illius", "illorum"), ("illi", "illis"),
                  ("illud", "illa"), ("illo", "illis")]),
    ],
    "is, ea, id": [
        ("masc", [("is", "ii"), ("ejus", "eorum"), ("ei", "eis"),
                  ("eum", "eos"), ("eo", "eis")]),
        ("fem", [("ea", "eæ"), ("ejus", "earum"), ("ei", "eis"),
                 ("eam", "eas"), ("ea", "eis")]),
        ("neut", [("id", "ea"), ("ejus", "eorum"), ("ei", "eis"),
                  ("id", "ea"), ("eo", "eis")]),
    ],
    "ipse, ipsa, ipsum": [
        ("masc", [("ipse", "ipsi"), ("ipsius", "ipsorum"), ("ipsi", "ipsis"),
                  ("ipsum", "ipsos"), ("ipso", "ipsis")]),
        ("fem", [("ipsa", "ipsæ"), ("ipsius", "ipsarum"), ("ipsi", "ipsis"),
                 ("ipsam", "ipsas"), ("ipsa", "ipsis")]),
        ("neut", [("ipsum", "ipsa"), ("ipsius", "ipsorum"), ("ipsi", "ipsis"),
                  ("ipsum", "ipsa"), ("ipso", "ipsis")]),
    ],
    "iste, ista, istud": [
        ("masc", [("iste", "isti"), ("istius", "istorum"), ("isti", "istis"),
                  ("istum", "istos"), ("isto", "istis")]),
        ("fem", [("ista", "istæ"), ("istius", "istarum"), ("isti", "istis"),
                 ("istam", "istas"), ("ista", "istis")]),
        ("neut", [("istud", "ista"), ("istius", "istorum"), ("isti", "istis"),
                  ("istud", "ista"), ("isto", "istis")]),
    ],
    # interrogative: two terminations, and no neuter plural in use
    "quis, quid": [
        ("m / f", [("quis", "qui"), ("cujus", "quorum"), ("cui", "quibus"),
                   ("quem", "quos"), ("quo", "quibus")]),
        ("n", [("quid", "quæ"), ("cujus", "quorum"), ("cui", "quibus"),
               ("quid", "quæ"), ("quo", "quibus")]),
    ],
    "uter, utra, utrum": [
        ("masc", [("uter", "utri"), ("utrius", "utrorum"), ("utri", "utris"),
                  ("utrum", "utros"), ("utro", "utris")]),
        ("fem", [("utra", "utræ"), ("utrius", "utrarum"), ("utri", "utris"),
                 ("utram", "utras"), ("utra", "utris")]),
        ("neut", [("utrum", "utra"), ("utrius", "utrorum"), ("utri", "utris"),
                  ("utrum", "utra"), ("utro", "utris")]),
    ],
    # duo and tres decline like nothing else, and are plural by nature: every
    # form belongs in the plural column
    "duo, duæ, duo": [
        ("masc", [(None, "duo"), (None, "duorum"), (None, "duobus"),
                  (None, "duos"), (None, "duobus")]),
        ("fem", [(None, "duæ"), (None, "duarum"), (None, "duabus"),
                 (None, "duas"), (None, "duabus")]),
        ("neut", [(None, "duo"), (None, "duorum"), (None, "duobus"),
                  (None, "duo"), (None, "duobus")]),
    ],
    "tres, tria": [
        ("m / f", [(None, "tres"), (None, "trium"), (None, "tribus"),
                   (None, "tres"), (None, "tribus")]),
        ("n", [(None, "tria"), (None, "trium"), (None, "tribus"),
               (None, "tria"), (None, "tribus")]),
    ],
    # ambo follows duo, not bonus: plural by nature, with the -o nominative
    # and the -obus/-abus dative and ablative
    "ambo, ambæ, ambo": [
        ("masc", [(None, "ambo"), (None, "amborum"), (None, "ambobus"),
                  (None, "ambos"), (None, "ambobus")]),
        ("fem", [(None, "ambæ"), (None, "ambarum"), (None, "ambabus"),
                 (None, "ambas"), (None, "ambabus")]),
        ("neut", [(None, "ambo"), (None, "amborum"), (None, "ambobus"),
                  (None, "ambo"), (None, "ambobus")]),
    ],
}

def _hundreds(stem):
    """ducenti … nongenti: first-and-second declension, but plural by nature,
    so every form belongs in the plural column, as with duo."""
    return [
        ("masc", [(None, stem + "i"), (None, stem + "orum"), (None, stem + "is"),
                  (None, stem + "os"), (None, stem + "is")]),
        ("fem", [(None, stem + "æ"), (None, stem + "arum"), (None, stem + "is"),
                 (None, stem + "as"), (None, stem + "is")]),
        ("neut", [(None, stem + "a"), (None, stem + "orum"), (None, stem + "is"),
                  (None, stem + "a"), (None, stem + "is")]),
    ]


PRONOUN_BLOCKS.update({
    f"{s}i, {s}æ, {s}a": _hundreds(s)
    for s in ("ducent", "trecent", "quadringent", "quingent", "sescent",
              "septingent", "octingent", "nongent",
              # the distributives decline the same way and are equally plural
              "bin", "tern", "quatern", "quin", "sen", "septen")
})

# Pronouns built by welding a fixed particle onto a declining base: only the
# base moves, which is exactly the thing a learner gets wrong.
SUFFIXED_PRONOUNS = {
    "quicumque, quæcumque, quodcumque": ("qui, quæ, quod", "cumque"),
    "uterque, utraque, utrumque": ("uter, utra, utrum", "que"),
}


def suffixed(base, suffix):
    return [(chip, [(sg and sg + suffix, pl and pl + suffix) for sg, pl in pairs])
            for chip, pairs in base]

# Welded the other way round: a fixed particle in FRONT of the declining base.
# semetipso is semet + ipso, and only the ipse half moves.
PREFIXED_PRONOUNS = {
    "semetipse, semetipsa, semetipsum": ("ipse, ipsa, ipsum", "semet"),
}

PRONOUN_BLOCKS.update({
    cite: [(chip, [(sg and prefix + sg, pl and prefix + pl) for sg, pl in pairs])
           for chip, pairs in PRONOUN_BLOCKS[base]]
    for cite, (base, prefix) in PREFIXED_PRONOUNS.items()
})

# unusquisque declines in both halves at once (unum + quodque) and only in the
# singular: the -que here is quisque, not the enclitic 'and'.
PRONOUN_BLOCKS["unusquisque, unaquæque, unumquodque"] = [
    ("masc", [("unusquisque", None), ("uniuscujusque", None),
              ("unicuique", None), ("unumquemque", None), ("unoquoque", None)]),
    ("fem", [("unaquæque", None), ("uniuscujusque", None),
             ("unicuique", None), ("unamquamque", None), ("unaquaque", None)]),
    ("neut", [("unumquodque", None), ("uniuscujusque", None),
              ("unicuique", None), ("unumquodque", None), ("unoquoque", None)]),
]

# The personal pronouns have no gender to chip: one paradigm each.
PERSONAL_BLOCKS = {
    "ego": ("first person", [("ego", "nos"), ("mei", "nostri"),
                             ("mihi", "nobis"), ("me", "nos"), ("me", "nobis")]),
    "tu": ("second person", [("tu", "vos"), ("tui", "vestri"),
                             ("tibi", "vobis"), ("te", "vos"), ("te", "vobis")]),
    "sui": ("reflexive", [(None, None), ("sui", "sui"), ("sibi", "sibi"),
                          ("se", "se"), ("se", "se")]),
}
PERSONAL_ALIAS = {"nos": "ego", "vos": "tu", "se": "sui", "sese": "sui",
                  "sui, sibi, se": "sui"}


def shared_note(blocks):
    """Names the forms a chip row would otherwise hide: cujus and cui are one
    form for all three genders, and a reader should not have to discover that
    by tapping through."""
    rows = [r for _, r in blocks]
    if len(rows) < 2:
        return None
    differing = [rows[0][i][0] for i in range(len(rows[0]))
                 if any(len({r[i][c] for r in rows}) > 1 for c in (1, 2))]
    if differing and set(differing) <= {"Nom", "Acc"}:
        return "Only the nominative and accusative differ."
    shared, seen = [], set()
    for i in range(len(rows[0])):
        for c in (1, 2):
            vals = {r[i][c] for r in rows}
            f = next(iter(vals))
            if len(vals) == 1 and f and f not in seen:
                seen.add(f)
                shared.append(f)
    if not shared or len(shared) > 4:
        return None
    where = "both genders" if len(rows) == 2 else "all three genders"
    if len(shared) == 1:
        return f"{shared[0]} is the same in {where}."
    return f"{', '.join(shared[:-1])} and {shared[-1]} are the same in {where}."


def build_gendered_tables(forms, tables, freq):
    for key, entry in forms.items():
        cls, cite, kind, parse = entry["c"], entry["l"], entry["k"], entry["p"]
        if entry.get("t"):
            continue
        blocks, suffix = None, ""
        if kind == "pronoun":
            base = PERSONAL_ALIAS.get(cite.lower(), cite.lower())
            if base in PERSONAL_BLOCKS:
                label, pairs = PERSONAL_BLOCKS[base]
                tkey = f"{base}-pron"
                if tkey not in tables:
                    tables[tkey] = {"l": cite, "c": label,
                                    "rows": make_rows(tkey, _cases(pairs), freq)}
                entry["t"] = tkey
                continue
            raw = PRONOUN_BLOCKS.get(cite)
            if raw is None and cite in SUFFIXED_PRONOUNS:
                base, suffix = SUFFIXED_PRONOUNS[cite]
                raw = suffixed(PRONOUN_BLOCKS[base], suffix)
            if raw is None:
                warn(f"no declension table for pronoun {cite!r}: "
                     f"add it to PRONOUN_BLOCKS")
                continue
            blocks = [(chip, _cases(pairs)) for chip, pairs in raw]
        elif kind == "adjective":
            blocks = adjective_blocks(cite, cls, parse)
            if blocks is None:
                if "," in cite:   # a one-word citation is an indeclinable
                    warn(f"no declension table for adjective {cite!r} ({cls})")
                continue
        elif kind == "verb" and "participle" in parse:
            blocks = participle_blocks(cite, cls, parse)
            suffix = "-ppp" if "perfect" in parse else "-ppl"
            if blocks is None:
                warn(f"no participle table for {cite!r} ({cls})")
                continue
        else:
            continue
        tkey = table_key(cite, clean(cite.split(",")[0]) + suffix)
        if tkey not in tables:
            t = {"l": cite, "c": cls,
                 "g": [[chip, make_rows(tkey, pairs, freq)]
                       for chip, pairs in blocks]}
            note = shared_note(blocks)
            if note:
                t["note"] = note
            tables[tkey] = t
        entry["t"] = tkey


# ---------- link expansion (identical to the Genesis 1 build) ----------
CLAUSE_TYPES = {"s": "subject", "o": "object", "d": "recipient"}
LINK_TYPES = {"s", "o", "d", "g", "a", "w", "c"}
HEAD_PHRASE = {"a": "described by", "w": "with", "g": "belongs to", "c": "introduces"}
DEP_PHRASE = {"a": "adjective for", "w": "with", "g": "owner of", "c": "introduced by"}


def word_of(toks, i):
    return re.sub(r"[^\wÆæŒœëï ]+$", "",
                  re.sub(r"^[^\wÆæŒœëï]+", "",
                         toks[i][0].split(" ")[0] if " " not in toks[i][0] else toks[i][0]))


def expand_links(vnum, toks, links):
    clauses = {}   # verb index -> [(index, role), ...]
    pairwise = []  # agreement / with / ownership / subordinator links
    for triple in links:
        if not (isinstance(triple, list) and len(triple) == 3):
            err(f"verse {vnum}: malformed link {triple}")
            continue
        i, j, typ = triple
        if typ not in LINK_TYPES:
            err(f"verse {vnum}: unknown link type {typ!r} in {triple}")
            continue
        if not (isinstance(i, int) and isinstance(j, int)
                and 0 <= i < len(toks) and 0 <= j < len(toks)) or i == j:
            err(f"verse {vnum}: link index out of range {triple} "
                f"({len(toks)} tokens)")
            continue
        if typ in CLAUSE_TYPES:
            clauses.setdefault(i, [(i, "verb")]).append((j, CLAUSE_TYPES[typ]))
        else:
            pairwise.append((i, j, typ))
    rel_r = {}     # index -> glow partner indices
    rel_line = {}  # index -> phrase list, clause line first
    # Whole clause in the verse's own word order; every member gets the same
    # line and glows every other member ("who did what").
    for members in clauses.values():
        ordered = sorted(members, key=lambda m: m[0])
        parts = []
        for idx, role in ordered:
            w = word_of(toks, idx)
            if parts and parts[-1][0] == role:
                parts[-1][1].append(w)
            else:
                parts.append((role, [w]))
        line = " · ".join(f"{role} {', '.join(ws)}" for role, ws in parts)
        idxs = [m[0] for m in members]
        for idx in idxs:
            rel_line.setdefault(idx, []).append(line)
            rel_r.setdefault(idx, set()).update(x for x in idxs if x != idx)
    rel_pairs = {}  # index -> [(phrase, word)] to be grouped by phrase
    for i, j, typ in pairwise:
        rel_r.setdefault(i, set()).add(j)
        rel_r.setdefault(j, set()).add(i)
        rel_pairs.setdefault(i, []).append((HEAD_PHRASE[typ], word_of(toks, j)))
        rel_pairs.setdefault(j, []).append((DEP_PHRASE[typ], word_of(toks, i)))
    for idx, parts in rel_pairs.items():
        grouped = []
        for phrase, w in parts:
            if grouped and grouped[-1][0] == phrase:
                grouped[-1][1].append(w)
            else:
                grouped.append((phrase, [w]))
        rel_line.setdefault(idx, []).extend(
            f"{ph} {', '.join(ws)}" for ph, ws in grouped
        )
    for idx, lines in rel_line.items():
        t = toks[idx]
        if len(t) == 2:
            t.append({})
        if rel_r.get(idx):
            t[2]["r"] = sorted(rel_r[idx])
        t[2]["rd"] = " · ".join(lines)


# ---------- compile ----------
GENDER_LETTER = {"masculine": "m.", "feminine": "f.", "neuter": "n.",
                 "common gender": "c."}
TOKEN_FIELDS = ("w", "g", "p", "l", "c", "d")


def compile_chapter(inter, out_path, registry_path=None, update_lemmas=False):
    book, chapter = inter.get("book"), inter.get("chapter")
    if not book or not chapter:
        raise SystemExit("intermediate file must carry 'book' and 'chapter'")
    src_path = f"{ROOT}/public/bible/{book}/{chapter}.json"
    if not os.path.exists(src_path):
        raise SystemExit(f"no source chapter at {src_path}")
    src = json.load(open(src_path))

    TKEY_OWNER.clear()
    freq, bigrams = corpus_counts()
    BIGRAMS.update(bigrams)
    FREQ.update(freq)

    # cross-chapter consistency: the settled dictionary every book shares
    registry = (lemma_registry.load(registry_path) if registry_path
                else {"lemmas": {}, "forms": {}})
    here = f"{book} {chapter}"
    staged, staged_forms, revised = {}, {}, []

    # lemma-level consistency: same citation -> same class + definition
    lemma_info = {}
    # form-level: surface form -> the citations it is used under here
    form_lemma = {}

    verses = {}
    # (surface form, citation) -> one reading; the commonest becomes the
    # form's default entry and the rest become per-token overrides
    readings = {}
    forms = {}
    for v in src["verses"]:
        vnum = v["v"]
        vdata = inter["verses"].get(str(vnum))
        if vdata is None:
            err(f"verse {vnum}: missing from intermediate file")
            continue
        toks_in = vdata.get("tokens", [])
        # reconstruction: tokens joined with single spaces = source text
        src_text = " ".join(p[0] for p in v["pairs"])
        rec = " ".join(t.get("w", "") for t in toks_in)
        if src_text != rec:
            err(f"verse {vnum}: reconstruction mismatch\n"
                f"  source: {src_text}\n  tokens: {rec}")
            continue
        out = []
        for t in toks_in:
            missing = [f for f in TOKEN_FIELDS if not t.get(f)]
            if missing:
                err(f"verse {vnum}: token {t.get('w')!r} missing {missing}")
                continue
            w, g, p, l, c, d = (t[f] for f in TOKEN_FIELDS)
            key = form_key(w)
            if not key.replace(" ", ""):
                err(f"verse {vnum}: token {w!r} cleans to nothing")
                continue
            cls = attrs_of(romanize(c))
            kind = pos_of(c, p, l)
            if not kind:
                warn(f"verse {vnum}: cannot classify {w!r} (class {c!r}); "
                     f"card gets no part-of-speech chip")
            # consistency bookkeeping
            if l in lemma_info:
                if lemma_info[l] != (cls, d):
                    err(f"lemma {l!r}: inconsistent class/definition "
                        f"({lemma_info[l]} vs {(cls, d)})")
            else:
                lemma_info[l] = (cls, d)
                # first sighting in this chapter is where the registry speaks
                prior = registry["lemmas"].get(l)
                if prior is None:
                    staged[l] = {"c": cls, "d": d, "src": here}
                else:
                    diff = lemma_registry.disagreement(prior, cls, d)
                    if diff and update_lemmas:
                        revised.append((l, prior.get("src", "?"), diff))
                        registry["lemmas"][l] = {"c": cls, "d": d, "src": here}
                    elif diff:
                        err(f"lemma {l!r} contradicts the registry (settled by "
                            f"{prior.get('src', '?')}): {diff}. Match it, or "
                            f"rerun with --update-lemmas to change the entry "
                            f"everywhere.")
            # A surface form may be two words (os, ossis and os, oris; cum the
            # preposition and cum the conjunction). The majority reading
            # becomes the form's default and the others ride on their tokens,
            # so both are true and neither is silently overwritten.
            if key in form_lemma and l not in form_lemma[key]:
                warn(f"form {key!r} is two lexemes here: {form_lemma[key][0]!r} "
                     f"and {l!r} — the commoner one becomes the card's default "
                     f"and the other rides on its tokens")
            seen_here = form_lemma.setdefault(key, [])
            if l not in seen_here:
                seen_here.append(l)
                known = registry["forms"].get(key, [])
                if l not in known:
                    if known:
                        warn(f"form {key!r} gains a reading: was {known!r}, "
                             f"this chapter adds {l!r}")
                    staged_forms.setdefault(key, list(known)).append(l)
            # gender letter in a noun citation should match the class
            if kind == "noun":
                for gw, letter in GENDER_LETTER.items():
                    if gw in cls and not l.rstrip().endswith(letter):
                        warn(f"{l!r}: class says {gw} but citation lacks "
                             f"'{letter}'")
                for gw in GENDER_LETTER:
                    if gw in p:
                        warn(f"verse {vnum} {w!r}: noun parse states gender "
                             f"({p!r}) — gender is a lemma fact")
            # ego, tu and sui have no gender to state; every other pronoun does
            genderless = (kind == "pronoun" and PERSONAL_ALIAS.get(
                l.lower(), l.lower()) in PERSONAL_BLOCKS)
            if kind in ("adjective", "pronoun") and not any(
                gw in p for gw in ("masculine", "feminine", "neuter")
            ) and "with -que" not in p and not genderless:
                warn(f"verse {vnum} {w!r}: {kind} parse lacks gender ({p!r})")
            r = readings.setdefault((key, l), {
                "l": l, "c": cls, "k": kind, "d": d,
                "n": (bigrams[tuple(key.split(" "))]
                      if " " in key else freq[key]),
                "_parses": collections.Counter(), "_seen": 0,
            })
            r["_parses"][p] += 1
            r["_seen"] += 1
            out.append([w, g, {"p": p, "_l": l}])
        verses[str(vnum)] = out
    extra = set(inter["verses"]) - {str(v["v"]) for v in src["verses"]}
    if extra:
        err(f"intermediate has verses not in source: {sorted(extra)}")

    # The commonest reading of a form is its default card; a tie is broken on
    # the citation so a rebuild never flips it. Everything else is an
    # alternate, and its tokens carry the difference.
    alts = {}
    for key in dict.fromkeys(k for k, _ in readings):
        here_l = [l for (k, l) in readings if k == key]
        main = max(here_l, key=lambda L: (readings[(key, L)]["_seen"], L))
        for l in here_l:
            entry = readings[(key, l)]
            entry["p"] = entry.pop("_parses").most_common(1)[0][0]
            entry.pop("_seen")
            (forms if l == main else alts)[key if l == main
                                           else (key, l)] = entry

    # tables are built over every reading, so an alternate gets its own
    # paradigm rather than inheriting the default's
    # the builders never read the key as a string, so the (form, citation)
    # pair itself serves as the key
    tabled = dict(forms)
    tabled.update(alts)
    lemma_forms = collections.defaultdict(set)
    for key, e in forms.items():
        lemma_forms[e["l"]].add(key)
    for (key, l), e in alts.items():
        lemma_forms[l].add(key)
    for form, lemmas in registry["forms"].items():
        for l in lemmas:
            lemma_forms[l].add(form)
    CLAIMED_ELSEWHERE.clear()
    CLAIMED_ELSEWHERE.update(registry["forms"])
    tables = build_tables(tabled, freq, lemma_forms)
    build_verb_tables(tabled, tables, freq)
    build_gendered_tables(tabled, tables, freq)

    # a token drops whatever it shares with its form's default card
    for toks in verses.values():
        for t in toks:
            key, l = form_key(t[0]), t[2].pop("_l")
            default = forms[key]
            if l == default["l"]:
                if t[2]["p"] == default["p"]:
                    del t[2]["p"]
            else:
                # the reader falls back to the default card, which belongs to
                # the other lexeme, so an alternate keeps its parse always
                a = alts[(key, l)]
                t[2].update({f: a[f] for f in ("l", "c", "k", "d")})
                # always stated, null included: an alternate with no paradigm
                # must not fall back to the default lexeme's table
                t[2]["t"] = a.get("t")
            if not t[2]:
                t.pop()

    # links -> glow arrays + relation lines
    for vnum_str, toks in verses.items():
        links = inter["verses"][vnum_str].get("links", [])
        expand_links(vnum_str, toks, links)

    for note in inter.get("notes", []):
        warn(f"model note: {note}")

    if errors:
        print(f"REJECTED — {len(errors)} error(s):", file=sys.stderr)
        for e in errors:
            print(f"  ✗ {e}", file=sys.stderr)
        for w in warnings:
            print(f"  ⚠ {w}", file=sys.stderr)
        raise SystemExit(1)

    result = {"verses": verses, "forms": forms, "tables": tables}
    json.dump(result, open(out_path, "w"), ensure_ascii=False,
              separators=(",", ":"))
    ntok = sum(len(t) for t in verses.values())
    print(f"wrote {out_path}: {len(verses)} verses, {ntok} tokens, "
          f"{len(forms)} forms, {len(tables)} tables")
    for w in warnings:
        print(f"  ⚠ {w}")

    # final sanity: reload and re-check reconstruction
    check = json.load(open(out_path))
    for v in src["verses"]:
        src_text = " ".join(p[0] for p in v["pairs"])
        rec = " ".join(t[0] for t in check["verses"][str(v["v"])])
        assert src_text == rec, f"verse {v['v']} post-write mismatch"
    print("reconstruction check passed")

    # the chapter stood up, so its new lemmas join the settled dictionary
    if registry_path:
        for lemma, was, diff in revised:
            print(f"  ↻ {lemma!r} rewritten (was settled by {was}): {diff}")
        registry["lemmas"].update(staged)
        registry["forms"].update(staged_forms)
        lemma_registry.save(registry, registry_path)
        print(f"registry: {len(staged)} new lemmas, {len(staged_forms)} new "
              f"forms, {len(revised)} revised — {len(registry['lemmas'])} "
              f"lemmas / {len(registry['forms'])} forms total")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("intermediate", help="LLM output in the prompt's format")
    ap.add_argument("--out", help="write here instead of public/bible/...")
    ap.add_argument("--registry", default=lemma_registry.DEFAULT_PATH,
                    help="the shared lemma dictionary")
    ap.add_argument("--no-registry", action="store_true",
                    help="skip the cross-chapter lemma check entirely")
    ap.add_argument("--update-lemmas", action="store_true",
                    help="a lemma that contradicts the registry rewrites it "
                         "instead of failing; use when the new reading is the "
                         "correct one")
    args = ap.parse_args()
    inter = json.load(open(args.intermediate))
    out = args.out or (f"{ROOT}/public/bible/{inter.get('book')}/"
                       f"{inter.get('chapter')}.gloss.json")
    compile_chapter(inter, out,
                    registry_path=None if args.no_registry else args.registry,
                    update_lemmas=args.update_lemmas)


if __name__ == "__main__":
    main()
