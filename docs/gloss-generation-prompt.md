# Per Actum — gloss generation prompt

**The normal way to run this is `/gloss <book> <chapter>` in a fresh Claude
Code chat** — `scripts/gloss_prep.py` assembles everything below the rule
together with the chapter's Latin and CPDV English, and the command compiles
and verifies the result afterwards. This file stays the single source of truth
for the conventions; edit it here, not in the command.

To drive a model by hand instead, paste everything below the rule (one chapter
per run), fill the two placeholders at the bottom with the chapter's Clementine
Latin and its CPDV English, and attach `docs/gen2-output.json` as the reference.

---

You are a Latin philologist annotating the Clementine Vulgate for Per Actum, a
word-by-word Bible reader for beginners learning ecclesiastical Latin. Your
annotations power three things: a one-line English gloss under each Latin word,
a grammar card that opens when the word is tapped, and a glow system that
lights up the word's grammatical partners in the verse.

You will be given one chapter of Latin text with its CPDV English translation
(for sense reference only — never copy its phrasing into glosses). Produce one
JSON object annotating every word of every verse.

A complete audited chapter in exactly this format is attached
(`docs/gen2-output.json`, Genesis 2). When any convention below feels
ambiguous, imitate it exactly — it always wins over your own habits.

## Output format

Return only a JSON object, no commentary:

```json
{
  "book": "<slug>",
  "chapter": <n>,
  "verses": {
    "1": {
      "tokens": [
        {"w": "In", "g": "in", "p": "preposition with the ablative or accusative",
         "l": "in", "c": "preposition", "d": "in, into, on"},
        ...
      ],
      "links": [[0, 1, "w"], [2, 3, "s"], [2, 4, "o"], [2, 6, "o"]]
    },
    "2": { ... }
  },
  "notes": ["<any irregular paradigms encountered — see §7>"]
}
```

Per token:
- `w` — the word exactly as printed, punctuation included (`"terram."`, `"abyssi:"`)
- `g` — the English gloss for this occurrence
- `p` — the parse in plain words
- `l` — the dictionary citation
- `c` — the class (declension / conjugation / part of speech)
- `d` — a short dictionary definition of the lemma

`links` is a list of `[head, dep, type]` triples using 0-based token indexes
within that verse.

## 1. Tokenization

- Split on spaces. Each token keeps its original punctuation and capitalization
  in `w`. The tokens of a verse, joined with single spaces, must reproduce the
  verse text **character for character**. This is checked mechanically; a
  mismatch rejects the whole chapter.
- **Merge periphrastic verb forms into one token** when two words are one verb:
  perfect passives (`creatus est`), perfects of fio (`facta est`, `factum est`,
  `factumque est`). The merged token's `w` contains both words
  (`"facta est"`), and its `p` explains: `"perfect of fio: two words, one
  verb"`. Do not merge anything else (not `cum` + noun, not esse + participle
  used adjectivally).
- Never merge or split for any other reason. Enclitic `-que` stays fused to its
  word as printed; note it in the parse: `"perfect, third singular, with -que
  (and) fused on"`.

## 2. Glosses (`g`)

The gloss says what the Latin says, with words — a reader stacking the glosses
should hear the Latin's own structure, not polished English.

- English articles (the/a/an) are allowed and encouraged where natural; the app
  strips them at render time in word-by-word mode.
- `et` and fused `-que` are always glossed ("and") — Latin has a word for and.
- Case is expressed with English function words: genitive "of the …", dative
  "to/for the …", ablative of means/place as the context demands ("by", "in",
  "with", or bare).
- Gloss the **occurrence**, not the lemma. The same form may need different
  glosses in different verses: in Genesis 1, `terra` is "the earth" in v.1 but
  "the land" in vv.11–12 where God names the dry land; `cæli` is "of heaven" in
  v.14 but "of the air" in vv.28/30 (birds); `lignum` is "trees" (collective)
  in v.11.
- Passives are glossed as passives ("was brought", not "moved"). Subjunctives
  carry their force ("let there be", "so that they may divide").
- Keep it to the fewest words that are honest. No parenthetical alternatives.

## 3. Parses (`p`)

Plain English words, lowercase, no abbreviations, comma-separated phrases.

- **Nouns**: case + number only — `"ablative singular"`, `"nominative plural"`.
  (Gender lives in the class field, not the parse.)
- **Adjectives, participles, pronouns**: case + number + **gender** —
  `"nominative singular feminine"`, `"accusative plural neuter, relative
  pronoun"`. Gender is required here because the form's agreement is the
  lesson. Add role notes after a comma where they teach something:
  `"accusative singular neuter, adjective used as a noun"`.
- **Verbs**: tense (+ voice if passive) + person/number — `"perfect, third
  singular"`, `"imperfect passive, third singular"`, `"present subjunctive,
  third singular"`. Participles parse as adjectives with the participle named:
  `"accusative singular feminine, present participle"`.

  The build reads the block out of these words, so use them and no synonyms:

  | slot | write exactly one of |
  |------|----------------------|
  | tense | `present` · `imperfect` · `future` · `perfect` · `pluperfect` · `future perfect` |
  | mood | (nothing, for the indicative) · `subjunctive` · `imperative` · `infinitive` |
  | voice | (nothing, for the active) · `passive` |
  | non-finite | `present participle` · `perfect participle` · `gerund` · `supine` |

  A form whose parse omits its tense gets no conjugation table. Anything after
  the person and number is free prose and is ignored by the build, so
  `"imperfect subjunctive, third plural, expressing purpose"` is fine.
- **Indeclinables**: name the part of speech and what governs or is governed —
  `"preposition with the accusative"`, `"conjunction"`, `"adverb"`. Add
  behavior notes that help a beginner: `"conjunction, always second in its
  clause"` (autem, enim).

## 4. Citations (`l`) and classes (`c`)

- Orthography is **Clementine**: æ and œ ligatures, consonantal j
  (`jaceo`, `ejus`), no macrons anywhere.
- **Nouns**: nominative, full genitive, gender letter — `"terra, terræ, f."`,
  `"spiritus, spiritus, m."`. Class: gender word + Roman-numeral declension —
  `"feminine · I declension"`, `"neuter · III declension"`. Plural-only nouns
  append `" · plural only"`.
- **Adjectives**: the standard forms — three-termination `"bonus, bona,
  bonum"`, two-termination `"inanis, inane"`, one-termination with genitive
  (`"felix, felicis"`). Class: `"I-II declension"` or `"III declension"`.
  Comparatives cite both terminations (`"melior, melius"`) with class
  `"comparative"`. **The build declines the adjective from this citation**, so
  a missing or non-standard second form costs the whole table.
- **Pronouns**: the citation must be the conventional full set —
  `"qui, quæ, quod"`, `"hic, hæc, hoc"`, `"ille, illa, illud"`,
  `"is, ea, id"`, `"ipse, ipsa, ipsum"`, `"iste, ista, istud"`,
  `"quis, quid"`, `"ego"`, `"tu"`, `"sui"`. Pronouns follow no rule and their
  tables are written out by hand against exactly these strings; a citation
  that differs by a character gets no table.
- **Verbs**: all principal parts — `"creo, creare, creavi, creatus"`, deponents
  `"fio, fieri, factus sum"`. Class: `"I conjugation"` … `"IV conjugation"`, or
  `"irregular"` (sum, fero, fio, eo, volo and compounds). Cite every principal
  part that exists; defective verbs cite what exists (`"vireo, virere,
  virui"` — no supine).
  - The build conjugates from the citation, so the **first** principal part
    decides the pattern: a third-conjugation verb in `-io` must be cited
    `"facio, facere, feci, factus"`, never `"faco"`.
  - Mark deponents in the class — `"III conjugation · deponent"` — and cite
    them with the passive infinitive (`"vescor, vesci"`,
    `"egredior, egredi, egressus sum"`). A deponent's stem is taken off that
    infinitive, so it must be exact.
  - Compounds of sum, fero, eo and fio are conjugated from their parent, which
    means both parts must show the compound: `"circumeo, circumire, circumivi,
    circumitus"`, `"præsum, præesse, præfui"`.
- **Indeclinables**: the word itself is the citation (`"et"`, `"super"`); class
  names the part of speech.
- The same lemma must receive the identical citation string at every
  occurrence in the chapter — the build collapses them into one dictionary
  entry and any variance is flagged as an error.

## 5. Definitions (`d`)

One short line, one to three senses, comma-separated: `"earth, land"`,
`"to carry, to bear"`. This is the dictionary meaning of the lemma, not the
contextual gloss.

## 6. Links — the tap rules

When a reader taps a word, its partners glow and the card names the relation.
The card and the glow are generated mechanically from your `links` — you only
supply the triples. The charter:

1. **Only link what is certain.** Silence over error. If a construction is
   ambiguous or you are less than sure, omit the link — a missing glow is a
   small loss, a wrong glow teaches a false rule.
2. Link **within the verse only**, by token index (0-based, counted after
   merges).
3. Direction matters. `[head, dep, type]`:

   | type | head | dep | meaning |
   |------|------|-----|---------|
   | `s` | verb | subject | who does it |
   | `o` | verb | direct object | done to what |
   | `d` | verb | indirect object | done for/to whom |
   | `g` | possessed noun | genitive | `spiritus Dei` → `[spiritus, Dei, "g"]` — the genitive is the **owner** |
   | `a` | noun | adjective/participle agreeing with it | `terra inanis` → `[terra, inanis, "a"]` |
   | `w` | preposition | its object | `super aquas` → `[super, aquas, "w"]` |
   | `c` | subordinating conjunction | the verb it governs | `ut dividant` → `[ut, dividant, "c"]` — explains the subjunctive |

4. Every verb links to each of its subjects, objects, and recipients that are
   present **as words in the verse**. Implied subjects (inside the verb ending)
   get no link. A verb with two coordinated objects links to both. A subject
   shared by two verbs links from both verbs.
5. Appositions and predicate nominatives after esse count as `a` only when the
   agreement is real and visible; otherwise omit.
6. Vocatives, interjections, and plain adverbs are normally unlinked.
7. Genitive chains: link each genitive to the noun it depends on, not to the
   top of the chain (`faciem abyssi` → faciem owns the link, even though
   faciem is itself inside `super faciem`).

## 7. Irregular paradigms (`notes`)

The build generates declension **and conjugation** tables mechanically from
your citations. Flag anything that would break a mechanical paradigm, one
string per item:

- Heteroclites and irregular plurals: `"cælum: plural is cæli/cælos
  (masculine)"`, `"locus: plural loca (neuter)"`
- First-declension -abus datives/ablatives: `"anima: dative/ablative plural
  animabus"`
- Third-declension i-stems and notable genitive plurals: `"mare: ablative
  singular mari, genitive plural marium"`
- Homographs that collide with another lexeme: `"maribus is also from mas,
  maris (male)"`
- **Verbs whose forms a regular pattern would get wrong**: irregular presents
  (`"volo, velle: present vis, vult, vultis"`), syncopated perfects
  (`"patrarat is syncopated for patraverat"`), suppletive stems, verbs with no
  perfect or no supine in use (`"vado: defective, no perfect or supine"`), and
  irregular imperatives (`"facio: imperative fac, not face"`).
- **Adjectives that are not regular**: pronominal genitives and datives
  (`"solus: genitive solius, dative soli"`), suppletive comparison
  (`"melior is the comparative of bonus; superlative optimus"`), indeclinable
  numerals (`"quatuor: indeclinable"`).
- **Anything welded together**: `"uterque: uter declines and -que stays
  fixed; this -que is not the enclitic 'and'"`.

The build warns loudly for any verb, adjective or pronoun it cannot table, so
a note here is what turns a silent gap into a fixable one.

If nothing is irregular, return `"notes": []`.

## 8. Exemplar — Genesis 1:1–3 in this exact format

```json
{
  "1": {
    "tokens": [
      {"w": "In", "g": "in", "p": "preposition with the ablative or accusative", "l": "in", "c": "preposition", "d": "in, into, on"},
      {"w": "principio", "g": "the beginning", "p": "ablative singular", "l": "principium, principii, n.", "c": "neuter · II declension", "d": "beginning, origin"},
      {"w": "creavit", "g": "created", "p": "perfect, third singular", "l": "creo, creare, creavi, creatus", "c": "I conjugation", "d": "to create"},
      {"w": "Deus", "g": "God", "p": "nominative singular", "l": "Deus, Dei, m.", "c": "masculine · II declension", "d": "God"},
      {"w": "cælum", "g": "heaven", "p": "accusative singular", "l": "cælum, cæli, n.", "c": "neuter · II declension", "d": "heaven, sky"},
      {"w": "et", "g": "and", "p": "conjunction", "l": "et", "c": "conjunction", "d": "and, also"},
      {"w": "terram.", "g": "the earth", "p": "accusative singular", "l": "terra, terræ, f.", "c": "feminine · I declension", "d": "earth, land"}
    ],
    "links": [[0, 1, "w"], [2, 3, "s"], [2, 4, "o"], [2, 6, "o"]]
  },
  "2": {
    "tokens": [
      {"w": "Terra", "g": "the earth", "p": "nominative singular", "l": "terra, terræ, f.", "c": "feminine · I declension", "d": "earth, land"},
      {"w": "autem", "g": "but", "p": "conjunction, always second in its clause", "l": "autem", "c": "conjunction", "d": "but, moreover"},
      {"w": "erat", "g": "was", "p": "imperfect, third singular", "l": "sum, esse, fui", "c": "irregular", "d": "to be"},
      {"w": "inanis", "g": "empty", "p": "nominative singular feminine", "l": "inanis, inane", "c": "III declension", "d": "empty, void"},
      {"w": "et", "g": "and", "p": "conjunction", "l": "et", "c": "conjunction", "d": "and, also"},
      {"w": "vacua,", "g": "unoccupied", "p": "nominative singular feminine", "l": "vacuus, vacua, vacuum", "c": "I-II declension", "d": "empty, unoccupied"},
      {"w": "et", "g": "and", "p": "conjunction", "l": "et", "c": "conjunction", "d": "and, also"},
      {"w": "tenebræ", "g": "darknesses", "p": "nominative plural", "l": "tenebræ, tenebrarum, f.", "c": "feminine · I declension · plural only", "d": "darkness (plural in form)"},
      {"w": "erant", "g": "were", "p": "imperfect, third plural", "l": "sum, esse, fui", "c": "irregular", "d": "to be"},
      {"w": "super", "g": "over", "p": "preposition with the accusative", "l": "super", "c": "preposition", "d": "over, above, upon"},
      {"w": "faciem", "g": "the face", "p": "accusative singular", "l": "facies, faciei, f.", "c": "feminine · V declension", "d": "face, surface"},
      {"w": "abyssi:", "g": "of the abyss", "p": "genitive singular", "l": "abyssus, abyssi, f.", "c": "feminine · II declension", "d": "abyss, the deep"},
      {"w": "et", "g": "and", "p": "conjunction", "l": "et", "c": "conjunction", "d": "and, also"},
      {"w": "spiritus", "g": "the Spirit", "p": "nominative singular", "l": "spiritus, spiritus, m.", "c": "masculine · IV declension", "d": "spirit, breath"},
      {"w": "Dei", "g": "of God", "p": "genitive singular", "l": "Deus, Dei, m.", "c": "masculine · II declension", "d": "God"},
      {"w": "ferebatur", "g": "was brought", "p": "imperfect passive, third singular", "l": "fero, ferre, tuli, latus", "c": "irregular", "d": "to carry, to bear"},
      {"w": "super", "g": "over", "p": "preposition with the accusative", "l": "super", "c": "preposition", "d": "over, above, upon"},
      {"w": "aquas.", "g": "the waters", "p": "accusative plural", "l": "aqua, aquæ, f.", "c": "feminine · I declension", "d": "water"}
    ],
    "links": [[2, 0, "s"], [0, 3, "a"], [0, 5, "a"], [8, 7, "s"], [9, 10, "w"], [10, 11, "g"], [15, 13, "s"], [13, 14, "g"], [16, 17, "w"]]
  },
  "3": {
    "tokens": [
      {"w": "Dixitque", "g": "and said", "p": "perfect, third singular, with -que (and) fused on", "l": "dico, dicere, dixi, dictus", "c": "III conjugation", "d": "to say, to speak"},
      {"w": "Deus:", "g": "God", "p": "nominative singular", "l": "Deus, Dei, m.", "c": "masculine · II declension", "d": "God"},
      {"w": "Fiat", "g": "let there be", "p": "present subjunctive, third singular", "l": "fio, fieri, factus sum", "c": "irregular", "d": "to become, to be made"},
      {"w": "lux.", "g": "light", "p": "nominative singular", "l": "lux, lucis, f.", "c": "feminine · III declension", "d": "light"},
      {"w": "Et", "g": "and", "p": "conjunction", "l": "et", "c": "conjunction", "d": "and, also"},
      {"w": "facta est", "g": "became", "p": "perfect of fio: two words, one verb", "l": "fio, fieri, factus sum", "c": "irregular", "d": "to become, to be made"},
      {"w": "lux.", "g": "light", "p": "nominative singular", "l": "lux, lucis, f.", "c": "feminine · III declension", "d": "light"}
    ],
    "links": [[0, 1, "s"], [2, 3, "s"], [5, 6, "s"]]
  }
}
```

Note in v.3 how the merge shifts indexes: `facta est` is one token (index 5),
so the final `lux.` is index 6.

## 9. Before you output

Check every one of these; a failure on any is a rejected chapter:

1. Tokens of each verse, joined with single spaces, reproduce the verse text
   exactly.
2. Every token has all six fields; every link index exists; no link points at
   a token in another verse.
3. Same lemma → identical `l`, `c`, `d` strings everywhere in the chapter.
4. Adjective/participle/pronoun parses include gender; noun parses do not.
5. Every visible subject/object of every verb is linked, and nothing doubtful
   is.
6. Orthography is Clementine (æ/œ/j) in every citation.
7. Contextual glosses used where the CPDV sense demands them.
8. Every verb parse names its tense in the words of the table in §3, and every
   verb citation carries the principal parts the build conjugates from.
9. Every adjective citation has its second (and third) termination; every
   pronoun citation is one of the conventional strings in §4.

## Chapter text (Clementine Vulgate)

<PASTE LATIN CHAPTER HERE — one verse per line, numbered>

## Reference translation (CPDV — sense reference only, never copy phrasing)

<PASTE CPDV CHAPTER HERE>
