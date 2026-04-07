// inventory.typ — Inventory slots + Master Potentials List
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let inventory-sheet(data, game-title) = {
  sheet-title("INVENTORY & POTENTIALS")

  // Inventory section
  section-title("Inventory")
  text(size: 9pt, style: "italic")[Record items you are carrying. Write the item name and its ID.]
  v(0.4em)

  let slot-count = data.inventory_slots
  let cols = 2
  let rows = calc.ceil(slot-count / cols)

  grid(
    columns: (1fr, 1fr),
    column-gutter: 1em,
    row-gutter: 0.6em,
    ..for i in range(slot-count) {
      (
        block(width: 100%)[
          #grid(
            columns: (1fr, auto),
            gutter: 0.4em,
            align(left + bottom)[#write-slot()],
            align(right + horizon)[#id-box(hide[000])],
          )
        ],
      )
    }
  )

  // Cue Checks section (only if game has cues)
  let cue-slots = data.at("cue_slots", default: 0)
  if cue-slots > 0 {
    v(1.5em)
    section-title("Cue Checks")
    block(below: 0.6em)[
      #text(size: 9pt, style: "italic")[On room entry, add each cue + Room ID and check the Potentials List.]
    ]
    v(0.4em)
    let cue-count = calc.max(cue-slots, 6)
    grid(
      columns: (auto,) * 6,
      column-gutter: 0.8em,
      row-gutter: 0.6em,
      ..for i in range(cue-count) {
        (id-box(hide[000]),)
      }
    )
  }

  // Signals section (only if game has signals)
  let signal-slots = data.at("signal_slots", default: 0)
  if signal-slots > 0 {
    v(1.5em)
    section-title("Signals")
    block(below: 0.6em)[
      #text(size: 9pt, style: "italic")[#if data.at("signal_has_incoming", default: false) [Copy any signals from the previous chapter, then write new ones when instructed.] else [Write signal codes here when instructed.]]
    ]
    v(0.4em)
    let slot-count = calc.max(signal-slots, 4)
    grid(
      columns: (auto,) * 4,
      column-gutter: 0.8em,
      row-gutter: 0.6em,
      ..for i in range(slot-count) {
        (id-box(hide[000], crossable: true),)
      }
    )
  }

  v(1.5em)

  // Master Potentials List
  section-title("Master Potentials List")
  block(below: 1.2em)[
    #text(size: 9pt, style: "italic")[
      Calculate verb number + object number(s) and look up the sum below. If listed, go to that Ledger entry.
    ]
  ]

  // Potentials grid — columns adapt to page width
  let pots = data.potentials
  let prefix = data.at("entry_prefix", default: "A")

  context {
    let pot-cols = calc.max(3, calc.min(6, int(page.width / 1.4in)))
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

    // Data rows — left to right, top to bottom
    for row-idx in range(rows) {
      block(
        width: 100%,
        inset: (x: 8pt, y: 0pt),
      )[
        #grid(
          columns: (1fr,) * pot-cols,
          gutter: 1.5em,
          ..for col-idx in range(pot-cols) {
            let idx = row-idx * pot-cols + col-idx
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
}
