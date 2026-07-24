// Traditional Latin prayers, enough to pray the Rosary, in praying order.
// Lines are broken at recitation phrases (how the prayer is actually said
// aloud); sections marked V. (versicle, leader) and R. (response) follow the
// customary Rosary division between leader and respondents.
// Spellings follow the Clementine convention used by the Bible text (æ, j).

export interface PrayerSection {
  /** "V." (leader) / "R." (response), when the prayer divides that way. */
  label?: string;
  /** [latin, english] recitation phrases. */
  lines: [string, string][];
}

export interface Prayer {
  slug: string;
  latin: string;
  english: string;
  sections: PrayerSection[];
}

export const PRAYERS: Prayer[] = [
  {
    slug: "signum-crucis",
    latin: "Signum Crucis",
    english: "Sign of the Cross",
    sections: [
      {
        lines: [
          ["In nomine Patris,", "In the name of the Father,"],
          ["et Filii,", "and of the Son,"],
          ["et Spiritus Sancti.", "and of the Holy Spirit."],
          ["Amen.", "Amen."],
        ],
      },
    ],
  },
  {
    slug: "symbolum-apostolorum",
    latin: "Symbolum Apostolorum",
    english: "Apostles' Creed",
    sections: [
      {
        lines: [
          [
            "Credo in Deum Patrem omnipotentem,",
            "I believe in God, the Father almighty,",
          ],
          ["Creatorem cæli et terræ.", "Creator of heaven and earth;"],
          ["Et in Jesum Christum,", "and in Jesus Christ,"],
          [
            "Filium ejus unicum, Dominum nostrum:",
            "His only Son, our Lord;",
          ],
          [
            "qui conceptus est de Spiritu Sancto,",
            "who was conceived by the Holy Spirit,",
          ],
          ["natus ex Maria Virgine,", "born of the Virgin Mary,"],
          ["passus sub Pontio Pilato,", "suffered under Pontius Pilate,"],
          [
            "crucifixus, mortuus, et sepultus:",
            "was crucified, died, and was buried.",
          ],
          ["descendit ad inferos;", "He descended into hell;"],
          [
            "tertia die resurrexit a mortuis;",
            "the third day He rose again from the dead;",
          ],
          ["ascendit ad cælos;", "He ascended into heaven,"],
          [
            "sedet ad dexteram Dei Patris omnipotentis:",
            "and sits at the right hand of God the Father almighty;",
          ],
          [
            "inde venturus est judicare vivos et mortuos.",
            "from thence He shall come to judge the living and the dead.",
          ],
          ["Credo in Spiritum Sanctum,", "I believe in the Holy Spirit,"],
          ["sanctam Ecclesiam catholicam,", "the holy Catholic Church,"],
          ["Sanctorum communionem,", "the communion of Saints,"],
          ["remissionem peccatorum,", "the forgiveness of sins,"],
          ["carnis resurrectionem,", "the resurrection of the body,"],
          ["vitam æternam. Amen.", "and life everlasting. Amen."],
        ],
      },
    ],
  },
  {
    slug: "pater-noster",
    latin: "Pater Noster",
    english: "Our Father",
    sections: [
      {
        label: "V.",
        lines: [
          ["Pater noster, qui es in cælis,", "Our Father, who art in heaven,"],
          ["sanctificetur nomen tuum.", "hallowed be Thy name."],
          ["Adveniat regnum tuum.", "Thy kingdom come."],
          [
            "Fiat voluntas tua, sicut in cælo et in terra.",
            "Thy will be done on earth as it is in heaven.",
          ],
        ],
      },
      {
        label: "R.",
        lines: [
          [
            "Panem nostrum quotidianum da nobis hodie,",
            "Give us this day our daily bread,",
          ],
          ["et dimitte nobis debita nostra,", "and forgive us our trespasses,"],
          [
            "sicut et nos dimittimus debitoribus nostris.",
            "as we forgive those who trespass against us.",
          ],
          ["Et ne nos inducas in tentationem,", "And lead us not into temptation,"],
          ["sed libera nos a malo. Amen.", "but deliver us from evil. Amen."],
        ],
      },
    ],
  },
  {
    slug: "ave-maria",
    latin: "Ave Maria",
    english: "Hail Mary",
    sections: [
      {
        label: "V.",
        lines: [
          ["Ave Maria, gratia plena,", "Hail Mary, full of grace,"],
          ["Dominus tecum.", "the Lord is with thee."],
          ["Benedicta tu in mulieribus,", "Blessed art thou amongst women,"],
          [
            "et benedictus fructus ventris tui, Jesus.",
            "and blessed is the fruit of thy womb, Jesus.",
          ],
        ],
      },
      {
        label: "R.",
        lines: [
          ["Sancta Maria, Mater Dei,", "Holy Mary, Mother of God,"],
          ["ora pro nobis peccatoribus,", "pray for us sinners,"],
          [
            "nunc et in hora mortis nostræ. Amen.",
            "now and at the hour of our death. Amen.",
          ],
        ],
      },
    ],
  },
  {
    slug: "gloria-patri",
    latin: "Gloria Patri",
    english: "Glory Be",
    sections: [
      {
        label: "V.",
        lines: [
          [
            "Gloria Patri, et Filio, et Spiritui Sancto.",
            "Glory be to the Father, and to the Son, and to the Holy Spirit.",
          ],
        ],
      },
      {
        label: "R.",
        lines: [
          [
            "Sicut erat in principio, et nunc, et semper,",
            "As it was in the beginning, is now, and ever shall be,",
          ],
          ["et in sæcula sæculorum. Amen.", "world without end. Amen."],
        ],
      },
    ],
  },
  {
    slug: "oratio-fatimae",
    latin: "Oratio Fatimæ",
    english: "Fatima Prayer",
    sections: [
      {
        lines: [
          [
            "Domine Jesu, dimitte nobis debita nostra,",
            "O my Jesus, forgive us our sins,",
          ],
          ["salva nos ab igne inferni,", "save us from the fires of hell,"],
          ["perduc in cælum omnes animas,", "lead all souls to Heaven,"],
          [
            "præsertim eas, quæ misericordiæ tuæ maxime indigent. Amen.",
            "especially those in most need of Thy mercy. Amen.",
          ],
        ],
      },
    ],
  },
  {
    slug: "salve-regina",
    latin: "Salve Regina",
    english: "Hail, Holy Queen",
    sections: [
      {
        lines: [
          [
            "Salve, Regina, mater misericordiæ:",
            "Hail, holy Queen, Mother of mercy:",
          ],
          [
            "vita, dulcedo, et spes nostra, salve.",
            "our life, our sweetness, and our hope, hail.",
          ],
          [
            "Ad te clamamus exsules filii Hevæ.",
            "To thee do we cry, poor banished children of Eve.",
          ],
          [
            "Ad te suspiramus,",
            "To thee do we send up our sighs,",
          ],
          [
            "gementes et flentes in hac lacrimarum valle.",
            "mourning and weeping in this valley of tears.",
          ],
          [
            "Eia ergo, advocata nostra,",
            "Turn then, most gracious Advocate,",
          ],
          [
            "illos tuos misericordes oculos ad nos converte.",
            "thine eyes of mercy toward us.",
          ],
          [
            "Et Jesum, benedictum fructum ventris tui, nobis post hoc exsilium ostende.",
            "And after this our exile, show unto us the blessed fruit of thy womb, Jesus.",
          ],
          [
            "O clemens, o pia, o dulcis Virgo Maria.",
            "O clement, O loving, O sweet Virgin Mary.",
          ],
        ],
      },
      {
        label: "V.",
        lines: [
          [
            "Ora pro nobis, sancta Dei Genetrix.",
            "Pray for us, O holy Mother of God.",
          ],
        ],
      },
      {
        label: "R.",
        lines: [
          [
            "Ut digni efficiamur promissionibus Christi.",
            "That we may be made worthy of the promises of Christ.",
          ],
        ],
      },
    ],
  },
  {
    slug: "oratio-post-rosarium",
    latin: "Oratio post Rosarium",
    english: "Prayer after the Rosary",
    sections: [
      {
        lines: [
          [
            "Deus, cujus Unigenitus",
            "O God, whose only-begotten Son,",
          ],
          [
            "per vitam, mortem et resurrectionem suam",
            "by His life, death, and resurrection,",
          ],
          [
            "nobis salutis æternæ præmia comparavit:",
            "has purchased for us the rewards of eternal life:",
          ],
          ["concede, quæsumus:", "grant, we beseech Thee,"],
          [
            "ut hæc mysteria sacratissimo beatæ Mariæ Virginis Rosario recolentes,",
            "that meditating upon these mysteries of the most holy Rosary of the Blessed Virgin Mary,",
          ],
          [
            "et imitemur quod continent,",
            "we may imitate what they contain",
          ],
          [
            "et quod promittunt assequamur.",
            "and obtain what they promise.",
          ],
          [
            "Per eumdem Christum Dominum nostrum. Amen.",
            "Through the same Christ our Lord. Amen.",
          ],
        ],
      },
    ],
  },
];

const bySlug = new Map(PRAYERS.map((p) => [p.slug, p]));

export function getPrayer(slug: string): Prayer | undefined {
  return bySlug.get(slug);
}

export function adjacentPrayer(slug: string, dir: -1 | 1): Prayer | null {
  const i = PRAYERS.findIndex((p) => p.slug === slug);
  if (i === -1) return null;
  return PRAYERS[i + dir] ?? null;
}
