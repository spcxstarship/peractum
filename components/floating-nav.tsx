"use client";

import { useEffect, useState } from "react";
import { cn } from "@/lib/utils";

/**
 * Fixed bottom container for the floating prev/next buttons.
 * Hides when scrolling down, reappears when scrolling up, and always stays
 * visible near the bottom of the page.
 */
export function FloatingNav({ children }: { children: React.ReactNode }) {
  const [visible, setVisible] = useState(true);

  useEffect(() => {
    let lastY = window.scrollY;
    const onScroll = () => {
      const y = window.scrollY;
      const nearBottom =
        window.innerHeight + y >=
        document.documentElement.scrollHeight - 200;
      if (nearBottom || y <= 0) {
        setVisible(true);
      } else if (y > lastY + 4) {
        setVisible(false);
      } else if (y < lastY - 4) {
        setVisible(true);
      }
      lastY = y;
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  return (
    <div
      className={cn(
        "pointer-events-none fixed inset-x-0 bottom-[max(1.25rem,env(safe-area-inset-bottom))] z-10",
        visible ? "opacity-100" : "translate-y-4 opacity-0"
      )}
      style={{
        visibility: visible ? "visible" : "hidden",
        transition:
          "opacity 250ms ease, transform 250ms ease, visibility 250ms",
      }}
    >
      <div className="mx-auto flex max-w-3xl items-center justify-between px-5">
        {children}
      </div>
    </div>
  );
}
