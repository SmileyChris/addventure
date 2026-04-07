// section-actions.typ — Actions & Inventory: verbs, inventory slots, signals
#import "style.typ": sheet-title, section-title, write-slot, id-box, strike-text

#let actions-inventory(data) = {
  sheet-title("ACTIONS & INVENTORY")

  section-title("Verbs")
  block(below: 0.8em)[
    #text(size: 9pt, style: "italic")[
      To take an action, calculate verb number + object number(s). Look up the resulting sum in the Potentials List. If listed, read the matching Ledger entry. If not listed, nothing happens.
    ]
  ]

  for verb in data.verbs {
    block(
      width: 100%,
      below: 0.4em,
    )[
      #grid(
        columns: (1fr, auto),
        gutter: 0.5em,
        align(left + horizon)[
          #strike-text(text(font: "Liberation Sans", size: 11pt, weight: "bold")[#verb.name])
        ],
        align(right + horizon)[
          #id-box(str(verb.id), crossable: true) #id-box(hide[00])
        ],
      )
    ]
    line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
  }

  v(0.3em)
  text(size: 9pt, style: "italic")[If instructed, record new verbs here.]
  for _ in range(3) {
    block(width: 100%, below: 0.4em)[
      #grid(
        columns: (1fr, auto),
        gutter: 0.4em,
        align(left + bottom)[#write-slot()],
        align(right + horizon)[#id-box(hide[00])],
      )
    ]
  }

  // Inventory
  v(2em)
  section-title("Inventory")
  text(size: 9pt, style: "italic")[Record items you are carrying. Write the item name and its ID.]
  v(0.4em)

  let slot-count = data.at("inventory_slots", default: 6)
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

  // Signals
  let signal-slots = data.at("signal_slots", default: 0)
  if signal-slots > 0 {
    v(2em)
    section-title("Signals")
    block(below: 0.6em)[
      #text(size: 9pt, style: "italic")[#if data.at("signal_has_incoming", default: false) [Copy any signals from the previous chapter, then write new ones when instructed.] else [Write signal codes here when instructed.]]
    ]
    v(0.4em)
    let sig-count = calc.max(signal-slots, 4)
    grid(
      columns: (auto,) * 4,
      column-gutter: 0.8em,
      row-gutter: 0.6em,
      ..for i in range(sig-count) {
        (id-box(hide[0000]),)
      }
    )
  }
}
