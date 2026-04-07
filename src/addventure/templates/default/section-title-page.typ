// section-title-page.typ — Chapter title page: image, description, signal checks, cues, potentials
#import "style.typ": sheet-title, section-title, id-box

#let potentials-grid(pots, prefix) = {
  context {
    let pot-cols = calc.max(3, calc.min(6, int(page.width / 1.4in)))
    let rows = calc.ceil(pots.len() / pot-cols)
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
    for row-idx in range(rows) {
      block(
        width: 100%,
        inset: (x: 8pt, y: 3pt),
        stroke: (bottom: 0.25pt + luma(200)),
      )[
        #grid(
          columns: (1fr,) * pot-cols,
          gutter: 1.5em,
          ..for col-idx in range(pot-cols) {
            let idx = col-idx * rows + row-idx
            if idx < pots.len() {
              let p = pots.at(idx)
              (
                grid(
                  columns: (auto, auto),
                  column-gutter: 1em,
                  align(left)[#text(size: 9pt)[#str(p.sum)]],
                  align(left)[#text(size: 9pt)[#prefix\-#str(p.entry)]],
                ),
              )
            } else {
              (none,)
            }
          }
        )
      ]
    }
  }
}

#let title-page(chapter, display-title) = {
  let prefix = chapter.at("ledger_prefix", default: "A")

  sheet-title(display-title)

  // Cover image + description + inline signal checks
  let cover-image = chapter.metadata.at("image", default: none)
  let image-height = eval(chapter.metadata.at("image_height", default: "12em"))
  let description = chapter.metadata.at("description", default: none)
  let signal-checks = chapter.at("signal_checks", default: ())

  let signal-check-content = if signal-checks.len() > 0 {
    text(size: 9pt, style: "italic")[
      Check your signals: #for (i, sc) in signal-checks.enumerate() {
        if sc.is_otherwise {
          [Otherwise, read #prefix\-#str(sc.entry).]
        } else if i == 0 {
          [if you have *#str(sc.signal_id)*, read #prefix\-#str(sc.entry).]
        } else {
          [ Otherwise, if you have *#str(sc.signal_id)*, read #prefix\-#str(sc.entry).]
        }
      }
    ]
  }

  if cover-image != none and description != none {
    block(below: 0.8em)[
      #grid(
        columns: (auto, 1fr),
        gutter: 1em,
        align(top)[
          #image(cover-image, height: image-height)
        ],
        align(left + top)[
          #text(size: 11pt)[#eval(description, mode: "markup")]
          #if signal-check-content != none { v(0.6em); signal-check-content }
        ],
      )
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  } else if cover-image != none {
    block(below: 0.8em)[
      #align(center)[#image(cover-image, height: image-height)]
    ]
    if signal-check-content != none { block(below: 0.8em)[#signal-check-content] }
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  } else if description != none {
    block(below: 0.8em)[
      #text(size: 11pt)[#eval(description, mode: "markup")]
      #if signal-check-content != none { v(0.6em); signal-check-content }
    ]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  } else if signal-check-content != none {
    block(below: 0.8em)[#signal-check-content]
    line(length: 100%, stroke: (paint: luma(150), thickness: 0.5pt))
    v(0.8em)
  }

  // Cue Checks
  let cue-slots = chapter.at("cue_slots", default: 0)
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

  // Potentials List
  v(1.5em)
  section-title("Potentials List")
  block(below: 1.2em)[
    #text(size: 9pt, style: "italic")[
      Calculate verb number + object number(s) and look up the sum below. If listed, go to that Ledger entry.
    ]
  ]
  potentials-grid(chapter.potentials, prefix)
}
