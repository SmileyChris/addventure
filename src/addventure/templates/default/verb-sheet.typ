// verb-sheet.typ — Verb reference page
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let verb-sheet(data) = {
  sheet-title("ADDVENTURE — VERB SHEET")

  block(below: 1em)[
    #text(size: 9pt, style: "italic")[
      To take an action, add a Verb ID to an Entity ID. The resulting sum is your result — look it up in the Story Ledger. If the sum is not listed, nothing happens.
    ]
  ]

  section-title("Verbs")

  for verb in data.verbs {
    block(
      width: 100%,
      below: 0.4em,
    )[
      #grid(
        columns: (1fr, auto),
        gutter: 0.5em,
        align(left + horizon)[
          #text(font: "Liberation Sans", size: 11pt, weight: "bold")[#verb.name]
        ],
        align(right + horizon)[
          #id-box(str(verb.id))
        ],
      )
    ]
    line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
  }

  v(1em)
  section-title("Additional Verbs")
  text(size: 9pt, style: "italic")[If the GM adds verbs during play, record them here.]
  v(0.4em)

  for _ in range(3) {
    block(
      width: 100%,
      below: 0.6em,
    )[
      #grid(
        columns: (1fr, 4em),
        gutter: 0.5em,
        align(left + bottom)[#write-slot()],
        align(right + bottom)[#write-slot(width: 100%)],
      )
    ]
  }
}
