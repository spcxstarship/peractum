# Per Actum · [peractum.org](https://peractum.org)

**Read the Bible and pray the Rosary in Latin.** Per Actum is a free, open-source
web app for Catholics discovering the Latin Mass who want to actually learn the
language, by reading and praying the real texts instead of starting from
grammar tables.

*Per actum*: "through the act."

## What it does

- **The complete Latin Bible**, the Clementine Vulgate (1592), the Church's
  traditional text: all 73 books, 1,334 chapters, 35,817 verses, each one a
  pre-rendered page (e.g. `/genesis/1`, `/joannes/3`).
- **Interlinear English under every phrase.** Each verse is split into clauses
  and paired with the Catholic Public Domain Version (CPDV), a modern English
  translation made directly from the same Latin text. Tap a verse to hide or
  reveal its English; toggle the whole chapter at once.
- **The prayers of the Rosary** (Orationes): Sign of the Cross, Apostles'
  Creed, Our Father, Hail Mary, Glory Be, Fatima Prayer, Salve Regina, and the
  closing prayer, broken into spoken phrases with the leader/response division
  marked.
- **No account, no tracking, no server.** The site is fully static; your
  reading position and theme live in your own browser.

## Stack

- [Next.js](https://nextjs.org) App Router with static export: every chapter
  and prayer is a pre-rendered HTML page
- [Tailwind CSS](https://tailwindcss.com) + [shadcn/ui](https://ui.shadcn.com)
- TypeScript, EB Garamond for the Latin

## Development

```sh
npm install
npm run dev    # http://localhost:3000
npm run build  # static export to out/
npm run data   # regenerate public/bible/ from the source texts
```

The generated `public/bible/` data is committed, so `npm run data` is only
needed when changing the pipeline (`scripts/build-data.mjs`). The script
downloads the raw source texts into `.cache/` (gitignored) on first run.

## How the interlinear pairing works

At build time each verse of the Vulgate and the CPDV is split into clauses at
punctuation. When the clause counts match, they pair one-to-one. When they
differ, the pipeline first tries splitting at coordinating conjunctions (only
when that resolves the mismatch unambiguously), then falls back to a
Gale–Church-style alignment that merges adjacent clauses by relative length.
Verses that still cannot be paired confidently render as a single whole-verse
pair, never a wrong pairing. About 94% of verses pair at clause level.

## Data provenance & licensing

Source texts come from
[scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
(`sources/la/VulgClementine`, `sources/en/CPDV`). Both the Clementine Vulgate
and the CPDV are in the public domain, as are the traditional Latin prayers.

Code is licensed under the [MIT License](LICENSE).

## Roadmap

- Word-level glosses and grammar notes
- Progressive memorization mode for the prayers
- More prayers and the Ordinary of the Mass
- Douay-Rheims as an optional second translation
- Audio

Contributions welcome. Open an issue or PR at
[github.com/spcxstarship/peractum](https://github.com/spcxstarship/peractum).
