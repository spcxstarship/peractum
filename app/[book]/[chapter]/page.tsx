import { promises as fs } from "node:fs";
import path from "node:path";
import type { Metadata } from "next";
import { notFound } from "next/navigation";
import { BOOKS, getBook, type ChapterData } from "@/lib/bible";
import { ChapterView } from "@/components/chapter-view";
import { Pager } from "@/components/pager";

interface Params {
  book: string;
  chapter: string;
}

export const dynamicParams = false;

export function generateStaticParams(): Params[] {
  return BOOKS.flatMap((book) =>
    book.chapters.map((_, i) => ({
      book: book.slug,
      chapter: String(i + 1),
    }))
  );
}

async function loadChapter(slug: string, chapter: number): Promise<ChapterData> {
  const file = path.join(process.cwd(), "public", "bible", slug, `${chapter}.json`);
  return JSON.parse(await fs.readFile(file, "utf8"));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { book: slug, chapter } = await params;
  const book = getBook(slug);
  if (!book) return {};
  return {
    title: `${book.latin} ${chapter}`,
    description: `${book.english} ${chapter} in Latin (Clementine Vulgate) with English translation (CPDV).`,
  };
}

export default async function ChapterPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { book: slug, chapter: chapterParam } = await params;
  const book = getBook(slug);
  const chapter = Number(chapterParam);
  if (!book || !Number.isInteger(chapter) || chapter < 1 || chapter > book.chapters.length) {
    notFound();
  }

  const data = await loadChapter(slug, chapter);

  return (
    <>
      <ChapterView book={book} chapter={chapter} verses={data.verses} />
      <Pager book={book} chapter={chapter} />
    </>
  );
}
