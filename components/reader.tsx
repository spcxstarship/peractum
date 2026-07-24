"use client";

import { useLayoutEffect, useRef, useState } from "react";
import type { Verse } from "@/lib/bible";
import { ClauseBlock, InterlinearPair } from "@/components/interlinear";

interface ReaderProps {
  verses: Verse[];
  selected: Set<number>;
  onToggle: (v: number) => void;
}

export function Reader({ verses, selected, onToggle }: ReaderProps) {
  return (
    <div className="mx-auto w-full max-w-3xl px-5 pt-2 pb-16">
      {verses.map((verse) => (
        <VerseItem
          key={verse.v}
          verse={verse}
          isSelected={selected.has(verse.v)}
          onToggle={() => onToggle(verse.v)}
        />
      ))}
    </div>
  );
}

/**
 * Renders a verse as interlinear clause blocks. Line breaks are computed from
 * a hidden copy laid out WITH the English widths, so the clause-to-line
 * grouping is identical whether the English is shown or not: toggling only
 * stretches the spacing within each line, never moves a clause to another line.
 */
function VerseItem({
  verse,
  isSelected,
  onToggle,
}: {
  verse: Verse;
  isSelected: boolean;
  onToggle: () => void;
}) {
  const measureRef = useRef<HTMLParagraphElement>(null);
  const [rows, setRows] = useState<number[][] | null>(null);

  useLayoutEffect(() => {
    const el = measureRef.current;
    if (!el) return;

    const compute = () => {
      const children = Array.from(el.children) as HTMLElement[];
      const grouped: number[][] = [];
      let lastTop = Number.NEGATIVE_INFINITY;
      children.forEach((child, i) => {
        if (Math.abs(child.offsetTop - lastTop) > 1) {
          grouped.push([i]);
          lastTop = child.offsetTop;
        } else {
          grouped[grouped.length - 1].push(i);
        }
      });
      setRows(grouped);
    };

    compute();
    const observer = new ResizeObserver(compute);
    observer.observe(el);
    return () => observer.disconnect();
  }, [verse]);

  const visibleRows = rows ?? [verse.pairs.map((_, i) => i)];

  return (
    <div
      role="button"
      tabIndex={0}
      aria-expanded={isSelected}
      onClick={onToggle}
      onKeyDown={(e) => {
        if (e.key === "Enter" || e.key === " ") {
          e.preventDefault();
          onToggle();
        }
      }}
      className="relative cursor-pointer rounded-sm py-2.5 outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
    >
      {/* Hidden measuring copy: always includes the English, so it wraps the
          way the expanded state will. */}
      <p
        ref={measureRef}
        aria-hidden
        className="invisible absolute inset-x-0 top-0 -z-10"
      >
        {verse.pairs.map(([la, en], i) => (
          <ClauseBlock key={i}>
            <InterlinearPair
              la={la}
              en={en}
              showEnglish
              animateIn={false}
              latinPrefix={i === 0 ? <VerseNumber v={verse.v} /> : undefined}
            />
          </ClauseBlock>
        ))}
      </p>

      {visibleRows.map((row, ri) => (
        <p key={ri}>
          {row.map((i) => {
            const [la, en] = verse.pairs[i];
            return (
              <ClauseBlock key={i}>
                <InterlinearPair
                  la={la}
                  en={en}
                  showEnglish={isSelected}
                  latinPrefix={
                    i === 0 ? <VerseNumber v={verse.v} /> : undefined
                  }
                />
              </ClauseBlock>
            );
          })}
        </p>
      ))}
    </div>
  );
}

function VerseNumber({ v }: { v: number }) {
  return (
    <sup className="mr-1.5 select-none font-sans text-[0.62em] font-semibold text-brand">
      {v}
    </sup>
  );
}
