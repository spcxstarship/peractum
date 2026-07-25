// localStorage helpers. All access is guarded so SSR/prerender never touches it.

const POS = "peractum:pos";
const READ = "peractum:read";

function get(key: string): string | null {
  if (typeof window === "undefined") return null;
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
}

function set(key: string, value: string) {
  if (typeof window === "undefined") return;
  try {
    localStorage.setItem(key, value);
  } catch {
    // storage unavailable (private mode etc.); reading still works
  }
}

/** Last global position, e.g. { book: "genesis", chapter: 3 }. */
export function getLastPosition(): { book: string; chapter: number } | null {
  const raw = get(POS);
  if (!raw) return null;
  const [book, ch] = raw.split("/");
  const chapter = Number(ch);
  return book && Number.isInteger(chapter) && chapter >= 1
    ? { book, chapter }
    : null;
}

export function savePosition(book: string, chapter: number) {
  set(POS, `${book}/${chapter}`);
  set(`${POS}:${book}`, String(chapter));
  const read = getReadChapters();
  read.add(`${book}/${chapter}`);
  set(READ, JSON.stringify([...read]));
}

/** Last-read chapter within a given book (1 if never opened). */
export function getBookPosition(book: string): number {
  const n = Number(get(`${POS}:${book}`));
  return Number.isInteger(n) && n >= 1 ? n : 1;
}

/** Set of "book/chapter" strings the user has opened. */
export function getReadChapters(): Set<string> {
  try {
    const raw = get(READ);
    return new Set(raw ? (JSON.parse(raw) as string[]) : []);
  } catch {
    return new Set();
  }
}

export type FontSize = "s" | "m" | "l";
export type Theme = "light" | "dark" | "system";

export function getFontSize(): FontSize {
  const v = get("peractum:fs");
  return v === "s" || v === "l" ? v : "m";
}

export function applyFontSize(fs: FontSize) {
  set("peractum:fs", fs);
  document.documentElement.setAttribute("data-fs", fs);
}

export function getTheme(): Theme {
  const v = get("peractum:theme");
  return v === "light" || v === "dark" ? v : "system";
}

export function applyTheme(theme: Theme) {
  set("peractum:theme", theme);
  const dark =
    theme === "dark" ||
    (theme === "system" &&
      window.matchMedia("(prefers-color-scheme: dark)").matches);
  document.documentElement.classList.toggle("dark", dark);
  syncThemeColor();
}

/**
 * The theme-color metas follow the system scheme, but the app theme can be
 * set independently; the PWA status bar reads the meta, so keep it in sync.
 */
export function syncThemeColor() {
  const dark = document.documentElement.classList.contains("dark");
  const color = dark ? "#1a1c20" : "#f4f1e5";
  // Mutate the parse-time meta in place: iOS Safari ignores both inserted
  // metas and media-qualified ones for runtime status-bar updates.
  document
    .querySelectorAll('meta[name="theme-color"]')
    .forEach((m) => m.setAttribute("content", color));
  document.documentElement.style.backgroundColor = color;
}
