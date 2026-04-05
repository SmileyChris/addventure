#import "style.typ": *

#let sealed-ledger(data) = {
  if data.sealed_texts.len() == 0 { return }

  sheet-title("SEALED TEXTS")
  v(0.3em)
  text(size: 8pt, style: "italic")[
    Do not read ahead — turn to a sealed text only when directed by a ledger entry.
  ]
  v(0.5em)

  for st in data.sealed_texts {
    block(
      width: 100%,
      below: 0.8em,
      stroke: 0.5pt + luma(180),
      inset: 8pt,
    )[
      #text(font: title-font, size: 10pt, weight: "bold")[
        Sealed Text #st.ref
      ]
      #v(0.3em)
      #text(size: 9pt)[#eval(st.content, mode: "markup")]
    ]
  }
}
