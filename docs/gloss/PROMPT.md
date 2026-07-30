# The pass-2 prompt

In a **fresh** session, type:

```
Read docs/gloss/REDO.md and follow it for Genesis 1, 2 and 3.
```

Then, in another fresh session:

```
Read docs/gloss/REDO.md and follow it for Genesis 4, 5 and 6.
```

That is the whole prompt. Every rule it needs — don't read pass 1's copy of
the chapter you're on, the chapter-2 exemplar swap, regenerate the brief each
time, compile as you go, compare only at the end, don't commit — lives in
`REDO.md` so it cannot be lost in a paste.

All six in one session works too (`… for Genesis 1 through 6`), at about 410k
tokens of a 1M window. Two sessions of three is safer: the last chapter still
gets a reasonably fresh context, and a mid-run auto-compaction can't strand
the later chapters on a summary.
