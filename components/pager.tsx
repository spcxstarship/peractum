import Link from "next/link";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { adjacentChapter, type BookMeta } from "@/lib/bible";
import { FloatingNav } from "@/components/floating-nav";
import { SwipeNav } from "@/components/swipe-nav";

interface PagerProps {
  book: BookMeta;
  chapter: number;
}

export function Pager({ book, chapter }: PagerProps) {
  const prev = adjacentChapter(book.slug, chapter, -1);
  const next = adjacentChapter(book.slug, chapter, 1);

  return (
    <>
      <SwipeNav
        prevHref={prev ? `/${prev.book.slug}/${prev.chapter}` : undefined}
        nextHref={next ? `/${next.book.slug}/${next.chapter}` : undefined}
      />
      <FloatingNav>
        <div>
          {prev && (
            <Link
              href={`/${prev.book.slug}/${prev.chapter}`}
              rel="prev"
              title={`${prev.book.latin} ${prev.chapter}`}
              aria-label={`Previous chapter: ${prev.book.latin} ${prev.chapter}`}
              className="pointer-events-auto inline-flex rounded-full border bg-background/90 p-2.5 text-muted-foreground shadow-sm backdrop-blur hover:bg-muted hover:text-foreground"
            >
              <ChevronLeft className="size-4" />
            </Link>
          )}
        </div>
        <div>
          {next && (
            <Link
              href={`/${next.book.slug}/${next.chapter}`}
              rel="next"
              title={`${next.book.latin} ${next.chapter}`}
              aria-label={`Next chapter: ${next.book.latin} ${next.chapter}`}
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
