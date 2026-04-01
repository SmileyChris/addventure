// inventory.typ — Inventory slots + Master Potentials List
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let inventory-sheet(data) = {
  sheet-title("ADDVENTURE — INVENTORY & POTENTIALS")

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

  // Table header
  block(
    width: 100%,
    fill: luma(230),
    inset: (x: 8pt, y: 4pt),
  )[
    #grid(
      columns: (1fr, 1fr),
      align(left)[
        #text(font: "Liberation Sans", size: 9pt, weight: "bold")[SUM]
      ],
      align(right)[
        #text(font: "Liberation Sans", size: 9pt, weight: "bold")[LEDGER ENTRY]
      ],
    )
  ]

  for pot in data.potentials {
    block(
      width: 100%,
      below: 0pt,
    )[
      #block(
        width: 100%,
        inset: (x: 8pt, y: 3pt),
      )[
        #grid(
          columns: (1fr, 1fr),
          align(left + horizon)[
            #text(font: "Liberation Mono", size: 10pt, weight: "bold")[#str(pot.sum)]
          ],
          align(right + horizon)[
            #text(font: "Liberation Mono", size: 10pt)[#str(pot.entry)]
          ],
        )
      ]
      #line(length: 100%, stroke: (paint: luma(210), thickness: 0.3pt))
    ]
  }
}
