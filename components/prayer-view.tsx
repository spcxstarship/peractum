"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import type { Prayer } from "@/lib/prayers";
import { InterlinearPair } from "@/components/interlinear";
import {
  ExpandAllButton,
  MobileMenu,
  ThemeToggle,
  TopBar,
} from "@/components/header";

export function PrayerView({ prayer }: { prayer: Prayer }) {
  const allKeys = prayer.sections.flatMap((s, si) =>
    s.lines.map((_, li) => `${si}:${li}`)
  );

  // English is shown by default; tapping a line hides/shows its translation.
  const [open, setOpen] = useState<Set<string>>(() => new Set(allKeys));

  useEffect(() => {
    setOpen(
      new Set(
        prayer.sections.flatMap((s, si) => s.lines.map((_, li) => `${si}:${li}`))
      )
    );
  }, [prayer]);
  const allOpen = open.size === allKeys.length;

  function toggle(key: string) {
    setOpen((prev) => {
      const next = new Set(prev);
      if (next.has(key)) next.delete(key);
      else next.add(key);
      return next;
    });
  }

  function toggleAll() {
    setOpen(allOpen ? new Set() : new Set(allKeys));
  }

  return (
    <>
      <TopBar active="orationes" />

      <div className="sticky top-0 z-10 border-b bg-background pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-5 py-2.5">
          <MobileMenu active="orationes" />
          <Link
            href="/orationes"
            aria-label="All prayers"
            className="rounded-md p-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            <ArrowLeft className="size-4" />
          </Link>
          <h1 className="px-1 font-latin text-lg font-semibold">
            {prayer.latin}
          </h1>
          <div className="ml-auto flex items-center gap-1.5">
            <ExpandAllButton allOpen={allOpen} onToggleAll={toggleAll} />
            <ThemeToggle />
          </div>
        </div>
      </div>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 pt-4 pb-16">
          <div className="flex flex-col gap-6">
            {prayer.sections.map((section, si) => (
              <div key={si} className="flex flex-col gap-1.5">
                {section.label && (
                  <div className="text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-brand">
                    {section.label}
                  </div>
                )}
                {section.lines.map(([la, en], li) => {
                  const key = `${si}:${li}`;
                  const isOpen = open.has(key);
                  return (
                    <div
                      key={key}
                      role="button"
                      tabIndex={0}
                      aria-expanded={isOpen}
                      onClick={() => toggle(key)}
                      onKeyDown={(e) => {
                        if (e.key === "Enter" || e.key === " ") {
                          e.preventDefault();
                          toggle(key);
                        }
                      }}
                      className="cursor-pointer rounded-sm outline-none focus-visible:ring-2 focus-visible:ring-ring/50"
                    >
                      <InterlinearPair la={la} en={en} showEnglish={isOpen} />
                    </div>
                  );
                })}
              </div>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
