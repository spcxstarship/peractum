// Runs after `next build`. Walks out/ and generates:
//   out/sw-precache.json  - every URL the service worker should cache for
//                           full offline support (app shell + all chapters
//                           as RSC segment payloads)
//   out/sw.js             - the service worker with its version stamped in
//
// Excluded from the precache list:
//   - *.html chapter pages (~160 MB; navigation uses the RSC payloads instead)
//   - __next._full.txt (never requested by the client router)
//   - public/bible/*.json (build-time inputs, never fetched at runtime)
import { createHash } from "node:crypto";
import { promises as fs } from "node:fs";
import path from "node:path";

const OUT = path.join(process.cwd(), "out");

async function walk(dir) {
  const entries = await fs.readdir(dir, { withFileTypes: true });
  const files = await Promise.all(
    entries.map((e) => {
      const p = path.join(dir, e.name);
      return e.isDirectory() ? walk(p) : [p];
    })
  );
  return files.flat();
}

const all = (await walk(OUT)).map((p) => path.relative(OUT, p));

const urls = [];
for (const rel of all) {
  const url = "/" + rel.split(path.sep).join("/");
  if (url.startsWith("/bible/")) continue;
  if (url === "/sw.js" || url === "/sw-precache.json") continue;
  if (url.startsWith("/_next/")) {
    if (url.startsWith("/_next/static/")) urls.push(url);
    continue;
  }
  const base = path.basename(url);
  if (base.startsWith("__next.")) {
    // Segment payloads drive Link navigations; _full is never requested.
    if (base !== "__next._full.txt") urls.push(url);
    continue;
  }
  if (base.endsWith(".txt")) {
    // Route-level RSC payloads: router.push/replace fetches these directly.
    urls.push(url);
    continue;
  }
  if (base.endsWith(".html")) {
    // Only shell pages; chapter HTML is huge and reachable via RSC payloads.
    const depth = url.split("/").length - 1;
    if (depth > 1) continue;
    if (base === "404.html" || base === "_not-found.html") continue;
    urls.push(url === "/index.html" ? "/" : url.replace(/\.html$/, ""));
    continue;
  }
  if (/\.(png|ico|webmanifest|svg)$/.test(base)) {
    urls.push(url);
    continue;
  }
}
urls.sort();

// Version from content of everything precached: any change re-versions the
// cache and clients re-download in the background.
const hash = createHash("sha256");
for (const url of urls) {
  const rel = url === "/" ? "index.html" : url.replace(/^\//, "");
  const file = path.join(OUT, rel);
  hash.update(url);
  try {
    hash.update(await fs.readFile(file));
  } catch {
    hash.update(await fs.readFile(file + ".html"));
  }
}
const version = hash.digest("hex").slice(0, 12);

await fs.writeFile(
  path.join(OUT, "sw-precache.json"),
  JSON.stringify({ version, files: urls })
);

const sw = await fs.readFile(path.join(OUT, "sw.js"), "utf8");
await fs.writeFile(
  path.join(OUT, "sw.js"),
  sw.replace("__BUILD_VERSION__", version)
);

console.log(`sw-precache.json: ${urls.length} files, version ${version}`);
