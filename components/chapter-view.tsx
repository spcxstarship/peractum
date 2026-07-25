"use client";

import { useEffect, useState } from "react";
import { type BookMeta, type Verse } from "@/lib/bible";
import { savePosition } from "@/lib/storage";
import { Header } from "@/components/header";
import { Reader } from "@/components/reader";

interface ChapterViewProps {
  book: BookMeta;
  chapter: number;
  verses: Verse[];
}

export function ChapterView({ book, chapter, verses }: ChapterViewProps) {
  // English is shown by default; tapping a verse hides/shows its translation.
  const [selected, setSelected] = useState<Set<number>>(
    () => new Set(verses.map((v) => v.v))
  );
  useEffect(() => {
    savePosition(book.slug, chapter);
  }, [book.slug, chapter]);

  useEffect(() => {
    setSelected(new Set(verses.map((v) => v.v)));
  }, [verses]);

  const allOpen = selected.size === verses.length;

  function toggle(v: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(v)) next.delete(v);
      else next.add(v);
      return next;
    });
  }

  function toggleAll() {
    setSelected(allOpen ? new Set() : new Set(verses.map((v) => v.v)));
  }

  return (
    <>
      <Header
        book={book}
        chapter={chapter}
        allOpen={allOpen}
        onToggleAll={toggleAll}
      />
      <main className="flex-1">
        <Reader verses={verses} selected={selected} onToggle={toggle} />
      </main>
    </>
  );
}
