import { cn } from "@/lib/utils";

/**
 * Shared interlinear formatting: a Latin phrase with its English translation
 * directly beneath. Used by the Bible reader (clause blocks) and the prayers
 * (recitation lines) so the typography stays identical everywhere.
 *
 * Latin is the text: serif, reading size. English is the help: smaller sans,
 * muted. Both wrap balanced so a too-long phrase never orphans a single word.
 */

export const latinLineClass =
  "block text-balance font-latin leading-snug text-[length:var(--reading-size)]";

export const englishLineClass =
  "block text-balance font-sans text-[0.78em] leading-snug";

interface InterlinearPairProps {
  la: string;
  en: string;
  showEnglish: boolean;
  /** Fade the English in when it appears (off for hidden measuring copies). */
  animateIn?: boolean;
  /** Rendered before the Latin text (e.g. a verse number). */
  latinPrefix?: React.ReactNode;
}

export function InterlinearPair({
  la,
  en,
  showEnglish,
  animateIn = true,
  latinPrefix,
}: InterlinearPairProps) {
  return (
    <>
      <span className={latinLineClass}>
        {latinPrefix}
        {la}
      </span>
      {showEnglish && (
        <span
          className={cn(
            englishLineClass,
            "text-muted-foreground",
            animateIn && "animate-in fade-in duration-200"
          )}
        >
          {en}
        </span>
      )}
    </>
  );
}

/** Inline-flowing wrapper for one clause pair in the Bible reader. */
export function ClauseBlock({ children }: { children: React.ReactNode }) {
  return (
    <span className="mr-2 inline-block max-w-full align-top">{children}</span>
  );
}
