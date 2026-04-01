// verb-sheet.typ — Game intro, description, and verb reference
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let verb-sheet(data, game-title, start-room) = {
  sheet-title(game-title)

  // Cover image + description
  let cover-image = data.metadata.at("image", default: none)
  let image-height = eval(data.metadata.at("image_height", default: "12em"))
  let description = data.metadata.at("description", default: none)

  if cover-image != none and description != none {
    // Image alongside description
    block(below: 0.8em)[
      #grid(
        columns: (auto, 1fr),
        gutter: 1em,
        align(top)[
          #image(cover-image, height: image-height)
        ],
        align(left + top)[
          #text(size: 11pt)[#eval(description, mode: "markup")]
        ],
      )
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  } else if cover-image != none {
    // Image only, centered
    block(below: 0.8em)[
      #align(center)[#image(cover-image, height: image-height)]
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  } else if description != none {
    // Description only (original behavior)
    block(below: 0.8em)[
      #text(size: 11pt)[#eval(description, mode: "markup")]
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  }

  // How to play
  block(below: 1em)[
    #text(size: 9pt, style: "italic")[
      To take an action, calculate verb number + object number(s). Look up the resulting sum in the Potentials List. If listed, read the matching Ledger entry. If not listed, nothing happens.
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
          #id-box(str(verb.id)) #id-box(hide[00])
        ],
      )
    ]
    line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
  }

  v(1em)
  section-title("Additional Verbs")
  text(size: 9pt, style: "italic")[If instructed, record new verbs here.]
  v(0.4em)

  for _ in range(3) {
    block(
      width: 100%,
      below: 0.8em,
    )[
      #grid(
        columns: (1fr, auto),
        gutter: 0.5em,
        align(left + bottom)[#write-slot()],
        align(right + horizon)[#id-box(hide[00])],
      )
    ]
  }
}
