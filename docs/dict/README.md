# Dictionary-tier coverage — Whitaker's Words vs the whole Vulgate

Every distinct wordform in the corpus (73 books, 611,757 tokens, 46,336
distinct forms) was run through Whitaker's Words — the real Ada program
(`mk270/whitakers-words`, built in Docker with
`make ADAFLAGS="-gnatwn -gnatyN"`), not the lossy Python port. Forms were
normalized Clementine → classical before lookup: æ→ae, œ→oe, j→i, ë→e, ï→i.

## Result

| | types | tokens | share of text |
|---|---|---|---|
| recognized | 43,295 (93.4%) | 596,156 | **97.45%** |
| gap: vocabulary | **30** | 150 | 0.02% |
| gap: proper names | 3,011 | 15,451 | 2.53% |

Words' own tricks (syncope `procreassent` → `procreavissent`, spelling mods
like acq/adq) fire natively, and its dictionary already includes the major
biblical names — Israel, David, Jerusalem, Jesus, Moses all resolve.

## The two gap lists

- `gaps-vocabulary.tsv` — all 30 unrecognized non-name forms. Nearly all are
  one family (pharisæus / sadducæus in their cases) plus Hebrew/Greek loans
  (theraphim) and hapax oddities (mygale, smigmata). Some may be spelling
  variants Words knows under another form (rhedarum ~ raeda, squallentes ~
  squalentes, braccis ~ bracae) — check before hand-writing an entry.
  Realistically ~a dozen custom lemma entries close this list.

- `gaps-names.tsv` — 3,011 unrecognized proper-name forms ("name" = the form
  is capitalized at every occurrence), sorted by frequency, with a `curated`
  column marking forms already settled in `docs/gloss/lemmas.json` by the
  hand-annotated chapters. This is the gazetteer job: group declined variants
  under one entry (jordanem/jordanis → Jordanes), and source meanings from a
  public-domain Bible-names dictionary (e.g. Hitchcock's, ~2,600 entries),
  with the curated chapters overriding as they land.

## Caveats

- A form Words recognizes is not necessarily *rightly* recognized — it
  reports candidate analyses, including flagged guesses. Recognition here
  means "would show a plausible dictionary card", not "correct".
- The name/vocabulary split is heuristic (always-capitalized ⇒ name), so a
  name that also opens sentences could be misfiled as vocabulary and vice
  versa; the 30-form vocab list was eyeballed and is clean.
- Nothing here touches the curated tier: hand-annotated chapters shadow all
  of this, form by form, as they are compiled.
