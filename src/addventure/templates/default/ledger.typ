// ledger.typ — Story Ledger entries
#import "style.typ": sheet-title, section-title, separator

#let story-ledger(data, game-title) = {
  sheet-title(game-title + " — STORY LEDGER")

  block(below: 1em)[
    #text(size: 9pt, style: "italic")[
      Only read an entry when directed to by the Potentials List. Read the narrative aloud, then follow any instructions.
    ]
  ]

  let entries = data.ledger
  let last-idx = entries.len() - 1

  for (i, entry) in entries.enumerate() {
    // Entry header
    block(
      width: 100%,
      below: 0.3em,
    )[
      #text(font: "Liberation Sans", size: 10pt, weight: "bold")[
        ENTRY #str(entry.entry)
      ]
    ]

    // Narrative
    block(
      width: 100%,
      below: 0.4em,
      inset: (left: 1em),
    )[
      #text(size: 10pt, style: "italic")[#entry.narrative]
    ]

    // Instructions (if any)
    if entry.instructions.len() > 0 {
      block(
        width: 100%,
        below: 0.3em,
        inset: (left: 1em),
      )[
        #for instr in entry.instructions {
          block(below: 0.2em)[
            #text(size: 9pt)[→ #instr]
          ]
        }
      ]
    }

    // Separator between entries (not after last)
    if i < last-idx {
      separator()
    }
  }
}
