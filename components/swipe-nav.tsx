"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";

interface SwipeNavProps {
  prevHref?: string;
  nextHref?: string;
}

// Reserved for iOS back/forward edge gestures; touches starting here are ignored.
const EDGE = 32;
// Vertical drift past this marks the gesture as a scroll and abandons it.
const AXIS_SLOP = 12;
// A flick must travel at least this far...
const MIN_DISTANCE = 70;
// ...and average at least this speed (px/ms) over the whole gesture, unless it
// went FAR_FRACTION of the screen. Whole-gesture speed is used because WebKit
// delivers coalesced touchmoves in bursts whose per-move timestamps are
// unreliable; start-to-end time is honest.
const MIN_VELOCITY = 0.3;
const FAR_FRACTION = 0.45;

/**
 * Renders nothing; makes a horizontal flick anywhere on the page navigate to
 * the previous/next reading. Swipe left = next, right = previous, mirroring
 * the floating chevrons. Vertical scrolling, text selection, open dialogs,
 * and OS edge gestures all take precedence.
 */
export function SwipeNav({ prevHref, nextHref }: SwipeNavProps) {
  const router = useRouter();

  useEffect(() => {
    if (!prevHref && !nextHref) return;

    let tracking = false;
    let startX = 0;
    let startY = 0;
    let startT = 0;

    function onTouchStart(e: TouchEvent) {
      tracking = false;
      if (e.touches.length !== 1) return;
      const t = e.touches[0];
      if (t.clientX < EDGE || t.clientX > window.innerWidth - EDGE) return;
      if ((e.target as Element | null)?.closest?.('[role="dialog"]')) return;
      // Radix disables body pointer events while a sheet/drawer is open.
      if (document.body.style.pointerEvents === "none") return;
      tracking = true;
      startX = t.clientX;
      startY = t.clientY;
      startT = e.timeStamp;
    }

    function onTouchMove(e: TouchEvent) {
      if (!tracking) return;
      if (e.touches.length !== 1) {
        tracking = false;
        return;
      }
      const t = e.touches[0];
      const dx = t.clientX - startX;
      const dy = t.clientY - startY;
      if (Math.abs(dy) > AXIS_SLOP && Math.abs(dy) > Math.abs(dx)) {
        tracking = false;
      }
    }

    function onTouchEnd(e: TouchEvent) {
      if (!tracking) return;
      tracking = false;
      const sel = window.getSelection();
      if (sel && !sel.isCollapsed) return;
      const dx = e.changedTouches[0].clientX - startX;
      const duration = e.timeStamp - startT;
      const fast =
        Math.abs(dx) >= MIN_DISTANCE &&
        duration > 0 &&
        Math.abs(dx) / duration >= MIN_VELOCITY;
      const far = Math.abs(dx) >= window.innerWidth * FAR_FRACTION;
      if (!fast && !far) return;
      const href = dx < 0 ? nextHref : prevHref;
      if (href) router.push(href);
    }

    function onTouchCancel() {
      tracking = false;
    }

    window.addEventListener("touchstart", onTouchStart, { passive: true });
    window.addEventListener("touchmove", onTouchMove, { passive: true });
    window.addEventListener("touchend", onTouchEnd, { passive: true });
    window.addEventListener("touchcancel", onTouchCancel, { passive: true });
    return () => {
      window.removeEventListener("touchstart", onTouchStart);
      window.removeEventListener("touchmove", onTouchMove);
      window.removeEventListener("touchend", onTouchEnd);
      window.removeEventListener("touchcancel", onTouchCancel);
    };
  }, [router, prevHref, nextHref]);

  return null;
}
