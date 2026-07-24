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
