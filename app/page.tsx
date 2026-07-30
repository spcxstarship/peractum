"use client";

import { useEffect } from "react";
import { useRouter } from "next/navigation";
import { getBook } from "@/lib/bible";
import { getLastPosition } from "@/lib/storage";

export default function Home() {
  const router = useRouter();

  useEffect(() => {
    const pos = getLastPosition();
    const book = pos && getBook(pos.book);
    if (book && pos.chapter >= 1 && pos.chapter <= book.chapters.length) {
      router.replace(`/${pos.book}/${pos.chapter}`);
    } else {
      router.replace("/genesis/1");
    }
  }, [router]);

  return (
    <main className="flex flex-1 items-center justify-center">
      <div className="text-center leading-tight">
        <span className="block text-sm font-bold tracking-[0.08em]">
          PER ACTUM
        </span>
        <span className="block text-[0.6rem] tracking-[0.14em] text-muted-foreground">
          THROUGH ACTION
        </span>
      </div>
    </main>
  );
}
