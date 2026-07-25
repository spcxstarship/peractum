"use client";

import { useEffect } from "react";

export function ServiceWorker() {
  useEffect(() => {
    if (process.env.NODE_ENV !== "production") return;
    if (!("serviceWorker" in navigator)) return;

    // When an updated worker takes control, reload once so the new build's
    // shell and payloads load together. The first-ever install also fires
    // controllerchange (clients.claim) — no reload needed then.
    let hadController = !!navigator.serviceWorker.controller;
    let reloading = false;
    const onControllerChange = () => {
      if (!hadController) {
        hadController = true;
        return;
      }
      if (reloading) return;
      // Rate-limit so a misbehaving update can never reload-loop.
      try {
        const last = Number(sessionStorage.getItem("peractum:swReload"));
        if (Date.now() - last < 60_000) return;
        sessionStorage.setItem("peractum:swReload", String(Date.now()));
      } catch {}
      reloading = true;
      window.location.reload();
    };
    navigator.serviceWorker.addEventListener(
      "controllerchange",
      onControllerChange
    );

    // Installed PWAs resume from memory without a page load, so the browser
    // never re-checks sw.js on its own; ask it to whenever we come to the
    // foreground.
    let checkForUpdate = () => {};
    const onVisible = () => {
      if (document.visibilityState === "visible") checkForUpdate();
    };
    document.addEventListener("visibilitychange", onVisible);

    navigator.serviceWorker
      .register("/sw.js")
      .then((reg) => {
        checkForUpdate = () => reg.update().catch(() => {});
        return navigator.serviceWorker.ready;
      })
      .then((reg) => reg.active?.postMessage({ type: "fill" }))
      .catch(() => {});

    return () => {
      navigator.serviceWorker.removeEventListener(
        "controllerchange",
        onControllerChange
      );
      document.removeEventListener("visibilitychange", onVisible);
    };
  }, []);
  return null;
}
