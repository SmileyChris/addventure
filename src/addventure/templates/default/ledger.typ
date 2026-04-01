// ledger.typ — Story Ledger entries (two-column layout)
#import "style.typ": sheet-title, section-title, separator

#let ledger-entry(entry) = {
  block(
    width: 100%,
    below: 0.5em,
    stroke: (left: 1.5pt + luma(180)),
    inset: (left: 6pt, y: 2pt),
  )[
    #text(font: "Liberation Sans", size: 9pt, weight: "bold")[
      ENTRY #str(entry.entry)
    ]
    #v(0.15em)
    #text(size: 9pt, style: "italic")[#eval(entry.narrative, mode: "markup")]
    #if entry.instructions.len() > 0 {
      v(0.15em)
      for instr in entry.instructions {
        block(below: 0.1em)[
          #text(size: 8pt)[→ #instr]
        ]
      }
    }
  ]
}

#let story-ledger(data, game-title) = {
  sheet-title(game-title + " — STORY LEDGER")

  block(below: 0.8em)[
    #text(size: 9pt, style: "italic")[
      Only read an entry when directed to by the Potentials List. Read the narrative aloud, then follow any instructions.
    ]
  ]

  columns(2, gutter: 1.5em)[
    #for entry in data.ledger {
      ledger-entry(entry)
    }
  ]
}
