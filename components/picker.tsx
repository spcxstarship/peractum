"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { useRouter } from "next/navigation";
import { ChevronDown, ChevronRight } from "lucide-react";
import { BOOKS, GROUP_LABELS, type BookGroup, type BookMeta } from "@/lib/bible";
import { cn } from "@/lib/utils";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Drawer, DrawerContent, DrawerHeader, DrawerTitle } from "@/components/ui/drawer";

interface PickerProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  currentBook: string;
  currentChapter: number;
  /** "books" scrolls the list; "chapters" opens with the current book expanded. */
  mode: "books" | "chapters";
}

interface PickerBodyProps extends PickerProps {
  autoFocusSearch: boolean;
}

function normalize(s: string): string {
  return s
    .toLowerCase()
    .replaceAll("æ", "ae")
    .replaceAll("œ", "oe")
    .normalize("NFD")
    .replace(/[̀-ͯ]/g, "");
}

/** Parses queries like "gen 4" / "ps 23" into a direct jump target. */
function parseReference(query: string): { book: BookMeta; chapter: number } | null {
  const m = query.trim().match(/^(.+?)\s+(\d{1,3})$/);
  if (!m) return null;
  const book = matchBooks(m[1])[0];
  if (!book) return null;
  const chapter = Number(m[2]);
  return chapter >= 1 && chapter <= book.chapters.length ? { book, chapter } : null;
}

function matchBooks(query: string): BookMeta[] {
  const q = normalize(query.trim());
  if (!q) return BOOKS;
  const starts = (name: string) =>
    normalize(name)
      .split(/\s+/)
      .some((w) => w.startsWith(q));
  const contains = (name: string) => normalize(name).includes(q);
  const score = (b: BookMeta) =>
    starts(b.latin) || starts(b.english) ? 0 : contains(b.latin) || contains(b.english) ? 1 : 2;
  return BOOKS.filter((b) => score(b) < 2).sort((a, b) => score(a) - score(b));
}

export function Picker(props: PickerProps) {
  const [isDesktop, setIsDesktop] = useState(true);
  const [finePointer, setFinePointer] = useState(false);

  useEffect(() => {
    const mqDesktop = window.matchMedia("(min-width: 768px)");
    // Touch devices (phone/tablet, incl. installed PWA) must not auto-focus
    // the search input, or the keyboard pops open over the picker.
    const mqFine = window.matchMedia("(hover: hover) and (pointer: fine)");
    const update = () => {
      setIsDesktop(mqDesktop.matches);
      setFinePointer(mqFine.matches);
    };
    update();
    mqDesktop.addEventListener("change", update);
    mqFine.addEventListener("change", update);
    return () => {
      mqDesktop.removeEventListener("change", update);
      mqFine.removeEventListener("change", update);
    };
  }, []);

  if (isDesktop) {
    return (
      <Dialog open={props.open} onOpenChange={props.onOpenChange}>
        <DialogContent className="max-w-md gap-0 p-0" aria-describedby={undefined}>
          <DialogHeader className="border-b px-4 py-3">
            <DialogTitle className="font-latin text-base font-semibold">
              Libri Bibliæ
            </DialogTitle>
          </DialogHeader>
          <PickerBody {...props} autoFocusSearch={finePointer} />
        </DialogContent>
      </Dialog>
    );
  }

  return (
    <Drawer open={props.open} onOpenChange={props.onOpenChange}>
      <DrawerContent className="h-dvh max-h-dvh rounded-none! border-t-0! pt-[env(safe-area-inset-top)]">
        <DrawerHeader className="border-b py-3">
          <DrawerTitle className="font-latin text-base font-semibold">
            Libri Bibliæ
          </DrawerTitle>
        </DrawerHeader>
        <PickerBody {...props} autoFocusSearch={false} />
      </DrawerContent>
    </Drawer>
  );
}

function PickerBody({
  open,
  onOpenChange,
  currentBook,
  currentChapter,
  mode,
  autoFocusSearch,
}: PickerBodyProps) {
  const router = useRouter();
  const [query, setQuery] = useState("");
  const [expanded, setExpanded] = useState<string | null>(
    mode === "chapters" ? currentBook : null
  );
  const listRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (!open) return;
    setQuery("");
    setExpanded(mode === "chapters" ? currentBook : null);
  }, [open, mode, currentBook]);

  // Scroll the current chapter (or book) into view when the sheet opens.
  useEffect(() => {
    if (!open) return;
    const id = requestAnimationFrame(() => {
      const list = listRef.current;
      const target =
        list?.querySelector("[data-now=true]") ??
        list?.querySelector("[data-current=true]");
      target?.scrollIntoView({ block: "center" });
    });
    return () => cancelAnimationFrame(id);
  }, [open]);

  const reference = useMemo(() => parseReference(query), [query]);
  const matches = useMemo(() => matchBooks(query.replace(/\s+\d+$/, "")), [query]);
  const filtering = query.trim().length > 0;

  function go(book: string, chapter: number) {
    onOpenChange(false);
    router.push(`/${book}/${chapter}`);
  }

  function onEnter() {
    if (reference) {
      go(reference.book.slug, reference.chapter);
    } else if (filtering && matches.length > 0) {
      setExpanded(matches[0].slug);
    }
  }

  const groups: BookGroup[] = ["vetus", "novum"];

  return (
    <div className="flex min-h-0 flex-col">
      <div className="border-b px-4 py-3">
        <input
          ref={inputRef}
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              onEnter();
            }
          }}
          placeholder="Quaerere… (e.g. “gen 4”, “ps 23”)"
          // 16px minimum on touch — iOS zooms the page when focusing smaller inputs.
          className="w-full rounded-md border bg-muted/50 px-3 py-2 text-base outline-none placeholder:text-muted-foreground/70 focus:ring-2 focus:ring-ring/40 md:text-sm"
          enterKeyHint="go"
          autoFocus={autoFocusSearch}
        />
        {reference && (
          <button
            onClick={() => go(reference.book.slug, reference.chapter)}
            className="mt-2 w-full rounded-md bg-brand px-3 py-2 text-left text-sm font-medium text-primary-foreground"
          >
            Ire ad {reference.book.latin} {reference.chapter} ↵
          </button>
        )}
      </div>

      <div
        ref={listRef}
        className="min-h-0 flex-1 overflow-y-auto overscroll-contain px-2 pt-1 pb-[max(0.5rem,env(safe-area-inset-bottom))] md:max-h-[60vh] md:pb-1"
      >
        {groups.map((group) => {
          const books = matches.filter((b) => b.group === group);
          if (books.length === 0) return null;
          return (
            <div key={group}>
              {!filtering && (
                <div className="px-2 pt-3 pb-1 text-[0.68rem] font-semibold uppercase tracking-[0.12em] text-brand">
                  {GROUP_LABELS[group]}
                </div>
              )}
              {books.map((book) => {
                const isExpanded = expanded === book.slug;
                const isCurrent = book.slug === currentBook;
                return (
                  <div key={book.slug} data-current={isCurrent} data-book={book.slug}>
                    <button
                      onClick={() => {
                        const next = isExpanded ? null : book.slug;
                        setExpanded(next);
                        if (next) {
                          requestAnimationFrame(() => {
                            listRef.current
                              ?.querySelector(`[data-book="${next}"]`)
                              ?.scrollIntoView({ block: "nearest" });
                          });
                        }
                      }}
                      className={cn(
                        "flex w-full items-baseline gap-2 rounded-md px-2 py-2.5 text-left hover:bg-muted md:py-2",
                        isExpanded && "text-brand"
                      )}
                    >
                      <span className="font-latin text-[0.95rem] font-semibold">
                        {book.latin}
                      </span>
                      <span className="text-xs text-muted-foreground">
                        {book.english} · {book.chapters.length}
                      </span>
                      <span className="ml-auto text-muted-foreground">
                        {isExpanded ? (
                          <ChevronDown className="size-3.5" />
                        ) : (
                          <ChevronRight className="size-3.5" />
                        )}
                      </span>
                    </button>
                    {isExpanded && (
                      <div className="mb-2 rounded-md px-2 py-1">
                        <div className="grid grid-cols-6 gap-2 md:grid-cols-10 md:gap-1.5">
                          {book.chapters.map((_, i) => {
                            const ch = i + 1;
                            const isNow = isCurrent && ch === currentChapter;
                            return (
                              <button
                                key={ch}
                                data-now={isNow}
                                onClick={() => go(book.slug, ch)}
                                className={cn(
                                  "rounded-md border py-2.5 text-center text-[0.8rem] tabular-nums hover:bg-muted md:py-1.5 md:text-xs",
                                  isNow &&
                                    "border-brand bg-brand font-bold text-primary-foreground hover:bg-brand"
                                )}
                              >
                                {ch}
                              </button>
                            );
                          })}
                        </div>
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          );
        })}
        {filtering && matches.length === 0 && (
          <p className="px-3 py-6 text-center text-sm text-muted-foreground">
            Nihil inventum.
          </p>
        )}
      </div>
    </div>
  );
}
