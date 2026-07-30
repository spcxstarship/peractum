"use client";

import { useEffect, useState } from "react";
import {
  type BookMeta,
  type GlossChapter,
  type Verse,
} from "@/lib/bible";
import {
  getReadingMode,
  savePosition,
  saveReadingMode,
  type ReadingMode,
} from "@/lib/storage";
import { Header } from "@/components/header";
import { Reader } from "@/components/reader";

interface ChapterViewProps {
  book: BookMeta;
  chapter: number;
  verses: Verse[];
}

export function ChapterView({ book, chapter, verses }: ChapterViewProps) {
  // Reading mode sets the granularity (whole verses or word glosses).
  // "expanded" is "English visible" chapter-wide: verse translations in
  // verses mode (default hidden), gloss lines in words mode (default shown).
  // The header's expand/collapse-all button is the only toggle — verses
  // themselves don't answer taps, keeping the tap gesture for words. Stored
  // preference is read after mount (SSR-safe).
  const [mode, setMode] = useState<ReadingMode>("verses");
  const [expanded, setExpanded] = useState(false);
  const [gloss, setGloss] = useState<GlossChapter | null>(null);
  // The global dictionary serves any chapter without a curated gloss; the
  // flag flips once the gloss fetch has come back empty, so a hand-annotated
  // chapter never flashes dictionary behavior while its gloss loads.
  const [dictReady, setDictReady] = useState(false);

  useEffect(() => {
    setMode(getReadingMode());
  }, []);

  useEffect(() => {
    savePosition(book.slug, chapter);
  }, [book.slug, chapter]);

  // Reset per-chapter state when the chapter or mode changes (state
  // adjustment during render, per the React docs, instead of an effect).
  const [prev, setPrev] = useState({ mode, verses });
  if (prev.mode !== mode || prev.verses !== verses) {
    setPrev({ mode, verses });
    setExpanded(mode === "words");
    if (prev.verses !== verses) {
      setGloss(null);
      setDictReady(false);
    }
  }

  // The hand-annotated gloss is a per-chapter file; chapters without one
  // fall back to the global sharded dictionary (candidate analyses from
  // Whitaker's Words), fetched shard by shard as words are tapped.
  useEffect(() => {
    let cancelled = false;
    fetch(`/bible/${book.slug}/${chapter}.gloss.json`)
      .then((r) => (r.ok ? r.json() : null))
      .then((g) => {
        if (cancelled) return;
        if (g) setGloss(g);
        else setDictReady(true);
      })
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [book.slug, chapter]);

  function toggleAll() {
    setExpanded((prev) => !prev);
  }

  function changeMode(next: ReadingMode) {
    saveReadingMode(next);
    setMode(next);
  }

  return (
    <>
      <Header
        book={book}
        chapter={chapter}
        allOpen={expanded}
        onToggleAll={toggleAll}
        mode={mode}
        onModeChange={changeMode}
      />
      <main className="flex-1">
        <Reader
          verses={verses}
          expanded={expanded}
          mode={mode}
          gloss={gloss}
          dict={dictReady}
        />
      </main>
    </>
  );
}
