# Word-by-word for the whole Bible — the campaign

The goal: every one of the 1,334 chapters carries a hand-quality interlinear
— per-occurrence glosses, one asserted parse, links, notes — authored by LLM
sessions, mechanically verified, and shipped as per-chapter `gloss.json`
that shadows the dictionary tier the moment it exists. The dictionary stays
the floor; this is the ceiling, spread chapter by chapter.

Ground truth from the corpus: 73 books, 611,757 tokens, mean 459 tokens per
chapter (median 430; Psalm 118 is the monster at 1,778, Psalm 116 the
smallest at 22). Zipf pays for the campaign: the top 897 forms are 66% of
all running text, the top 2,000 are 74%, the top 5,000 are 83%. Every
settled lemma makes every later chapter cheaper.

## The unit of work (unchanged in spirit, upgraded in tooling)

Per chapter, in a FRESH context (a subagent per chapter satisfies the
fresh-session rule):

1. `gloss_prep.py <book> <ch>` — the brief: charter + registry-settled
   strings + chapter text + CPDV. **Upgrade:** embed Whitaker's candidate
   analyses (from `public/dict` shards) for every form the registry has not
   settled — the annotator chooses and glosses; it should not re-derive
   morphology the analyzer already knows.
2. Annotate → `docs/gloss/<ch>-<book>.json` intermediate.
3. `compile_gloss.py` — the existing hard gate: reconstruction, citation
   consistency, tables, homograph splits. Warnings resolved, THIRD /
   HAND_VERBS extended by hand as they surface.
4. **Lint (to build, M0):** every parse must sit inside Whitaker's candidate
   set for that form; every citation head must match a known lemma or be
   explicitly flagged (names, new coinages). Catches the one error class the
   compiler cannot see — a hallucinated parse. Runs offline from the shards.
5. Registry grows; next chapter inherits.

Per book, at the end: `lemma_registry.py seed/check`, an adversarial audit
pass (separate subagent, existing audit prompt: parses vs candidates,
glosses vs CPDV sense, link overreach), fix pass, recompile, and a report
whose flagged judgment calls are the only thing a human needs to read.

## Quality tiers by genre

Two independent passes + compare was the Genesis 1–6 method; it caught real
disagreements (`qua` 5:1, `quam` 4:13) at double cost. Spend it where
judgment is dense:

- **Single-pass + lint + audit** — narrative and lists: Pentateuch stories,
  Josue–Esther, Gospels narration, Acts, genealogies (Gen 5 is 31 verses of
  one sentence; a second pass buys nothing).
- **Two-pass + compare** — poetry and argument: Psalms, Job, Canticum,
  prophets' oracles, Pauline epistles. Word order is scrambled, ellipsis is
  everywhere, links are hard.
- Either way: silence over error on links, notes for every irregular, the
  compiler as unbypassable gate.

## Order of battle

Chosen for reader value first, difficulty ramp second, registry warmth third:

| phase | scope | chapters | notes |
|---|---|---|---|
| M0 | infrastructure | — | lint; brief upgrade; STATUS manifest + campaign driver; recompile Genesis 1–6 (returns instantly) |
| M1 | Genesis 7–50 | 44 | pilot at scale; same genre the registry was grown on |
| M2 | Gospels | 89 | Mt 28, Mc 16, Lc 24, Jo 21 — the audience's texts; PROIEL NT treebank available as audit oracle |
| M3 | Acts + rest of NT | 171 | epistles are two-pass territory |
| M4 | Psalms | 150 | two-pass; hardest Latin, most-prayed text |
| M5 | OT narrative | ~400 | Exodus–Esther |
| M6 | wisdom + prophets | ~470 | Job, Isaias 66, Jeremias 52, Ecclesiasticus 51… registry is maximal by now, which is where it is needed |

## Throughput, honestly

A 459-token chapter is one focused annotator pass plus compile/lint fixes.
With chapters running as parallel fresh-context subagents inside one
driving session — annotate in parallel, compile serially (registry is
ordered) — 10–25 chapters per session is realistic for narrative, fewer for
poetry. Whole campaign: roughly **60–100 working sessions**. A
few-sessions-a-week cadence lands the Gospels in the first month or two and
the whole canon in two seasons; the tail (M6) is the biggest block but also
the cheapest per chapter, since by then almost every form is settled.

Constraint honored throughout: session-based Claude Code work only — no API
in the pipeline. Parallelism comes from subagents/workflows inside sessions,
each chapter in a clean context.

## Consistency at scale

- The registry is the single source of citation/class/definition strings;
  `--only` seeding per book, `check` after every book, conflicts adjudicated
  before the next book starts.
- Homograph splits (os/facies/cum pattern) are compiler-handled; new ones
  get notes and move on.
- The charter (conventions in the /gloss brief) is versioned; changes apply
  forward only — no retro-editing finished books over wording taste.
- Names: definitions are written from the verses in front of the annotator
  (`Irad, a son of Henoch`), exactly as Genesis did; the registry carries
  them corpus-wide and doubles as the future gazetteer for the dict tier.

## Risks and their answers

- **Hallucinated parses** → the lint (M0, non-negotiable before scaling).
- **Link overreach** → silence-over-error + audit + Michael reviewing flags,
  never the full output.
- **Wording drift between books** → registry binds l/c/d; glosses are meant
  to vary by occurrence — that is the feature.
- **Poetry quality** → two-pass tier + registry warmth by doing it after the
  Gospels, before the prophets.
- **Fatigue/dilution across a long campaign** → per-book audits, STATUS
  manifest, and the compiler's refusal to accept anything malformed.

## Definition of done, per chapter

Compiles clean; lints clean or with adjudicated exceptions; audited (its
book's pass); registry checked; shipped as `public/bible/<book>/<ch>.gloss.json`
where it silently replaces the dictionary card with the asserted reading,
the glosses, and the hand-fixed tables.
