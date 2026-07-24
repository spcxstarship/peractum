"use client";

import { useEffect, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { adjacentChapter, type BookMeta, type Verse } from "@/lib/bible";
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
  const router = useRouter();
  const touchStart = useRef<{ x: number; y: number } | null>(null);

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

  // Swipe left/right anywhere in the reader to change chapter (mobile).
  function onTouchStart(e: React.TouchEvent) {
    const t = e.touches[0];
    touchStart.current = { x: t.clientX, y: t.clientY };
  }

  function onTouchEnd(e: React.TouchEvent) {
    const start = touchStart.current;
    touchStart.current = null;
    if (!start) return;
    const t = e.changedTouches[0];
    const dx = t.clientX - start.x;
    const dy = t.clientY - start.y;
    if (Math.abs(dx) < 70 || Math.abs(dy) > 60) return;
    const target = adjacentChapter(book.slug, chapter, dx < 0 ? 1 : -1);
    if (target) router.push(`/${target.book.slug}/${target.chapter}`);
  }

  return (
    <>
      <Header
        book={book}
        chapter={chapter}
        allOpen={allOpen}
        onToggleAll={toggleAll}
      />
      <main
        className="flex-1"
        onTouchStart={onTouchStart}
        onTouchEnd={onTouchEnd}
      >
        <Reader verses={verses} selected={selected} onToggle={toggle} />
      </main>
    </>
  );
}
