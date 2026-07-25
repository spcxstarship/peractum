import type { Metadata } from "next";
import Link from "next/link";
import { notFound } from "next/navigation";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { adjacentPrayer, getPrayer, PRAYERS } from "@/lib/prayers";
import { FloatingNav } from "@/components/floating-nav";
import { PrayerView } from "@/components/prayer-view";
import { SwipeNav } from "@/components/swipe-nav";

interface Params {
  slug: string;
}

export const dynamicParams = false;

export function generateStaticParams(): Params[] {
  return PRAYERS.map((p) => ({ slug: p.slug }));
}

export async function generateMetadata({
  params,
}: {
  params: Promise<Params>;
}): Promise<Metadata> {
  const { slug } = await params;
  const prayer = getPrayer(slug);
  if (!prayer) return {};
  return {
    title: prayer.latin,
    description: `${prayer.english} in Latin with English translation.`,
  };
}

export default async function PrayerPage({
  params,
}: {
  params: Promise<Params>;
}) {
  const { slug } = await params;
  const prayer = getPrayer(slug);
  if (!prayer) notFound();

  const prev = adjacentPrayer(slug, -1);
  const next = adjacentPrayer(slug, 1);

  return (
    <>
      <PrayerView prayer={prayer} />
      <SwipeNav
        prevHref={prev ? `/orationes/${prev.slug}` : undefined}
        nextHref={next ? `/orationes/${next.slug}` : undefined}
      />
      <FloatingNav>
        <div>
            {prev && (
              <Link
                href={`/orationes/${prev.slug}`}
                rel="prev"
                title={prev.latin}
                aria-label={`Previous prayer: ${prev.latin}`}
                className="pointer-events-auto inline-flex rounded-full border bg-background/90 p-2.5 text-muted-foreground shadow-sm backdrop-blur hover:bg-muted hover:text-foreground"
              >
                <ChevronLeft className="size-4" />
              </Link>
            )}
          </div>
          <div>
            {next && (
              <Link
                href={`/orationes/${next.slug}`}
                rel="next"
                title={next.latin}
                aria-label={`Next prayer: ${next.latin}`}
                className="pointer-events-auto inline-flex rounded-full border bg-background/90 p-2.5 text-muted-foreground shadow-sm backdrop-blur hover:bg-muted hover:text-foreground"
              >
                <ChevronRight className="size-4" />
              </Link>
            )}
          </div>
      </FloatingNav>
    </>
  );
}
