import type { Metadata } from "next";
import Link from "next/link";
import { MobileMenu, ThemeToggle, TopBar } from "@/components/header";
import { REPO_URL, SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "Learn Latin Through the Mass, the Bible & the Rosary",
  description:
    "Why Per Actum exists: a free, open-source way for Catholics discovering the Latin Mass to learn Latin by reading the Vulgate Bible and praying the Rosary in Latin, with English under every phrase.",
  alternates: { canonical: `${SITE_URL}/about` },
};

export default function AboutPage() {
  return (
    <>
      <TopBar active="about" />

      <div className="sticky top-0 z-10 border-b bg-background/90 pt-[env(safe-area-inset-top)] backdrop-blur">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-5 py-2.5">
          <MobileMenu active="about" />
          <h1 className="px-1 font-latin text-lg font-semibold">About</h1>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </div>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-[42rem] px-5 pt-6 pb-16">
          <article className="flex flex-col gap-4 leading-relaxed">
            <h2 className="font-latin text-2xl font-semibold">
              Learn Latin the way the Church speaks it
            </h2>
            <p>
              <em>Per actum</em> means “through the act.” This project began with a
              simple frustration: discovering the Latin Mass and wanting to
              actually <em>understand</em> the words: not just follow along in
              a missal, but know what <em>Pater noster, qui es in cælis</em>{" "}
              means as naturally as English. Latin courses start with grammar
              drills and Caesar; I wanted to start with the words I was already
              hearing and praying every week.
            </p>
            <p>
              So Per Actum takes the opposite approach: read the real texts
              first. The complete Latin Bible (the Clementine Vulgate, the
              Church&apos;s traditional text) with the English meaning sitting
              directly under every Latin phrase, and the prayers of the Rosary
              formatted the way they are actually said aloud. Tap any line to
              hide or reveal the English. Over time, you stop needing it.
            </p>
            <p>
              There is no account, no streak, no paywall. The site is a fully
              static page that remembers your reading position in your own
              browser, and the whole thing is open source: the code is MIT
              licensed and the texts are public domain, so anyone can inspect
              it, improve it, or host their own copy.
            </p>
            <p className="text-sm text-muted-foreground">
              Built by Michael. Source code, issues, and contributions:{" "}
              <a
                href={REPO_URL}
                target="_blank"
                rel="noopener noreferrer"
                className="text-brand underline underline-offset-2 hover:opacity-80"
              >
                github.com/spcxstarship/peractum
              </a>
            </p>

            <p className="mt-6 text-sm text-muted-foreground">
              Start anywhere:{" "}
              <Link href="/genesis/1" className="text-brand underline underline-offset-2">
                Genesis 1
              </Link>
              ,{" "}
              <Link href="/joannes/1" className="text-brand underline underline-offset-2">
                the Gospel of John
              </Link>
              , or{" "}
              <Link href="/orationes" className="text-brand underline underline-offset-2">
                the Rosary prayers
              </Link>
              .
            </p>
          </article>
        </div>
      </main>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "WebApplication",
            name: "Per Actum",
            url: SITE_URL,
            applicationCategory: "EducationalApplication",
            operatingSystem: "Web",
            offers: { "@type": "Offer", price: "0" },
            description:
              "Read the complete Latin Bible (Clementine Vulgate) and pray the Rosary in Latin, with English shown under every phrase. Free and open source, made for Catholics learning the Latin of the Mass.",
          }),
        }}
      />
    </>
  );
}
