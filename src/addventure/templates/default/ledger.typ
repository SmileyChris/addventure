// ledger.typ — Story Ledger entries (two-column layout)
#import "style.typ": sheet-title, section-title, separator, title-font

#let ledger-entry(entry, prefix) = {
  block(
    width: 100%,
    below: 0.5em,
    breakable: false,
    stroke: 0.5pt + luma(180),
    inset: 6pt,
  )[
    #text(font: title-font, size: 9pt, weight: "bold", tracking: 0.05em)[
      #prefix\-#str(entry.entry)
    ]
    #v(0.15em)
    #text(size: 9pt)[#eval(entry.narrative, mode: "markup")]
    #if entry.instructions.len() > 0 {
      v(0.3em)
      for instr in entry.instructions {
        block(below: 0.2em)[
          #text(size: 8pt, style: "italic")[→ #instr]
        ]
      }
    }
  ]
}

#let story-ledger(data, game-title) = {
  sheet-title("STORY LEDGER")

  block(below: 0.8em)[
    #text(size: 9pt, style: "italic")[
      Only read an entry when directed to by the Potentials List. Read the narrative aloud, then follow any instructions.
    ]
  ]

  let prefix = data.at("ledger_prefix", default: "A")

  columns(2, gutter: 1.5em)[
    #for entry in data.ledger {
      ledger-entry(entry, prefix)
    }
  ]
}
