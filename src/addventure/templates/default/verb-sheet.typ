// verb-sheet.typ — Game intro, description, and verb reference
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let verb-sheet(data, game-title, start-room) = {
  sheet-title(game-title)

  // Game description (from body text before first # header)
  let description = data.metadata.at("description", default: none)
  if description != none {
    block(below: 0.8em)[
      #text(size: 11pt)[#eval(description, mode: "markup")]
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  }

  // How to play
  block(below: 1em)[
    #text(size: 9pt, style: "italic")[
      To take an action, add a Verb ID to an Entity ID. Look up the resulting sum in the Potentials List. If listed, read the matching Ledger entry. If not listed, nothing happens.
    ]
  ]

  // Start room instruction
  if start-room != none {
    block(
      below: 1.5em,
      width: 100%,
      stroke: (left: 2pt + luma(100)),
      inset: (left: 8pt, y: 6pt),
    )[
      #text(size: 10pt, weight: "bold")[
        You begin in: #start-room
      ]
    ]
  }

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
  text(size: 9pt, style: "italic")[If the game adds verbs during play, record them here.]
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
