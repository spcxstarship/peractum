# The lemma registry: the settled dictionary, shared by every chapter of
# every book.
#
# compile_gloss.py already enforces two rules WITHIN a chapter — same citation
# means same class and definition, and one surface form belongs to one lemma.
# Neither rule survived the chapter boundary, and both had already broken by
# the third compiled chapter: seven of 103 shared lemmas disagreed on their
# definition, and 'quod' and 'vobis' were filed under different lemmas in
# different chapters. The reader's card is keyed by surface form, so that is
# the same word showing two different entries depending on where it is tapped.
#
# This file makes both rules global. It holds two indexes:
#
#   lemmas   citation -> {class, definition, the chapter that settled it}
#   forms    surface form -> every citation it is legitimately used under
#
# A form usually has exactly one reading. Some have two, because they are two
# words: os (bone / mouth), cum (preposition / conjunction), facies (you will
# make / face). The compiler makes the commoner one the form's default card
# and hangs the other on its own tokens, so both stay true.
#
# compile_gloss.py loads them, rejects a chapter that contradicts either, and
# adds genuinely new entries on success. gloss_prep.py quotes the relevant
# slice into the next chapter's brief, so drift is prevented at the point of
# annotation rather than caught afterwards.
#
#   python3 scripts/lemma_registry.py seed     # build it from compiled chapters
#   python3 scripts/lemma_registry.py check    # re-verify every compiled chapter
#   python3 scripts/lemma_registry.py show terra
import argparse
import glob
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_PATH = f"{ROOT}/docs/gloss/lemmas.json"

FIELDS = ("c", "d")
EMPTY = {"lemmas": {}, "forms": {}}


def load(path=DEFAULT_PATH):
    if not path or not os.path.exists(path):
        return {"lemmas": {}, "forms": {}}
    reg = json.load(open(path))
    return {"lemmas": reg.get("lemmas", {}), "forms": reg.get("forms", {})}


def save(reg, path=DEFAULT_PATH):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as fh:
        json.dump({"lemmas": dict(sorted(reg["lemmas"].items())),
                   "forms": dict(sorted(reg["forms"].items()))},
                  fh, ensure_ascii=False, indent=1, sort_keys=True)
        fh.write("\n")


def clean(tok):
    return re.sub(r"[^\wÆæŒœëï]+$", "", re.sub(r"^[^\wÆæŒœëï]+", "", tok)).lower()


def facts(entry):
    return tuple(entry[f] for f in FIELDS)


def disagreement(prior, cls, d):
    """None if the lemma matches the registry, else a human-readable diff."""
    if facts(prior) == (cls, d):
        return None
    parts = []
    if prior["c"] != cls:
        parts.append(f"class {prior['c']!r} -> {cls!r}")
    if prior["d"] != d:
        parts.append(f"definition {prior['d']!r} -> {d!r}")
    return "; ".join(parts)


# ---------- seeding from already-compiled chapters ----------
def compiled_chapters():
    """Every public/bible/<book>/<n>.gloss.json, in book then chapter order."""
    out = []
    for path in glob.glob(f"{ROOT}/public/bible/*/*.gloss.json"):
        book = os.path.basename(os.path.dirname(path))
        m = re.match(r"(\d+)\.gloss\.json$", os.path.basename(path))
        if m:
            out.append((book, int(m.group(1)), path))
    return sorted(out)


def entries_of(gloss):
    """(form, citation, class, definition) for every reading in a compiled
    chapter. A form's default card lives in `forms`; an alternate reading —
    os the mouth where os the bone is the default — rides on its own tokens,
    so both have to be walked or half the dictionary is invisible here."""
    seen = set()
    for form, e in gloss["forms"].items():
        seen.add((form, e["l"]))
        yield form, e["l"], e["c"], e["d"]
    for toks in gloss["verses"].values():
        for t in toks:
            ov = t[2] if len(t) > 2 else None
            if not ov or "l" not in ov:
                continue
            pair = (clean_form(t[0]), ov["l"])
            if pair not in seen:
                seen.add(pair)
                yield pair[0], ov["l"], ov["c"], ov["d"]


def clean_form(display):
    return " ".join(clean(w) for w in display.split(" "))


def scan(chapters):
    """(registry, conflicts) from compiled chapters, first occurrence wins."""
    reg = {"lemmas": {}, "forms": {}}
    conflicts = []
    for book, chapter, path in chapters:
        here = f"{book} {chapter}"
        for form, lemma, cls, d in entries_of(json.load(open(path))):
            prior = reg["lemmas"].get(lemma)
            if prior is None:
                reg["lemmas"][lemma] = {"c": cls, "d": d, "src": here}
            else:
                diff = disagreement(prior, cls, d)
                if diff:
                    conflicts.append((lemma, prior["src"], here, diff))
            reg["forms"].setdefault(form, [])
            if lemma not in reg["forms"][form]:
                reg["forms"][form].append(lemma)
    return reg, conflicts


def settled_for(forms, path=DEFAULT_PATH):
    """[(form, citation, entry)] for those surface forms already settled."""
    reg = load(path)
    out = []
    for form in sorted(set(forms)):
        for lemma in reg["forms"].get(form, []):
            if lemma in reg["lemmas"]:
                out.append((form, lemma, reg["lemmas"][lemma]))
    return out


def report_conflicts(conflicts):
    print(f"{len(conflicts)} disagreement(s) between chapters:", file=sys.stderr)
    for key, first, second, diff in conflicts:
        print(f"  ✗ {key!r}\n      {first} vs {second}: {diff}", file=sys.stderr)
    print("\nFix the source of one side, rebuild that chapter, and seed again.\n"
          "Nothing was written.", file=sys.stderr)


def select(chapters, only):
    """Restrict to `book:n,n,...` — during a re-annotation the compiled
    chapters on disk belong to two different passes, and seeding across both
    just reports every wording difference between them."""
    if not only:
        return chapters
    book, _, nums = only.partition(":")
    want = {int(n) for n in nums.split(",") if n.strip()}
    return [c for c in chapters if c[0] == book and (not want or c[1] in want)]


def cmd_seed(args):
    chapters = select(compiled_chapters(), args.only)
    if not chapters:
        raise SystemExit("no compiled chapters found under public/bible")
    reg, conflicts = scan(chapters)
    if conflicts:
        report_conflicts(conflicts)
        raise SystemExit(1)
    save(reg, args.registry)
    names = ", ".join(f"{b} {c}" for b, c, _ in chapters)
    split = {f: ls for f, ls in reg["forms"].items() if len(ls) > 1}
    print(f"wrote {args.registry}: {len(reg['lemmas'])} lemmas, "
          f"{len(reg['forms'])} forms, from {len(chapters)} chapter(s) ({names})")
    if split:
        print(f"{len(split)} form(s) carry more than one reading:")
        for f, ls in sorted(split.items()):
            print(f"  {f}: " + " / ".join(ls))


def cmd_check(args):
    reg = load(args.registry)
    if not reg["lemmas"]:
        raise SystemExit(f"no registry at {args.registry} — run 'seed' first")
    bad = []
    for book, chapter, path in select(compiled_chapters(), args.only):
        here = f"{book} {chapter}"
        for form, lemma, cls, d in entries_of(json.load(open(path))):
            prior = reg["lemmas"].get(lemma)
            if prior is None:
                bad.append((lemma, here, "not in registry"))
            else:
                diff = disagreement(prior, cls, d)
                if diff:
                    bad.append((lemma, here, diff))
            known = reg["forms"].get(form)
            if not known:
                bad.append((form, here, "form not in registry"))
            elif lemma not in known:
                bad.append((form, here,
                            f"reading {lemma!r} not among {known!r}"))
    seen = set()
    bad = [b for b in bad if not (b[:2] in seen or seen.add(b[:2]))]
    if bad:
        print(f"{len(bad)} mismatch(es):", file=sys.stderr)
        for key, where, diff in bad:
            print(f"  ✗ {key!r} ({where}): {diff}", file=sys.stderr)
        raise SystemExit(1)
    split = sum(1 for ls in reg["forms"].values() if len(ls) > 1)
    print(f"registry clean: {len(reg['lemmas'])} lemmas and "
          f"{len(reg['forms'])} forms agree with every compiled chapter "
          f"({split} form(s) with two readings)")


def cmd_show(args):
    reg = load(args.registry)
    needle = " ".join(args.lemma).lower()
    hits = {k: v for k, v in reg["lemmas"].items() if needle in k.lower()}
    for form, lemmas in reg["forms"].items():
        if needle == form:
            for lemma in lemmas:
                if lemma in reg["lemmas"]:
                    hits[lemma] = reg["lemmas"][lemma]
    if not hits:
        raise SystemExit(f"no lemma matching {needle!r} in {args.registry}")
    for k, v in sorted(hits.items()):
        forms = sorted(f for f, ls in reg["forms"].items() if k in ls)
        print(f"{k}\n  class      {v['c']}\n  definition {v['d']}\n"
              f"  settled by {v.get('src', '?')}\n"
              f"  forms      {', '.join(forms) or '—'}")


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--registry", default=DEFAULT_PATH)
    sub = ap.add_subparsers(dest="cmd", required=True)
    sd = sub.add_parser("seed", help="build the registry from compiled chapters")
    sd.add_argument("--only", help="limit to e.g. genesis:1,2,3")
    ck = sub.add_parser("check", help="verify every compiled chapter against it")
    ck.add_argument("--only", help="limit to e.g. genesis:1,2,3")
    show = sub.add_parser("show", help="print one lemma's settled entry")
    show.add_argument("lemma", nargs="+")
    args = ap.parse_args()
    {"seed": cmd_seed, "check": cmd_check, "show": cmd_show}[args.cmd](args)


if __name__ == "__main__":
    main()
