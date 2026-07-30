"use client";

import { Fragment, useEffect, useRef, useState } from "react";
import {
  glossFormKey,
  type DictEntry,
  type GlossCell,
  type GlossChapter,
  type GlossTable,
  type GlossToken,
  type Verse,
} from "@/lib/bible";
import {
  markWordHintSeen,
  wordHintSeen,
  type ReadingMode,
} from "@/lib/storage";
import { lookupDict } from "@/lib/dict";
import { cn } from "@/lib/utils";
import { englishLineClass, latinLineClass } from "@/components/interlinear";

interface ReaderProps {
  verses: Verse[];
  expanded: boolean;
  mode: ReadingMode;
  gloss: GlossChapter | null;
  /** The global dictionary serves this chapter (no curated gloss exists). */
  dict: boolean;
}

interface WordPopover {
  /** "verse:tokenIndex", marks the active word. */
  key: string;
  word: string;
  gloss: string;
  parse: string;
  lemma: string;
  /** Class line, e.g. "feminine · first declension" or "third conjugation". */
  cls: string;
  /** Part of speech, shown as the corner chip: noun, verb, adjective... */
  kind: string;
  def: string;
  count: number;
  /** Key into gloss.tables when this word has a paradigm table. */
  tableKey?: string;
  /** No lexicon entry yet: the card says so instead of not opening. */
  unglossed?: boolean;
  /** Dictionary tier: candidate analyses instead of one asserted reading. */
  entries?: DictEntry[];
  /** Grammatically linked words ("verse:index"), glowed while open. */
  related: string[];
  /** Names the glowing words' relations: "subject Deus · object cælum". */
  relationLine?: string;
  left: number;
  top: number;
}

const POP_WIDTH = 264;
const POP_EXPANDED_WIDTH = 308;
const POP_EST_HEIGHT = 172;

/**
 * Verse-level reader. The tap gesture belongs to words alone (gloss popover);
 * English translations show chapter-wide via the header's expand-all button.
 * The English is a separate block under the Latin, so toggling it never
 * reflows the Latin.
 */
export function Reader({ verses, expanded, mode, gloss, dict }: ReaderProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [pop, setPop] = useState<WordPopover | null>(null);
  const [hint, setHint] = useState(false);
  // Dictionary cards fold readings after the first behind a toggle.
  const [moreOpen, setMoreOpen] = useState(false);
  // The tap a shard fetch is answering; a newer tap makes it stale.
  const dictReq = useRef<string | null>(null);
  // When set, the popover stretches to show this paradigm table inline.
  const [table, setTable] = useState<GlossTable | null>(null);
  // Which gender's paradigm is showing, for the tables that carry chips.
  const [gender, setGender] = useState(0);

  // One-time hint that words answer a tap, shown when word data first
  // arrives; dismissed by the first word tap or after a few seconds.
  useEffect(() => {
    if ((!gloss && !dict) || wordHintSeen()) return;
    setHint(true);
    const t = setTimeout(() => {
      markWordHintSeen();
      setHint(false);
    }, 8000);
    return () => clearTimeout(t);
  }, [gloss, dict]);

  // Any tap that is not on a word dismisses the popover; tapping another
  // word moves the popover instead.
  function handleClickCapture(e: React.MouseEvent) {
    if (pop && !(e.target as HTMLElement).closest("[data-word]")) {
      e.stopPropagation();
      setPop(null);
      setTable(null);
      setGender(0);
    }
  }

  useEffect(() => {
    if (!pop && !table) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key !== "Escape") return;
      setTable(null);
      setPop(null);
    };
    document.addEventListener("keydown", onKey);
    return () => document.removeEventListener("keydown", onKey);
  }, [pop, table]);

  // Close when the chapter or mode changes (state adjustment during render).
  const [prevCtx, setPrevCtx] = useState({ verses, mode });
  if (prevCtx.verses !== verses || prevCtx.mode !== mode) {
    setPrevCtx({ verses, mode });
    setPop(null);
    setTable(null);
  }

  function toggleTable() {
    if (table) {
      setTable(null);
      return;
    }
    if (!pop?.tableKey || !gloss?.tables) return;
    const data = gloss.tables[pop.tableKey];
    if (!data) return;
    // The card widens for the table; keep it inside the text margins.
    const c = containerRef.current;
    if (c && pop.left + POP_EXPANDED_WIDTH + 8 > c.clientWidth) {
      setPop({ ...pop, left: Math.max(8, c.clientWidth - POP_EXPANDED_WIDTH - 8) });
    }
    // Open on the gender the tapped word is in; an ambiguous form lands on
    // its first reading and the chip dots point at the others.
    setGender(genderOf(data, matchKeys(pop.word, pop.parse)));
    setTable(data);
  }

  /** Open/close a dictionary reading's generated declension table. */
  function toggleDictTable(t: GlossTable) {
    if (table === t) {
      setTable(null);
      return;
    }
    const c = containerRef.current;
    if (pop && c && pop.left + POP_EXPANDED_WIDTH + 8 > c.clientWidth) {
      setPop({ ...pop, left: Math.max(8, c.clientWidth - POP_EXPANDED_WIDTH - 8) });
    }
    if (pop) setGender(genderOf(t, matchKeys(pop.word, "")));
    setTable(t);
  }

  /** Where the card sits: under the word, or above it near the fold. */
  function place(btn: HTMLElement) {
    const c = containerRef.current;
    if (!c) return null;
    const crect = c.getBoundingClientRect();
    const r = btn.getBoundingClientRect();
    return {
      left: Math.max(
        8,
        Math.min(r.left - crect.left, crect.width - POP_WIDTH - 8)
      ),
      top:
        r.bottom + POP_EST_HEIGHT + 16 < window.innerHeight
          ? r.bottom - crect.top + 6
          : r.top - crect.top - POP_EST_HEIGHT - 6,
    };
  }

  function showUnglossed(btn: HTMLElement, key: string, display: string) {
    if (pop?.key === key) {
      setPop(null);
      return;
    }
    const at = place(btn);
    if (!at) return;
    setTable(null);
    setPop({
      key,
      word: stripPunctuation(display),
      gloss: "",
      parse: "",
      lemma: "",
      cls: "",
      kind: "",
      def: "",
      count: 0,
      unglossed: true,
      related: [],
      ...at,
    });
  }

  /** Dictionary-tier tap: candidate analyses from the sharded global
      dictionary, or an honest empty card for the forms it lacks. */
  function showDictWord(btn: HTMLElement, key: string, display: string) {
    if (!dict) return;
    if (pop?.key === key) {
      setPop(null);
      return;
    }
    const at = place(btn);
    if (!at) return;
    dictReq.current = key;
    lookupDict(glossFormKey(display)).then((entry) => {
      if (dictReq.current !== key) return;   // a later tap superseded this
      if (!entry) {
        setTable(null);
        setPop({
          key,
          word: stripPunctuation(display),
          gloss: "",
          parse: "",
          lemma: "",
          cls: "",
          kind: "",
          def: "",
          count: 0,
          unglossed: true,
          related: [],
          ...at,
        });
        return;
      }
      if (hint) {
        markWordHintSeen();
        setHint(false);
      }
      setTable(null);
      setMoreOpen(false);
      setPop({
        key,
        word: stripPunctuation(display),
        gloss: "",
        parse: "",
        lemma: "",
        cls: "",
        kind: entry.e[0]?.k ?? "",
        def: "",
        count: entry.n,
        entries: entry.e,
        related: [],
        ...at,
      });
    });
  }

  function showWord(btn: HTMLElement, key: string, token: GlossToken) {
    if (!gloss) return;
    const [display, g, ov] = token;
    const formKey = glossFormKey(display);
    const form = gloss.forms[formKey];
    // A word the lexicon has not reached yet still answers the tap: a card
    // that says so beats a control that silently does nothing.
    if (!form) {
      showUnglossed(btn, key, display);
      return;
    }
    if (hint) {
      markWordHintSeen();
      setHint(false);
    }
    if (pop?.key === key) {
      setPop(null);
      setTable(null);
      setGender(0);
      return;
    }
    setTable(null);
    const at = place(btn);
    if (!at) return;
    setPop({
      key,
      word: stripPunctuation(display),
      gloss: g,
      parse: ov?.p ?? form.p,
      // A form that is two words carries the minority reading on the token,
      // so the card describes this occurrence rather than the commoner one.
      lemma: ov?.l ?? form.l,
      cls: ov?.c ?? form.c,
      kind: ov?.k ?? form.k,
      def: ov?.d ?? form.d,
      // frequency is a count of the spelling, so it is the same either way
      count: form.n,
      // stated on every override, so a null there means "no table",
      // not "fall back to the default lexeme's"
      tableKey: ov && "t" in ov ? (ov.t ?? undefined) : form.t,
      related: (ov?.r ?? []).map((j) => `${key.split(":")[0]}:${j}`),
      relationLine: ov?.rd,
      ...at,
    });
  }

  return (
    <div
      ref={containerRef}
      onClickCapture={handleClickCapture}
      className="relative mx-auto w-full max-w-3xl px-5 pt-2 pb-16"
    >
      {mode === "words" && !gloss && (
        <p className="mb-4 rounded-md bg-muted px-3 py-2 font-sans text-xs text-muted-foreground">
          {dict
            ? "Word-by-word glosses have not reached this chapter yet; tap any word for its dictionary entry."
            : "Word-by-word glosses have not reached this chapter yet."}
        </p>
      )}
      {verses.map((verse) => (
        <VerseItem
          key={verse.v}
          verse={verse}
          tokens={gloss?.verses[String(verse.v)]}
          hasDict={!!dict}
          mode={mode}
          expanded={expanded}
          activeKey={pop?.key ?? null}
          onWord={showWord}
          onDictWord={showDictWord}
        />
      ))}
      {hint && (
        <div className="fixed bottom-16 left-1/2 z-30 -translate-x-1/2 rounded-full border bg-background px-4 py-2 font-sans text-xs text-muted-foreground shadow-md animate-in fade-in duration-300">
          {gloss
            ? "Tap any word for its meaning and grammar"
            : "Tap any word for its dictionary entry"}
        </div>
      )}
      {pop && (
        <div
          role="dialog"
          aria-label={`Word detail: ${pop.word}`}
          className="absolute z-20 rounded-xl border bg-background p-3 shadow-lg"
          style={{
            left: pop.left,
            top: pop.top,
            width: table ? POP_EXPANDED_WIDTH : POP_WIDTH,
          }}
        >
          <span
            className={cn(
              "font-latin text-lg leading-tight",
              pop.unglossed && "text-muted-foreground"
            )}
          >
            {pop.word}
          </span>
          {pop.unglossed && (
            <>
              <p className="mt-0.5 font-sans text-xs text-muted-foreground">
                {gloss ? "not yet glossed" : "not in the dictionary"}
              </p>
              <div className="mt-2 border-t pt-2">
                <p className="font-latin text-sm italic leading-snug text-muted-foreground">
                  {gloss
                    ? "This chapter has word-by-word glosses; this word is not among them yet."
                    : "Not in the dictionary yet — most such words are proper names, which are still being added."}
                </p>
              </div>
            </>
          )}
          {/* Dictionary tier: the likeliest reading up front, meaning first
              — a beginner reads the English before the grammar. Readings
              after the first fold behind a toggle so an ambiguous form is a
              quiet footnote, not a wall. The card offers; the curated tier
              asserts. */}
          {pop.entries &&
            (() => {
              const [first, ...rest] = pop.entries;
              const reading = (e: DictEntry, i: number) => {
                const [sense, ...rawSenses] = e.d.split(";");
                const moreSenses = rawSenses.filter((s) => s.trim());
                return (
                  <div key={i} className="mt-2 border-t pt-2">
                    <p className="font-sans text-sm font-semibold">
                      {sense.trim()}
                    </p>
                    {moreSenses.length > 0 && (
                      <p className="font-sans text-xs text-muted-foreground">
                        also: {moreSenses.join(";").trim()}
                      </p>
                    )}
                    {e.l && (
                      <p className="mt-1 font-latin text-sm italic leading-tight">
                        {e.l}
                        {e.src === "curated" && (
                          <span className="ml-1.5 font-sans text-[9px] font-semibold tracking-[0.1em] uppercase not-italic text-brand/70">
                            hand-checked
                          </span>
                        )}
                      </p>
                    )}
                    {e.c && e.c !== e.k && (
                      <p className="font-sans text-[11px] leading-snug text-brand">
                        {e.c}
                      </p>
                    )}
                    {e.p && e.p.length > 0 && e.p.join("; ") !== e.c && (
                      <p className="mt-0.5 font-sans text-xs text-muted-foreground/80">
                        {e.p.join("; ")}
                      </p>
                    )}
                    {e.t && (
                      <button
                        type="button"
                        data-word
                        onClick={(ev) => {
                          ev.stopPropagation();
                          toggleDictTable(e.t!);
                        }}
                        className="mt-1.5 flex w-full items-center justify-between gap-2 rounded-xs text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50 active:bg-brand/10"
                      >
                        <span className="font-sans text-xs font-semibold text-brand">
                          {e.k === "verb" ? "Conjugations" : "Declensions"}
                        </span>
                        <span
                          className={cn(
                            "inline-block font-sans text-sm leading-none text-brand transition-transform duration-200",
                            table === e.t && "rotate-90"
                          )}
                        >
                          &#8250;
                        </span>
                      </button>
                    )}
                  </div>
                );
              };
              return (
                <>
                  <p className="mt-0.5 font-sans text-[10px] font-semibold tracking-[0.12em] uppercase text-muted-foreground/70">
                    dictionary
                  </p>
                  {reading(first, 0)}
                  {rest.length > 0 && (
                    <button
                      type="button"
                      data-word
                      onClick={(e) => {
                        e.stopPropagation();
                        setMoreOpen((v) => !v);
                      }}
                      className="mt-2 flex w-full items-center justify-between gap-2 border-t pt-2 rounded-xs text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50 active:bg-brand/10"
                    >
                      <span className="font-sans text-xs font-semibold text-brand">
                        {rest.length === 1
                          ? "or 1 other reading"
                          : `or ${rest.length} other readings`}
                      </span>
                      <span
                        className={cn(
                          "inline-block font-sans text-sm leading-none text-brand transition-transform duration-200",
                          moreOpen && "rotate-90"
                        )}
                      >
                        &#8250;
                      </span>
                    </button>
                  )}
                  {moreOpen && rest.map((e, i) => reading(e, i + 1))}
                </>
              );
            })()}
          {/* One grammar line: part of speech, word class, this occurrence. */}
          {!pop.unglossed && !pop.entries && (() => {
            const bits: string[] = [];
            if (pop.kind && !pop.cls.includes(pop.kind)) bits.push(pop.kind);
            if (pop.cls) bits.push(pop.cls);
            if (pop.parse && pop.parse !== pop.cls && pop.parse !== pop.kind)
              bits.push(pop.parse);
            const grammar = bits.join(" · ");
            return grammar ? (
              <p className="mt-0.5 font-sans text-xs text-muted-foreground">
                {grammar}
              </p>
            ) : null;
          })()}
          {pop.gloss && (
            <p className="font-sans text-sm font-semibold">{pop.gloss}</p>
          )}
          {pop.relationLine && (
            <p className="mt-0.5 font-sans text-xs text-muted-foreground">
              <span className="mr-1 inline-block size-1.5 translate-y-px rounded-full bg-brand/40" />
              {pop.relationLine}
            </p>
          )}
          {!pop.unglossed && !pop.entries && (
          <div className="mt-2 border-t pt-2">
            {/* Verbs and other table-less words keep the dictionary citation
                (their principal parts have nowhere else to live yet). */}
            {!pop.tableKey && (
              <p className="font-latin text-sm italic leading-tight">{pop.lemma}</p>
            )}
            <p className="font-sans text-xs text-muted-foreground">{pop.def}</p>
            {pop.tableKey && (
              <button
                type="button"
                data-word
                onClick={(e) => {
                  e.stopPropagation();
                  toggleTable();
                }}
                className="mt-1.5 flex w-full items-center justify-between gap-2 rounded-xs text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50 active:bg-brand/10"
              >
                <span className="font-sans text-xs font-semibold text-brand">
                  {tableLabel(pop.kind, pop.parse)}
                </span>
                <span
                  className={cn(
                    "inline-block font-sans text-sm leading-none text-brand transition-transform duration-200",
                    table && "rotate-90"
                  )}
                >
                  &#8250;
                </span>
              </button>
            )}
          </div>
          )}
          {table &&
            (() => {
              const keys = matchKeys(pop.word, pop.parse);
              const rows = table.g ? table.g[gender]?.[1] ?? [] : table.rows ?? [];
              const [headL, headR] = table.h ?? ["Singular", "Plural"];
              const oneColumn = headR === "";
              return (
                <div className="mt-2 border-t pt-2 animate-in fade-in duration-200">
                  {/* Lewis & Short citation: the string to look this word up
                      with in any dictionary ever printed. */}
                  <p className="font-latin text-sm italic leading-tight">
                    {table.l}
                  </p>
                  {/* Verb blocks name their mood and tense. */}
                  {table.c !== pop.cls && (
                    <p className="font-sans text-[11px] leading-snug text-brand">
                      {table.c}
                    </p>
                  )}
                  {/* Gender is a chip row, not six columns: the table under it
                      keeps the noun's shape. A dot marks a gender whose
                      paradigm also holds the word you tapped, so an ambiguous
                      form never hides behind a chip. */}
                  {table.g && (
                    <div className="mt-2 flex flex-wrap gap-1">
                      {table.g.map(([chip, chipRows], i) => (
                        <button
                          key={chip}
                          type="button"
                          data-word
                          aria-pressed={i === gender}
                          onClick={(e) => {
                            e.stopPropagation();
                            setGender(i);
                          }}
                          className={cn(
                            "rounded-full border px-2 py-0.5 font-sans text-[9px] font-semibold tracking-[0.1em] uppercase outline-none focus-visible:ring-2 focus-visible:ring-ring/50",
                            i === gender
                              ? "border-brand/40 bg-brand/10 text-brand"
                              : "text-muted-foreground"
                          )}
                        >
                          {chip}
                          {chipRows.some((r) => hit(r[1], keys) || hit(r[2], keys)) && (
                            <span className="ml-1 inline-block size-1 -translate-y-px rounded-full bg-brand align-middle" />
                          )}
                        </button>
                      ))}
                    </div>
                  )}
                  <table className="mt-1.5 w-full border-collapse font-sans">
                    <thead>
                      <tr>
                        <th></th>
                        <th className="pb-1 text-left text-[9px] font-semibold tracking-[0.12em] text-muted-foreground/70 uppercase">
                          {headL}
                        </th>
                        {!oneColumn && (
                          <th className="pb-1 text-left text-[9px] font-semibold tracking-[0.12em] text-muted-foreground/70 uppercase">
                            {headR}
                          </th>
                        )}
                      </tr>
                    </thead>
                    <tbody>
                      {rows.map(([label, sg, pl]) => (
                        <tr key={label} className="border-t border-dashed">
                          <td className="py-1 pr-2 text-[9px] font-semibold tracking-[0.1em] text-muted-foreground uppercase">
                            {label}
                          </td>
                          {(oneColumn ? [sg] : [sg, pl]).map((cell, i) => (
                            <td key={i} className="py-1 pr-2">
                              {cell ? (
                                <span
                                  className={cn(
                                    "inline-block rounded-xs px-0.5",
                                    hit(cell, keys) &&
                                      "bg-brand/10 shadow-[inset_0_-1.5px_0_0] shadow-brand",
                                    cell[1] === 0 && "opacity-40"
                                  )}
                                >
                                  <span className="font-latin text-sm leading-tight">
                                    {cell[0]}
                                  </span>
                                  <span className="block text-[9px] leading-tight text-muted-foreground/70 tabular-nums">
                                    {cell[1].toLocaleString("en-US")}
                                  </span>
                                </span>
                              ) : (
                                <span className="text-muted-foreground/40">
                                  &#8211;
                                </span>
                              )}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                  {/* What the chips would otherwise hide: cujus and cui are
                      one form for all three genders. */}
                  {table.note && (
                    <p className="mt-1.5 font-sans text-[10px] leading-snug text-muted-foreground/70">
                      {table.note}
                    </p>
                  )}
                </div>
              );
            })()}
          {!pop.unglossed && (
            <p className="mt-2 font-sans text-[10px] text-muted-foreground/70">
              {pop.count.toLocaleString("en-US")}{" "}
              {pop.count === 1 ? "occurrence" : "occurrences"} in the Vulgate
              {table && <> &#183; counts per spelling</>}
            </p>
          )}
        </div>
      )}
    </div>
  );
}

function VerseItem({
  verse,
  tokens,
  hasDict,
  mode,
  expanded,
  activeKey,
  onWord,
  onDictWord,
}: {
  verse: Verse;
  tokens: GlossToken[] | undefined;
  hasDict: boolean;
  mode: ReadingMode;
  expanded: boolean;
  activeKey: string | null;
  onWord: (btn: HTMLElement, key: string, token: GlossToken) => void;
  onDictWord: (btn: HTMLElement, key: string, display: string) => void;
}) {
  const english = verse.pairs.map((p) => p[1]).join(" ");
  // In words mode the gloss line is the English, so the same expand state
  // that reveals verse translations in verses mode shows/hides glosses here.
  const showGloss = mode === "words" && !!tokens && expanded;

  return (
    <div className="relative rounded-sm py-2.5">
      <span className={cn(latinLineClass, showGloss && "text-pretty")}>
        <VerseNumber v={verse.v} />
        {tokens
          ? tokens.map((token, i) => {
              const key = `${verse.v}:${i}`;
              const [display, g] = token;
              const lean = showGloss ? leanGloss(g) : null;
              return (
                <Fragment key={i}>
                  <button
                    type="button"
                    data-word
                    onClick={(e) => {
                      e.stopPropagation();
                      onWord(e.currentTarget, key, token);
                    }}
                    className={cn(
                      "rounded-xs text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50 active:bg-brand/10",
                      showGloss && "mb-1.5 inline-flex flex-col items-start align-top",
                      activeKey === key && "bg-brand/10"
                    )}
                  >
                    <span
                      className={cn(
                        activeKey === key && "shadow-[0_1.5px_0_0] shadow-brand"
                      )}
                    >
                      {display}
                    </span>
                    {lean && (
                      <span className="max-w-[12ch] font-sans text-[0.58em] leading-tight font-normal text-balance text-muted-foreground">
                        {lean}
                      </span>
                    )}
                  </button>{" "}
                </Fragment>
              );
            })
          : hasDict
            ? // Dictionary tier: no curated tokenization, so split the verse
              // on spaces — every word answers a tap, none is merged.
              verse.pairs
                .map((p) => p[0])
                .join(" ")
                .split(" ")
                .map((display, i) => {
                  const key = `${verse.v}:${i}`;
                  return (
                    <Fragment key={i}>
                      <button
                        type="button"
                        data-word
                        onClick={(e) => {
                          e.stopPropagation();
                          onDictWord(e.currentTarget, key, display);
                        }}
                        className={cn(
                          "rounded-xs text-left outline-none focus-visible:ring-2 focus-visible:ring-ring/50 active:bg-brand/10",
                          activeKey === key && "bg-brand/10"
                        )}
                      >
                        <span
                          className={cn(
                            activeKey === key &&
                              "shadow-[0_1.5px_0_0] shadow-brand"
                          )}
                        >
                          {display}
                        </span>
                      </button>{" "}
                    </Fragment>
                  );
                })
            : verse.pairs.map((p) => p[0]).join(" ")}
      </span>
      {/* In word-by-word mode the glosses carry the meaning, so the verse
          translation stays off entirely. */}
      {expanded && !showGloss && (
        <span
          className={cn(
            englishLineClass,
            "mt-0.5 text-muted-foreground",
            "animate-in fade-in duration-200"
          )}
        >
          {english}
        </span>
      )}
    </div>
  );
}

/**
 * The forms a table cell may match. An enclitic is fused to the word as
 * printed, so Appellavitque never appears in appello's paradigm; when the
 * parse says one is attached, the bare word counts as a match too.
 */
function matchKeys(word: string, parse: string): string[] {
  const base = word.toLowerCase();
  const enclitic = /-(que|ve|ne)\b/.exec(parse)?.[1];
  if (!enclitic) return [base];
  const bare = base.replace(new RegExp(`${enclitic}(?=\\s|$)`), "");
  return bare === base ? [base] : [base, bare];
}

/** Spelling-blind comparison: the dictionary tables are generated in
 * classical orthography while the text is Clementine (æ/œ/j). */
function normLatin(w: string): string {
  return w
    .toLowerCase()
    .replace(/æ/g, "ae")
    .replace(/œ/g, "oe")
    .replace(/j/g, "i")
    .replace(/ë/g, "e")
    .replace(/ï/g, "i");
}

function hit(cell: GlossCell, keys: string[]): boolean {
  return !!cell && keys.some((k) => normLatin(k) === normLatin(cell[0]));
}

/** The gender chip to open on: the first whose paradigm holds the word. */
function genderOf(table: GlossTable, keys: string[]): number {
  if (!table.g) return 0;
  const i = table.g.findIndex(([, rows]) =>
    rows.some((r) => hit(r[1], keys) || hit(r[2], keys))
  );
  return i < 0 ? 0 : i;
}

/** Participles decline, so their table is a declension however the word is
 * classed; the gerund is neither, and says so. */
function tableLabel(kind: string, parse: string): string {
  if (parse.includes("gerund")) return "Gerund";
  if (parse.includes("infinitive")) return "Infinitives";
  if (kind !== "verb" || parse.includes("participle")) return "Declensions";
  return "Conjugations";
}

/**
 * The gloss line drops English articles: Latin has no articles (definiteness
 * lives in the endings and context), so every "the" is the translator's
 * addition, not a Latin word. Everything Latin says with an actual word
 * (et = and, prepositions, case markers like "of") keeps its gloss; the
 * popover keeps the full CPDV phrasing, articles included.
 */
function leanGloss(gloss: string): string | null {
  const lean = gloss
    .replace(/\b(?:the|an?)\b/gi, "")
    .replace(/\s+/g, " ")
    .trim();
  return lean || null;
}

function stripPunctuation(display: string): string {
  return display
    .split(" ")
    .map((w) =>
      w.replace(/^[^\wÆæŒœëï]+/, "").replace(/[^\wÆæŒœëï]+$/, "")
    )
    .join(" ");
}

function VerseNumber({ v }: { v: number }) {
  return (
    <sup className="mr-1.5 select-none font-sans text-[0.62em] font-semibold text-brand">
      {v}
    </sup>
  );
}
