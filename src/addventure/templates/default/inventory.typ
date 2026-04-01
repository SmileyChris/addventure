// inventory.typ — Inventory slots + Master Potentials List
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let inventory-sheet(data, game-title) = {
  sheet-title(game-title + " — INVENTORY & POTENTIALS")

  // Inventory section
  section-title("Inventory")
  block(below: 0.6em)[
    #text(size: 9pt, style: "italic")[Record items you are carrying. Write the item name and its ID.]
  ]
  v(0.4em)

  let slot-count = data.inventory_slots
  let cols = 2
  let rows = calc.ceil(slot-count / cols)

  grid(
    columns: (1fr, 1fr),
    gutter: (1em, 0.6em),
    ..for i in range(slot-count) {
      (
        block(width: 100%)[
          #grid(
            columns: (1fr, 3.5em),
            gutter: 0.4em,
            align(left + bottom)[#write-slot()],
            align(right + bottom)[#write-slot(width: 100%)],
          )
        ],
      )
    }
  )

  v(1.5em)

  // Master Potentials List
  section-title("Master Potentials List")
  block(below: 0.6em)[
    #text(size: 9pt, style: "italic")[
      Add a Verb ID + Entity ID and look up the sum below. If listed, go to that Ledger Entry.
    ]
  ]
  v(0.4em)

  // 3-column potentials grid
  let pot-cols = 3
  let pots = data.potentials
  let prefix = data.at("entry_prefix", default: "A")
  let rows = calc.ceil(pots.len() / pot-cols)

  // Header row
  block(
    width: 100%,
    fill: luma(230),
    inset: (x: 8pt, y: 4pt),
  )[
    #grid(
      columns: (1fr,) * pot-cols,
      gutter: 1.5em,
      ..for _ in range(pot-cols) {
        (
          grid(
            columns: (auto, auto),
            column-gutter: 1em,
            align(left)[
              #text(font: "Liberation Sans", size: 8pt, weight: "bold")[SUM]
            ],
            align(left)[
              #text(font: "Liberation Sans", size: 8pt, weight: "bold")[ENTRY]
            ],
          ),
        )
      }
    )
  ]

  // Data rows — fill column by column (down then right)
  for row-idx in range(rows) {
    block(
      width: 100%,
      inset: (x: 8pt, y: 1pt),
    )[
      #grid(
        columns: (1fr,) * pot-cols,
        gutter: 1.5em,
        ..for col-idx in range(pot-cols) {
          let idx = col-idx * rows + row-idx
          if idx < pots.len() {
            (
              grid(
                columns: (auto, auto),
                column-gutter: 1em,
                align(left + horizon)[
                  #text(font: "Liberation Mono", size: 9pt, weight: "bold")[#str(pots.at(idx).sum)]
                ],
                align(left + horizon)[
                  #text(font: "Liberation Mono", size: 9pt)[#prefix\-#str(pots.at(idx).entry)]
                ],
              ),
            )
          } else {
            ([], )
          }
        }
      )
    ]
    line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
  }
}
