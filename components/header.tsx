"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import {
  Check,
  ChevronDown,
  Eclipse,
  Languages,
  Maximize2,
  Menu,
  Minimize2,
} from "lucide-react";
import type { BookMeta } from "@/lib/bible";
import { applyTheme, syncThemeColor, type ReadingMode } from "@/lib/storage";
import { cn } from "@/lib/utils";
import { Picker } from "@/components/picker";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetTrigger,
} from "@/components/ui/sheet";

export type Section = "biblia" | "orationes" | "about" | "faq";

interface HeaderProps {
  book: BookMeta;
  chapter: number;
  allOpen: boolean;
  onToggleAll: () => void;
  mode: ReadingMode;
  onModeChange: (mode: ReadingMode) => void;
}

export function Header({
  book,
  chapter,
  allOpen,
  onToggleAll,
  mode,
  onModeChange,
}: HeaderProps) {
  const [pickerOpen, setPickerOpen] = useState(false);

  return (
    <>
      <TopBar active="biblia" />

      <div className="sticky top-0 z-10 border-b bg-background pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-5 py-2.5">
          <MobileMenu active="biblia" />
          <button
            onClick={() => setPickerOpen(true)}
            className="flex items-center gap-1.5 rounded-md px-1 font-latin text-lg font-semibold outline-none hover:text-brand focus-visible:ring-2 focus-visible:ring-ring/50"
          >
            {book.latin} {chapter}
            <ChevronDown className="size-4 text-muted-foreground" />
          </button>
          <div className="ml-auto flex items-center gap-1.5">
            <ModeMenu mode={mode} onModeChange={onModeChange} />
            <ExpandAllButton allOpen={allOpen} onToggleAll={onToggleAll} />
            <ThemeToggle />
          </div>
        </div>
      </div>

      <Picker
        open={pickerOpen}
        onOpenChange={setPickerOpen}
        currentBook={book.slug}
        currentChapter={chapter}
        mode="chapters"
      />
    </>
  );
}

export function TopBar({ active }: { active: Section }) {
  return (
    <div className="hidden border-b pt-[env(safe-area-inset-top)] sm:block">
      <div className="mx-auto flex max-w-3xl items-center gap-6 px-5 py-3">
        <Link href="/" className="leading-tight">
          <span className="block text-sm font-bold tracking-[0.08em]">
            PER ACTUM
          </span>
          <span className="block text-[0.6rem] tracking-[0.14em] text-muted-foreground">
            THROUGH ACTION
          </span>
        </Link>
        <nav className="ml-auto flex items-center gap-5 text-sm">
          <NavItem href="/" isActive={active === "biblia"}>
            Biblia Sacra
          </NavItem>
          <NavItem href="/orationes" isActive={active === "orationes"}>
            Orationes
          </NavItem>
          <NavItem href="/about" isActive={active === "about"}>
            About
          </NavItem>
          <NavItem href="/faq" isActive={active === "faq"}>
            FAQ
          </NavItem>
        </nav>
      </div>
    </div>
  );
}

function NavItem({
  href,
  isActive,
  children,
}: {
  href: string;
  isActive: boolean;
  children: React.ReactNode;
}) {
  if (isActive) {
    return (
      <span className="border-b-2 border-brand pb-0.5 font-semibold">
        {children}
      </span>
    );
  }
  return (
    <Link
      href={href}
      className="text-muted-foreground hover:text-foreground"
    >
      {children}
    </Link>
  );
}

export function MobileMenu({ active }: { active: Section }) {
  return (
    <Sheet>
      <SheetTrigger
        aria-label="Menu"
        className="mr-1 rounded-md p-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50 sm:hidden"
      >
        <Menu className="size-4" />
      </SheetTrigger>
      <SheetContent side="left" className="w-64 pt-[env(safe-area-inset-top)]">
        <SheetHeader className="pb-0">
          <SheetTitle className="leading-tight">
            <span className="block text-sm font-bold tracking-[0.08em]">
              PER ACTUM
            </span>
            <span className="block text-[0.6rem] font-normal tracking-[0.14em] text-muted-foreground">
              THROUGH ACTION
            </span>
          </SheetTitle>
        </SheetHeader>
        <nav className="flex flex-col gap-1 px-4">
          <MenuItem
            href="/"
            isActive={active === "biblia"}
            latin="Biblia Sacra"
            english="Holy Bible"
          />
          <MenuItem
            href="/orationes"
            isActive={active === "orationes"}
            latin="Orationes"
            english="Prayers"
          />
          <MenuItem
            href="/about"
            isActive={active === "about"}
            latin="About"
            english="The story & the source"
          />
          <MenuItem
            href="/faq"
            isActive={active === "faq"}
            latin="FAQ"
            english="Common questions"
          />
        </nav>
      </SheetContent>
    </Sheet>
  );
}

function MenuItem({
  href,
  isActive,
  latin,
  english,
}: {
  href: string;
  isActive: boolean;
  latin: string;
  english: string;
}) {
  return (
    <Link
      href={href}
      className={cn(
        "rounded-md px-3 py-2 hover:bg-muted",
        isActive && "bg-muted"
      )}
    >
      <span
        className={cn("block text-sm", isActive ? "font-semibold" : undefined)}
      >
        {latin}
      </span>
      <span className="block text-xs text-muted-foreground">{english}</span>
    </Link>
  );
}

const MODES: { value: ReadingMode; label: string; hint: string }[] = [
  { value: "verses", label: "Verse by verse", hint: "Expand for the English" },
  { value: "words", label: "Word by word", hint: "A gloss under each word" },
];

export function ModeMenu({
  mode,
  onModeChange,
}: {
  mode: ReadingMode;
  onModeChange: (mode: ReadingMode) => void;
}) {
  return (
    <DropdownMenu>
      <DropdownMenuTrigger
        title="Modus legendi"
        aria-label="Reading mode"
        className="rounded-md p-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
      >
        <Languages className="size-4" />
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {MODES.map((item) => (
          <DropdownMenuItem
            key={item.value}
            onClick={() => onModeChange(item.value)}
          >
            <span className="flex-1">
              <span
                className={cn(
                  "block text-sm",
                  mode === item.value && "font-semibold"
                )}
              >
                {item.label}
              </span>
              <span className="block text-xs text-muted-foreground">
                {item.hint}
              </span>
            </span>
            {mode === item.value && <Check className="size-4 text-brand" />}
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function ExpandAllButton({
  allOpen,
  onToggleAll,
}: {
  allOpen: boolean;
  onToggleAll: () => void;
}) {
  return (
    <button
      onClick={onToggleAll}
      title={allOpen ? "Colligere omnia" : "Expandere omnia"}
      aria-label={allOpen ? "Collapse all" : "Expand all"}
      className="rounded-md p-1.5 text-muted-foreground outline-none hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
    >
      {allOpen ? (
        <Minimize2 className="size-4" />
      ) : (
        <Maximize2 className="size-4" />
      )}
    </button>
  );
}

export function ThemeToggle() {
  const [dark, setDark] = useState<boolean | null>(null);

  useEffect(() => {
    setDark(document.documentElement.classList.contains("dark"));
    syncThemeColor();
  }, []);

  function toggle() {
    const next = !dark;
    setDark(next);
    applyTheme(next ? "dark" : "light");
  }

  return (
    <button
      onClick={toggle}
      title={dark ? "Lux" : "Nox"}
      aria-label={dark ? "Switch to light mode" : "Switch to dark mode"}
      className="rounded-md p-1.5 text-muted-foreground outline-none transition-transform duration-300 hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring/50"
      style={{ transform: dark ? "rotate(180deg)" : "rotate(0deg)" }}
    >
      <Eclipse className="size-4" />
    </button>
  );
}
