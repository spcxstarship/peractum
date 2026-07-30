import index from "@/public/bible/index.json";

export type BookGroup = "vetus" | "novum";

export interface BookMeta {
  slug: string;
  latin: string;
  english: string;
  group: BookGroup;
  /** Verse count per chapter; length = number of chapters. */
  chapters: number[];
}

export interface Verse {
  v: number;
  /** Interlinear clause pairs: [latin, english][] */
  pairs: [string, string][];
}

export interface ChapterData {
  book: string;
  chapter: number;
  verses: Verse[];
}

/**
 * Word-gloss data for one chapter (served from <book>/<chapter>.gloss.json,
 * absent for chapters that have not been glossed yet).
 *
 * verses: verse number -> tokens in text order. Each token is
 *   [display, gloss] or [display, gloss, overrides]; display keeps original
 *   punctuation and may span two words for periphrastics ("facta est").
 * forms: cleaned form -> default parse/lemma/definition and its corpus-wide
 *   occurrence count; per-token overrides (e.g. a different parse in one
 *   verse) ride on the token itself.
 *
 * A handful of forms are two words — os is bone in Genesis 2 and mouth in
 * Genesis 4, cum is a preposition and a conjunction. The commoner reading is
 * the form's entry above; the other arrives as l/c/k/d/t on its own tokens,
 * so the card shows the word actually in front of the reader.
 */
export type GlossToken =
  | [string, string]
  | [
      string,
      string,
      {
        g?: string;
        p?: string;
        r?: number[];
        rd?: string;
        /** This occurrence belongs to a different lexeme than the form's default. */
        l?: string;
        c?: string;
        k?: string;
        d?: string;
        t?: string | null;
      },
    ];

/** One cell: the form and how often that spelling occurs in the Vulgate, or
 * null where the paradigm has no such form. */
export type GlossCell = [string, number] | null;
/** [row label, left column, right column] — cases for a declension, persons
 * for a conjugation block. */
export type GlossRow = [string, GlossCell, GlossCell];

/**
 * A paradigm. Nouns and verb blocks carry `rows` directly; adjectives,
 * participles and pronouns decline in three genders, which will not fit in
 * six columns, so they carry `g` and the card renders a chip per gender.
 */
export interface GlossTable {
  l: string;
  c: string;
  rows?: GlossRow[];
  /** [chip label, rows] per gender. */
  g?: [string, GlossRow[]][];
  /** Column headers when they are not Singular/Plural; an empty second
   * header means the table has one column (the gerund). */
  h?: [string, string];
  /** Generated line naming what the chips hide (forms shared by every
   * gender), or another fact the table alone would not show. */
  note?: string;
}

export interface GlossChapter {
  verses: Record<string, GlossToken[]>;
  forms: Record<
    string,
    { p: string; l: string; c: string; k: string; d: string; n: number; t?: string }
  >;
  tables?: Record<string, GlossTable>;
}

/**
 * Dictionary-tier data for one chapter (<book>/<chapter>.dict.json, built by
 * scripts/build_dict.py from Whitaker's Words). Unlike the curated gloss
 * this asserts nothing about the occurrence in front of the reader: each
 * form carries *candidate* analyses — the reader picks from context, as with
 * a printed dictionary. A candidate with src "curated" carries the
 * hand-annotated chapters' citation and definition strings; a candidate with
 * an empty `l` is a pronoun the analyzer knows only by its forms.
 */
export interface DictEntry {
  l: string;
  c: string;
  k: string;
  d: string;
  p?: string[];
  src?: "curated";
}

export interface DictChapter {
  book: string;
  chapter: number;
  forms: Record<string, { n: number; e: DictEntry[] }>;
}

/** Strip punctuation and lowercase, matching the gloss build script. */
export function glossFormKey(display: string): string {
  return display
    .split(" ")
    .map((w) => w.replace(/^[^\wÆæŒœëï]+/, "").replace(/[^\wÆæŒœëï]+$/, ""))
    .join(" ")
    .toLowerCase();
}

export const BOOKS = index as BookMeta[];

const bySlug = new Map(BOOKS.map((b) => [b.slug, b]));

export function getBook(slug: string): BookMeta | undefined {
  return bySlug.get(slug);
}

export const GROUP_LABELS: Record<BookGroup, string> = {
  vetus: "Vetus Testamentum",
  novum: "Novum Testamentum",
};

/** The chapter before/after the given one, crossing book boundaries. */
export function adjacentChapter(
  slug: string,
  chapter: number,
  dir: -1 | 1
): { book: BookMeta; chapter: number } | null {
  const book = bySlug.get(slug);
  if (!book) return null;
  const target = chapter + dir;
  if (target >= 1 && target <= book.chapters.length) {
    return { book, chapter: target };
  }
  const i = BOOKS.indexOf(book) + dir;
  const next = BOOKS[i];
  if (!next) return null;
  return { book: next, chapter: dir === 1 ? 1 : next.chapters.length };
}
