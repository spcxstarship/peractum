import type { Metadata } from "next";
import Link from "next/link";
import { MobileMenu, ThemeToggle, TopBar } from "@/components/header";
import { SITE_URL } from "@/lib/site";

export const metadata: Metadata = {
  title: "FAQ · Learning Latin with the Vulgate & the Rosary",
  description:
    "Common questions about learning the Latin of the Mass: which Latin Bible to read, how to pray the Rosary in Latin, and how Per Actum works.",
  alternates: { canonical: `${SITE_URL}/faq` },
};

const FAQ = [
  {
    q: "How can I learn the Latin used at the Latin Mass?",
    a: "The fastest way is to read and pray the actual texts. Per Actum gives you the complete Latin Bible (the Clementine Vulgate, the Church's traditional text) and the prayers of the Rosary, with the English meaning directly under every Latin phrase. You absorb vocabulary and phrasing exactly as the Church uses them, instead of starting from abstract grammar tables.",
  },
  {
    q: "What Latin Bible does Per Actum use?",
    a: "The Clementine Vulgate (1592), the official Latin Bible of the Catholic Church for nearly four centuries and the text behind the traditional Latin Mass and classic Latin prayers. The English shown beneath it is the Catholic Public Domain Version (CPDV), a modern translation made directly from the same Latin text, so every line genuinely corresponds.",
  },
  {
    q: "Can I pray the Rosary in Latin with this app?",
    a: "Yes. The Orationes section contains every prayer needed for the Rosary: the Sign of the Cross, Apostles' Creed, Our Father, Hail Mary, Glory Be, Fatima Prayer, Salve Regina, and the closing prayer. Each is broken into spoken phrases with the English underneath and marked where the leader and response divide.",
  },
  {
    q: "Is Per Actum free?",
    a: "Completely. There is no account, no tracking, and no payment. The site is static, your reading position stays in your own browser, and the entire project is open source under the MIT license. The biblical and prayer texts are public domain.",
  },
  {
    q: "Do I need to know any Latin to start?",
    a: "No. Open any chapter and every phrase has its English directly beneath it. Hide the English on a verse when you want to test yourself, and bring it back with a tap.",
  },
];

export default function FaqPage() {
  return (
    <>
      <TopBar active="faq" />

      <div className="sticky top-0 z-10 border-b bg-background pt-[env(safe-area-inset-top)]">
        <div className="mx-auto flex max-w-3xl items-center gap-2 px-5 py-2.5">
          <MobileMenu active="faq" />
          <h1 className="px-1 font-latin text-lg font-semibold">FAQ</h1>
          <div className="ml-auto">
            <ThemeToggle />
          </div>
        </div>
      </div>

      <main className="flex-1">
        <div className="mx-auto w-full max-w-[42rem] px-5 pt-6 pb-16">
          <div className="flex flex-col gap-5">
            {FAQ.map((item) => (
              <div key={item.q}>
                <h2 className="font-semibold">{item.q}</h2>
                <p className="mt-1 text-sm leading-relaxed text-muted-foreground">
                  {item.a}
                </p>
              </div>
            ))}
          </div>
          <p className="mt-8 text-sm text-muted-foreground">
            Ready to start?{" "}
            <Link
              href="/genesis/1"
              className="text-brand underline underline-offset-2"
            >
              Open Genesis 1
            </Link>{" "}
            or{" "}
            <Link
              href="/orationes"
              className="text-brand underline underline-offset-2"
            >
              the Rosary prayers
            </Link>
            .
          </p>
        </div>
      </main>

      <script
        type="application/ld+json"
        dangerouslySetInnerHTML={{
          __html: JSON.stringify({
            "@context": "https://schema.org",
            "@type": "FAQPage",
            mainEntity: FAQ.map((item) => ({
              "@type": "Question",
              name: item.q,
              acceptedAnswer: { "@type": "Answer", text: item.a },
            })),
          }),
        }}
      />
    </>
  );
}
