#import "style.typ": *

#let sealed-jigsaw(data) = {
  let jigsaw = data.at("jigsaw_data", default: none)
  if jigsaw == none { return }

  let pieces = jigsaw.pieces
  if pieces.len() == 0 { return }

  // Reconstruct content blocks for each sealed text
  let contents = (:)
  for st in data.sealed_texts {
    let cw = eval(jigsaw.cell_w)
    let ch = eval(jigsaw.cell_h)
    let full-w = cw * jigsaw.cols
    let full-h = ch * st.rows
    let pad = eval(jigsaw.pad)
    contents.insert(st.ref, block(width: full-w, height: full-h, inset: pad)[
      #set text(size: 10pt)
      #set par(justify: true)
      #set align(left)
      #eval(st.content, mode: "markup")
    ])
  }

  let kerf = 1pt
  let cw = eval(jigsaw.cell_w)
  let ch = eval(jigsaw.cell_h)
  let cut-cols = jigsaw.cut_cols

  // Assembly instructions
  sheet-title("CUT PAGES")
  v(0.3em)
  text(size: 8pt, style: "italic")[
    When directed by a ledger entry, find the matching pieces, cut them out, and assemble them to reveal the content.
  ]
  v(0.5em)

  // Render pieces in grid
  let piece-boxes = ()
  for p in pieces {
    let src = contents.at(p.ref)
    let flipped = p.flip
    let inner = box(
      width: cw + kerf,
      height: ch + kerf,
      clip: true,
      stroke: kerf + black,
      align(left + top, move(
        dx: -(p.col * cw - kerf / 2),
        dy: -(p.row * ch - kerf / 2),
        src,
      ))
    )
    if flipped {
      piece-boxes.push(rotate(180deg, reflow: false, inner))
    } else {
      piece-boxes.push(inner)
    }
  }

  grid(
    columns: cut-cols,
    gutter: 0mm,
    ..piece-boxes
  )
}
