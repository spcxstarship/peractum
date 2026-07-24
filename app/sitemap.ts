import type { MetadataRoute } from "next";
import { BOOKS } from "@/lib/bible";
import { PRAYERS } from "@/lib/prayers";
import { SITE_URL } from "@/lib/site";

export const dynamic = "force-static";

export default function sitemap(): MetadataRoute.Sitemap {
  return [
    { url: SITE_URL, priority: 1 },
    { url: `${SITE_URL}/about`, priority: 0.9 },
    { url: `${SITE_URL}/faq`, priority: 0.9 },
    { url: `${SITE_URL}/orationes`, priority: 0.9 },
    ...PRAYERS.map((p) => ({
      url: `${SITE_URL}/orationes/${p.slug}`,
      priority: 0.8,
    })),
    ...BOOKS.flatMap((book) =>
      book.chapters.map((_, i) => ({
        url: `${SITE_URL}/${book.slug}/${i + 1}`,
        priority: 0.5,
      }))
    ),
  ];
}
