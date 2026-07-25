import type { Metadata, Viewport } from "next";
import { Geist, EB_Garamond } from "next/font/google";
import { SITE_NAME, SITE_URL } from "@/lib/site";
import { ServiceWorker } from "@/components/service-worker";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const latinSerif = EB_Garamond({
  variable: "--font-latin-serif",
  subsets: ["latin", "latin-ext"],
  weight: ["400", "500", "600"],
  style: ["normal", "italic"],
});

export const metadata: Metadata = {
  metadataBase: new URL(SITE_URL),
  title: {
    default: "Per Actum · Read the Bible & Pray the Rosary in Latin",
    template: "%s · Per Actum",
  },
  description:
    "Learn the Latin of the Mass by reading it. The complete Clementine Vulgate Bible and the prayers of the Rosary in Latin, with English shown line-by-line under every phrase. Free, no account, open source.",
  keywords: [
    "learn Latin",
    "Latin Mass",
    "Traditional Latin Mass",
    "Church Latin",
    "Ecclesiastical Latin",
    "Latin Bible",
    "Vulgate",
    "Clementine Vulgate",
    "Latin Bible with English translation",
    "Rosary in Latin",
    "Latin prayers",
    "Pater Noster",
    "Ave Maria",
    "Catholic",
  ],
  openGraph: {
    type: "website",
    siteName: SITE_NAME,
    title: "Per Actum · Read the Bible & Pray the Rosary in Latin",
    description:
      "The complete Latin Bible (Clementine Vulgate) and the Rosary prayers with English under every phrase. Made for Catholics discovering the Latin Mass.",
    url: SITE_URL,
  },
  twitter: {
    card: "summary",
    title: "Per Actum · Read the Bible & Pray the Rosary in Latin",
    description:
      "The complete Latin Bible and the Rosary prayers with English under every phrase. Free and open source.",
  },
  appleWebApp: {
    capable: true,
    title: SITE_NAME,
    statusBarStyle: "default",
  },
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: light)", color: "#f4f1e5" },
    { media: "(prefers-color-scheme: dark)", color: "#1a1c20" },
  ],
};

// Applies stored theme and font size before first paint to avoid flashes.
const bootScript = `
try {
  var t = localStorage.getItem("peractum:theme");
  var dark = t === "dark" || ((!t || t === "system") && matchMedia("(prefers-color-scheme: dark)").matches);
  if (dark) document.documentElement.classList.add("dark");
  var tc = document.querySelectorAll('meta[name="theme-color"]');
  for (var i = 0; i < tc.length; i++) tc[i].setAttribute("content", dark ? "#1a1c20" : "#f4f1e5");
  var fs = localStorage.getItem("peractum:fs");
  if (fs) document.documentElement.setAttribute("data-fs", fs);
} catch (e) {}
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${latinSerif.variable} h-full antialiased`}
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: bootScript }} />
      </head>
      <body className="min-h-full flex flex-col">
        {children}
        <ServiceWorker />
      </body>
    </html>
  );
}
