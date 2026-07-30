# Assembles the glossing prompt for one chapter: the standing instructions
# from docs/gloss-generation-prompt.md, the chapter's Clementine Latin, and
# the CPDV English, in the layout that prompt expects.
#
#   python3 scripts/gloss_prep.py genesis 3            # print to stdout
#   python3 scripts/gloss_prep.py genesis 3 --out /tmp/gen3.md
#
# The Latin and the English both live in the source chapter file, one pair per
# phrase, so this script is the only thing that needs to know that layout.
# Nothing here talks to a model — /gloss (the slash command) reads what this
# prints and does the philology.
import argparse
import json
import os

import lemma_registry

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PROMPT = f"{ROOT}/docs/gloss-generation-prompt.md"


def instructions():
    """Everything below the rule, minus the two paste-here placeholders."""
    text = open(PROMPT).read()
    if "\n---\n" not in text:
        raise SystemExit(f"{PROMPT}: expected a '---' rule after the preamble")
    body = text.split("\n---\n", 1)[1]
    return body.split("## Chapter text")[0].rstrip()


def chapter_text(book, chapter):
    path = f"{ROOT}/public/bible/{book}/{chapter}.json"
    if not os.path.exists(path):
        raise SystemExit(f"no chapter at {path}")
    src = json.load(open(path))
    latin, english = [], []
    for v in src["verses"]:
        # a verse is stored as phrase pairs; rejoin them into the printed verse
        latin.append(f"{v['v']}. " + " ".join(p[0] for p in v["pairs"]))
        english.append(f"{v['v']}. " + " ".join(p[1] for p in v["pairs"]))
    return "\n".join(latin), "\n".join(english)


def settled(book, chapter, registry):
    """The dictionary entries this chapter's words already have.

    Cross-chapter drift is cheapest to stop here, before a word is annotated:
    if the reader has already been shown a citation for this exact form, the
    new chapter has to reuse it, not invent a near-miss. compile_gloss.py will
    reject the chapter otherwise, so this is the courteous half of the same
    rule.
    """
    src = json.load(open(f"{ROOT}/public/bible/{book}/{chapter}.json"))
    forms = [lemma_registry.clean(t)
             for v in src["verses"] for p in v["pairs"] for t in p[0].split()]
    rows = lemma_registry.settled_for([f for f in forms if f], registry)
    if not rows:
        return []
    return [
        "## Already settled",
        "",
        f"{len(rows)} of this chapter's forms have been glossed in an earlier "
        "chapter. Their citation, class and definition are fixed — reuse the "
        "strings below exactly. The gloss and the parse are still yours to "
        "write for this occurrence; only the dictionary entry is binding.",
        "",
        "A form listed twice is two words (os the bone and os the mouth). "
        "Pick the one this occurrence actually is — the build keeps both.",
        "",
        "| form | `l` | `c` | `d` |",
        "|------|-----|-----|-----|",
        *(f"| {form} | {lem} | {e['c']} | {e['d']} |" for form, lem, e in rows),
        "",
    ]


def build(book, chapter, registry=lemma_registry.DEFAULT_PATH):
    latin, english = chapter_text(book, chapter)
    return "\n".join([
        instructions(),
        "",
        f"Produce the intermediate JSON for **{book} {chapter}**, with",
        f'`"book": "{book}"` and `"chapter": {chapter}`.',
        "",
        *settled(book, chapter, registry),
        "## Chapter text (Clementine Vulgate)",
        "",
        latin,
        "",
        "## Reference translation (CPDV — sense reference only, never copy phrasing)",
        "",
        english,
        "",
    ])


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("book", help="book slug, e.g. genesis")
    ap.add_argument("chapter", type=int)
    ap.add_argument("--out", help="write here instead of stdout")
    ap.add_argument("--registry", default=lemma_registry.DEFAULT_PATH,
                    help="the shared lemma dictionary to quote from")
    args = ap.parse_args()
    text = build(args.book, args.chapter, args.registry)
    if args.out:
        open(args.out, "w").write(text)
        print(f"wrote {args.out} ({len(text):,} chars)")
    else:
        print(text)


if __name__ == "__main__":
    main()
