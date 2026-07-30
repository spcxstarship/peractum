# Diffs a re-annotated chapter against an earlier pass.
#
#   python3 scripts/compare_passes.py genesis 3
#   python3 scripts/compare_passes.py genesis 3 --verbose
#
# Two independent passes over the same Latin will agree on most of it. Where
# they disagree is the interesting part: one of them is wrong, or the text is
# genuinely ambiguous and the disagreement is telling you so. This prints that
# list and nothing else — matching tokens are not news.
#
# The Latin itself cannot differ (the compiler reconstructs it character for
# character against the source), so every difference here is a judgement:
# a gloss, a parse, a citation, a link, or a merge.
import argparse
import json
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASS1 = f"{ROOT}/docs/gloss/pass1"

FIELDS = (("g", "gloss"), ("p", "parse"), ("l", "citation"),
          ("c", "class"), ("d", "definition"))


def card(gloss, tok):
    """What the reader would actually see for one token, defaults resolved."""
    form = gloss["forms"].get(_key(tok[0]), {})
    ov = tok[2] if len(tok) > 2 else {}
    out = {"g": tok[1]}
    for f, _ in FIELDS[1:]:
        out[f] = ov.get(f, form.get(f))
    out["r"] = tuple(ov.get("r", ()))
    return out


def _key(display):
    import re
    return " ".join(
        re.sub(r"[^\wÆæŒœëï]+$", "", re.sub(r"^[^\wÆæŒœëï]+", "", w)).lower()
        for w in display.split(" ")
    )


def compare(a, b, verbose):
    rows = []
    for vnum in sorted(a["verses"], key=int):
        ta, tb = a["verses"][vnum], b["verses"].get(vnum, [])
        if len(ta) != len(tb):
            rows.append((vnum, None, "tokenization",
                         f"{len(ta)} tokens", f"{len(tb)} tokens"))
            continue
        for i, (x, y) in enumerate(zip(ta, tb)):
            if x[0] != y[0]:
                rows.append((vnum, i, "token text", x[0], y[0]))
                continue
            ca, cb = card(a, x), card(b, y)
            for f, label in FIELDS:
                if ca.get(f) != cb.get(f):
                    rows.append((vnum, i, f"{x[0]} — {label}",
                                 ca.get(f), cb.get(f)))
            if ca["r"] != cb["r"] and verbose:
                rows.append((vnum, i, f"{x[0]} — links",
                             list(ca["r"]), list(cb["r"])))
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book")
    ap.add_argument("chapter", type=int)
    ap.add_argument("--old", help=f"default {PASS1}/<n>.gloss.json")
    ap.add_argument("--new", help="default the live public/bible copy")
    ap.add_argument("--verbose", action="store_true",
                    help="include link differences, which are noisier")
    args = ap.parse_args()

    old = args.old or f"{PASS1}/{args.chapter}.gloss.json"
    new = args.new or (f"{ROOT}/public/bible/{args.book}/"
                       f"{args.chapter}.gloss.json")
    for p in (old, new):
        if not os.path.exists(p):
            raise SystemExit(f"missing {p}")
    a, b = json.load(open(old)), json.load(open(new))

    rows = compare(a, b, args.verbose)
    ntok = sum(len(t) for t in a["verses"].values())
    if not rows:
        print(f"{args.book} {args.chapter}: the two passes agree on all "
              f"{ntok} tokens")
        return
    print(f"{args.book} {args.chapter}: {len(rows)} difference(s) "
          f"across {ntok} tokens\n")
    for vnum, i, what, x, y in rows:
        where = f"{vnum}:{i}" if i is not None else vnum
        print(f"  {where:>8}  {what}")
        print(f"            pass 1: {x!r}")
        print(f"            pass 2: {y!r}")
    print(f"\nEvery difference is a judgement call — the Latin is identical by "
          f"construction.\nWork through them and keep the better reading.",
          file=sys.stderr)


if __name__ == "__main__":
    main()
