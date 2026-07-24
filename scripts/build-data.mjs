// Builds public/bible/ from the scrollmapper Clementine Vulgate + CPDV sources.
//
// Sources (public domain), cached in .cache/ (gitignored):
//   https://github.com/scrollmapper/bible_databases
//     sources/la/VulgClementine/VulgClementine.json
//     sources/en/CPDV/CPDV.json
//
// Output:
//   public/bible/index.json            — book metadata + per-chapter verse counts
//   public/bible/<slug>/<chapter>.json — { book, chapter, verses: [{ v, pairs: [[la, en], ...] }] }
//
// A verse's `pairs` is the interlinear clause pairing: Latin and English are
// split at punctuation, paired clause-for-clause only when the clause counts
// match; otherwise the verse is a single whole-verse pair.

import { mkdir, readFile, rm, writeFile } from "node:fs/promises";
import { existsSync } from "node:fs";
import path from "node:path";
import { BOOKS } from "./books.mjs";

const ROOT = path.join(import.meta.dirname, "..");
const CACHE = path.join(ROOT, ".cache");
const OUT = path.join(ROOT, "public", "bible");

const SOURCES = {
  "VulgClementine.json":
    "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/la/VulgClementine/VulgClementine.json",
  "CPDV.json":
    "https://raw.githubusercontent.com/scrollmapper/bible_databases/master/sources/en/CPDV/CPDV.json",
};

async function loadSource(filename) {
  const file = path.join(CACHE, filename);
  if (!existsSync(file)) {
    console.log(`Downloading ${filename}…`);
    await mkdir(CACHE, { recursive: true });
    const res = await fetch(SOURCES[filename]);
    if (!res.ok) throw new Error(`Failed to download ${filename}: ${res.status}`);
    await writeFile(file, await res.text());
  }
  return JSON.parse(await readFile(file, "utf8"));
}

// Split a verse into clauses at punctuation (, ; : . ? !), keeping the
// punctuation — plus any closing quotes/brackets that follow it — attached
// to the clause it ends.
function clauses(text) {
  const out = [];
  const re = /[^,;:.?!]+(?:[,;:.?!]+[”’"')\]]*)?/g;
  for (const m of text.matchAll(re)) {
    const clause = m[0].trim();
    if (clause) out.push(clause);
  }
  return out.length ? out : [text.trim()];
}

// When clause counts differ, align them by relative character length
// (Gale–Church style): contiguous runs of clauses may merge 1-2, 2-1, etc.
// Works because the CPDV translates the Vulgate clause-for-clause, in order.
const BEADS = [
  [1, 1, 0],
  [1, 2, 0.1],
  [2, 1, 0.1],
  [2, 2, 0.18],
  [1, 3, 0.22],
  [3, 1, 0.22],
];
const MAX_AVG_COST = 0.3;

function alignClauses(cla, cen) {
  const n = cla.length;
  const m = cen.length;
  const laLens = cla.map((s) => s.length);
  const enLens = cen.map((s) => s.length);
  const ratio =
    enLens.reduce((a, b) => a + b, 0) / laLens.reduce((a, b) => a + b, 0);

  const INF = Infinity;
  const cost = Array.from({ length: n + 1 }, () => Array(m + 1).fill(INF));
  const steps = Array.from({ length: n + 1 }, () => Array(m + 1).fill(0));
  const back = Array.from({ length: n + 1 }, () => Array(m + 1).fill(null));
  cost[0][0] = 0;

  for (let i = 0; i <= n; i++) {
    for (let j = 0; j <= m; j++) {
      if (cost[i][j] === INF) continue;
      for (const [a, b, penalty] of BEADS) {
        if (i + a > n || j + b > m) continue;
        const la = laLens.slice(i, i + a).reduce((x, y) => x + y, 0) * ratio;
        const en = enLens.slice(j, j + b).reduce((x, y) => x + y, 0);
        const d = Math.abs(en - la) / (en + la);
        const c = cost[i][j] + d + penalty;
        if (c < cost[i + a][j + b]) {
          cost[i + a][j + b] = c;
          steps[i + a][j + b] = steps[i][j] + 1;
          back[i + a][j + b] = [i, j];
        }
      }
    }
  }

  if (cost[n][m] === INF || cost[n][m] / steps[n][m] > MAX_AVG_COST) return null;

  const pairs = [];
  let i = n;
  let j = m;
  while (i > 0 || j > 0) {
    const [pi, pj] = back[i][j];
    pairs.unshift([cla.slice(pi, i).join(" "), cen.slice(pj, j).join(" ")]);
    i = pi;
    j = pj;
  }
  return pairs;
}

// Split points before coordinating conjunctions, used when one side has
// fewer punctuation clauses than the other (e.g. the CPDV renders two Latin
// clauses as one "... and ..." sentence with no comma).
const CONJUNCTIONS = {
  la: /\s+(?=(?:et|atque|ac|aut|vel|sed|neque)\s)/g,
  en: /\s+(?=(?:and|but|or|nor)\s)/g,
};

// If splitting at conjunctions produces EXACTLY the deficit, apply it —
// unambiguous. Otherwise give up and let the DP aligner handle it.
function subSplitAtConjunctions(clausesArr, targetCount, lang) {
  const re = CONJUNCTIONS[lang];
  let candidates = 0;
  const split = clausesArr.map((c) => {
    const parts = c.split(re).map((s) => s.trim()).filter(Boolean);
    candidates += parts.length - 1;
    return parts;
  });
  if (clausesArr.length + candidates !== targetCount) return null;
  return split.flat();
}

function pairVerse(la, en) {
  let cla = clauses(la);
  let cen = clauses(en);
  if (cla.length !== cen.length) {
    if (cla.length < cen.length) {
      cla = subSplitAtConjunctions(cla, cen.length, "la") ?? cla;
    } else {
      cen = subSplitAtConjunctions(cen, cla.length, "en") ?? cen;
    }
  }
  if (cla.length > 1 && cla.length === cen.length) {
    return cla.map((c, i) => [c, cen[i]]);
  }
  if (cla.length > 1 && cen.length > 1 && cla.length <= 40 && cen.length <= 40) {
    const aligned = alignClauses(cla, cen);
    if (aligned) return aligned;
  }
  return [[la.trim(), en.trim()]];
}

const [vulg, cpdv] = await Promise.all([
  loadSource("VulgClementine.json"),
  loadSource("CPDV.json"),
]);

const byName = (data) => new Map(data.books.map((b) => [b.name, b]));
const vulgBooks = byName(vulg);
const cpdvBooks = byName(cpdv);

await rm(OUT, { recursive: true, force: true });
await mkdir(OUT, { recursive: true });

const index = [];
let chapterCount = 0;
let verseCount = 0;
let clausePaired = 0;

for (const meta of BOOKS) {
  const la = vulgBooks.get(meta.dataset);
  const en = cpdvBooks.get(meta.dataset);
  if (!la || !en) throw new Error(`Missing book in sources: ${meta.dataset}`);
  if (la.chapters.length !== en.chapters.length)
    throw new Error(`Chapter count mismatch in ${meta.dataset}`);

  const verseCounts = [];
  await mkdir(path.join(OUT, meta.slug), { recursive: true });

  for (const [ci, laCh] of la.chapters.entries()) {
    const enCh = en.chapters[ci];
    const enByVerse = new Map(enCh.verses.map((v) => [v.verse, v.text]));
    const verses = laCh.verses.map((v) => {
      const enText = enByVerse.get(v.verse);
      if (enText === undefined)
        throw new Error(`Missing CPDV verse ${meta.dataset} ${laCh.chapter}:${v.verse}`);
      const pairs = pairVerse(v.text, enText);
      if (pairs.length > 1) clausePaired += 1;
      return { v: v.verse, pairs };
    });

    verseCounts.push(verses.length);
    chapterCount += 1;
    verseCount += verses.length;

    await writeFile(
      path.join(OUT, meta.slug, `${laCh.chapter}.json`),
      JSON.stringify({ book: meta.slug, chapter: laCh.chapter, verses })
    );
  }

  index.push({
    slug: meta.slug,
    latin: meta.latin,
    english: meta.english,
    group: meta.group,
    chapters: verseCounts,
  });
}

await writeFile(path.join(OUT, "index.json"), JSON.stringify(index));

console.log(
  `Built ${index.length} books, ${chapterCount} chapters, ${verseCount} verses.`
);
console.log(
  `Clause-paired verses: ${clausePaired} (${((clausePaired / verseCount) * 100).toFixed(1)}%); rest are whole-verse pairs.`
);
