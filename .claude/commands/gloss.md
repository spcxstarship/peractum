---
description: Gloss one Bible chapter into the word-by-word reader format
argument-hint: <book-slug> <chapter>  (e.g. genesis 3)
allowed-tools: Bash, Read, Write, Edit, Glob, Grep
---

Gloss **$1 $2** for Per Actum, then compile and verify it.

Run this in a fresh chat. A chapter is a few hundred tokens to annotate and
several thousand to emit; a clean context is worth more than anything you
would carry over.

## 1. Read the brief

```
python3 scripts/gloss_prep.py $1 $2 --out /tmp/gloss-$1-$2.md
```

Read that file. It contains the full annotation charter — tokenization,
glosses, parses, citations, definitions, the link rules, and the closed
vocabulary the build parses tenses out of — followed by the chapter's
Clementine Latin and its CPDV English.

Then read `docs/gen2-output.json` — a complete audited chapter in exactly the
format you are about to produce. When any convention feels ambiguous, imitate
it rather than your own habits.

## 2. Annotate

Produce the intermediate JSON for every verse. Write it straight to
`docs/gloss/$1-$2.json` with the Write tool — do not print it to the
conversation first. It is a large object and you only need it on disk.

Work verse by verse in order. Do not batch-guess: each token needs its own
gloss for *that occurrence*, and each link needs to be one you are sure of.
Silence over error — a missing glow is a small loss, a wrong glow teaches a
false rule.

## 3. Compile

```
python3 scripts/compile_gloss.py docs/gloss/$1-$2.json
```

This is the real check. It reconstructs every verse character for character,
enforces one citation per lemma, and generates the paradigm tables. It
**rejects** the chapter on any error.

- **Errors** — fix the intermediate and run it again. A reconstruction
  mismatch means your tokens do not rejoin into the printed verse; that is
  always your tokenization, never the source.
- **Warnings** — read each one. Most are the build telling you it could not
  build a table:
  - *"add 'X' to THIRD"* — a third-declension noun whose genitive plural the
    citation cannot supply. Add it to the `THIRD` dict in
    `scripts/compile_gloss.py` with the real genitive plural (and the neuter
    plural and i-stem ablative where they apply). Do not guess: check the form
    actually used in the Vulgate.
  - *"no conjugation tables for X"* — an irregular verb the generator cannot
    conjugate. Add it to `HAND_VERBS`, or, if it is a compound of sum / fero /
    eo / fio, make sure both principal parts show the prefix so it inherits
    from its parent.
  - *"no declension table for pronoun X"* — add it to `PRONOUN_BLOCKS`.
  - *"parse lacks gender"* — fix the parse in the intermediate; adjectives,
    participles and pronouns must state gender.
  - *"model note: …"* — your own notes from §7, echoed back. Each one is a
    paradigm you flagged as irregular; confirm the build handled it, and if it
    did not, that is what the dicts above are for.

## 4. Report

Tell me:

- how many verses, tokens and distinct forms compiled
- table coverage: how many forms got a paradigm, and what the uncovered ones
  are (function words are correct to have none; a noun or verb without one is
  a gap worth naming)
- any warning you could not resolve, and why
- anything in the chapter that was genuinely hard to parse, where a second
  opinion would be worth having

Do not commit. Leave the working tree for me to look at.
