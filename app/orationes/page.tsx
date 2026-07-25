import type { Metadata } from "next";
import Link from "next/link";
import { ChevronRight } from "lucide-react";
import { PRAYERS } from "@/lib/prayers";
import { MobileMenu, ThemeToggle, TopBar } from "@/components/header";

export const metadata: Metadata = {
  title: "Orationes",
  description:
    "Traditional Catholic prayers in Latin with English translation: everything needed to pray the Rosary.",
};

export default function OrationesPage() {
  return (
    <>
      <TopBar active="orationes" />

      <div className="sticky top-0 z-10 border-b bg-background pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-5 py-2.5">
          <MobileMenu active="orationes" />
          <h1 className="px-1 font-latin text-lg font-semibold">Orationes</h1>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </div>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-3xl px-5 pt-6 pb-10">
          <p className="mb-5 text-sm text-muted-foreground">
            The prayers of the Rosary, in praying order. Tap a line for its
            English.
          </p>
          <div className="flex flex-col">
            {PRAYERS.map((prayer) => (
              <Link
                key={prayer.slug}
                href={`/orationes/${prayer.slug}`}
                className="flex items-baseline gap-3 border-b border-border/60 py-3.5 hover:bg-muted/40"
              >
                <span className="font-latin text-[1.05rem] font-semibold">
                  {prayer.latin}
                </span>
                <span className="text-xs text-muted-foreground">
                  {prayer.english}
                </span>
                <ChevronRight className="ml-auto size-3.5 self-center text-muted-foreground" />
              </Link>
            ))}
          </div>
        </div>
      </main>
    </>
  );
}
