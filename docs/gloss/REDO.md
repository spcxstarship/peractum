# Re-annotating Genesis 1–6 — pass 2

A second, independent philological pass over the six chapters that already
exist. One chapter per session, as `/gloss` intends: the point is a fresh
reading of the Latin, and a context that already knows the answers cannot
give one.

Pass 1 is archived under `docs/gloss/pass1/` — outputs, intermediates and its
registry. Nothing here destroys it.

## Why bother

Genesis 1 is the real prize: it was never annotated in this format at all. It
came from a one-off script with a hardcoded dictionary (now retired to
`docs/gloss/pass1/build_gloss_gen1.py.retired`)
that only ever built **noun** tables, so 117 of its 213 forms have no paradigm.
Pass 2 gives it an intermediate like every other chapter, and retires that
script.

Chapters 2–6 are already current. Redoing them buys a second opinion on ~2,200
tokens of judgement, and `compare_passes.py` turns every disagreement into a
line to adjudicate.

## The loop, per chapter N = 1 … 6

Run each in a **fresh session**.

For each chapter in order:

```sh
python3 scripts/gloss_prep.py genesis N --out /tmp/pass2-N.md   # brief, with
                                                                # the registry
                                                                # so far
```

Then `/gloss genesis N`, writing the intermediate to
`docs/gloss/N-genesis.json`, and compile it before starting the next chapter:

```sh
python3 scripts/compile_gloss.py docs/gloss/N-genesis.json
```

**Only once every chapter in the session is annotated**, compare:

```sh
python3 scripts/compare_passes.py genesis N     # for each N
```

Comparing earlier would defeat the point: `compare_passes` prints pass 1's
readings, and having just seen pass 1's answer for `terra` or `lignum` you
would carry it into the chapters still to come. Compile as you go so mistakes
do not compound; compare only at the end.

The compile overwrites `public/bible/genesis/N.gloss.json`, so the app moves
to pass 2 a chapter at a time. Both passes are valid data; a half-migrated
state is untidy, not broken.

## The rules, in one place

1. Never read pass 1's copy of the chapter you are annotating right now
   (`docs/gloss/pass1/N-*.json`). Other chapters' pass-1 files are fine as
   format references.
2. Chapter 2 only: use `docs/gloss/pass1/3-genesis.json` as the format
   exemplar, not `docs/gen2-output.json` — see below. Write to
   `docs/gloss/2-genesis.json`.
3. Regenerate each brief immediately before annotating that chapter.
4. Compile each chapter before starting the next.
5. Run `compare_passes.py` only after the last chapter of the session, then
   report every disagreement.
6. Do not commit.

## The exemplar trap

`/gloss` step 1 says to read `docs/gen2-output.json` as the format exemplar.
That file **is pass-1 chapter 2**, byte for byte. For every other chapter it is
just a format reference and the overlap is ordinary shared vocabulary. For
chapter 2 it is the answer sheet.

So: when re-annotating **chapter 2**, read `docs/gloss/pass1/3-genesis.json`
as the exemplar instead, write the new intermediate to
`docs/gloss/2-genesis.json`, and leave `docs/gen2-output.json` untouched until
you have compared the two.

The general rule: never read pass 1's copy of the chapter you are annotating
right now. Other chapters' pass-1 files are fine as format references.

## The registry starts empty

`docs/gloss/lemmas.json` was cleared, so chapter 1 begins with no settled
dictionary and each later chapter inherits only what pass 2 itself decided.
That is what makes the pass independent — a brief quoting pass 1 would be
handing back its own answers.

Pass 1's registry stays readable when you want to check what it concluded:

```sh
python3 scripts/lemma_registry.py --registry docs/gloss/pass1/lemmas.json show terra
```

At the end:

```sh
python3 scripts/lemma_registry.py seed --only genesis:1,2,3,4,5,6
python3 scripts/lemma_registry.py check --only genesis:1,2,3,4,5,6
```

`--only` matters while the migration is half-done: chapters not yet redone are
still pass 1, and seeding across both passes reports every wording difference
between them as a conflict. Drop the flag once all six are pass 2.

## Things pass 1 learned the hard way

Not binding — if pass 2 disagrees, that is the exercise working. But these
cost real time to discover, and the build now handles all of them:

- **`os`** is bone in 2:23 and mouth in 4:11; **`adæ`** is Adam's dative in
  3:17 and Ada's in 4:23; **`facies`** is "you shall make" in 6:14 and "face"
  in 4:6; **`cum`** is a preposition and a conjunction. Each is one surface
  form and two words. The compiler now makes the commoner reading the form's
  default card and hangs the other on its own tokens — no longer a blocker,
  just a warning naming the split.
- **`Heva`** declines (`Hevam`, 4:1) — Genesis 3 wrongly called it
  indeclinable. **`Mathusala`** is the same shape.
- **`Henoch`** and **`Lamech`** each name two different men (Cain's line and
  Seth's). One entry, a definition covering both.
- **`tui`** is `tuus` far more often than it is the genitive of `tu`.

## Aborting

```sh
cp docs/gloss/pass1/*.gloss.json public/bible/genesis/
cp docs/gloss/pass1/lemmas.json docs/gloss/lemmas.json
```
