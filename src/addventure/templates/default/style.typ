// style.typ — shared helpers and page setup for Addventure PDF output

// Page setup constants
#let page-paper = "a4"
#let page-margin = (top: 0.5in, left: 0.5in, right: 0.5in, bottom: 0.75in)
#let body-font = "Alegreya"
#let mono-font = "Liberation Mono"
#let heading-font = "Liberation Sans"
#let title-font = "Montserrat"

// sheet-title: centered bold title with a rule underneath
#let sheet-title(title) = {
  align(center)[
    #block(
      width: 100%,
      below: 0.15em,
    )[
      #text(font: title-font, size: 20pt, weight: "black", tracking: 0.1em)[#title]
    ]
    #line(length: 100%, stroke: 1.5pt)
  ]
}

// section-title: left-aligned section heading with thin rule underneath
#let section-title(title) = {
  block(below: 0.2em)[
    #text(font: heading-font, size: 11pt, weight: "bold", tracking: 0.05em)[#upper(title)]
  ]
  line(length: 100%, stroke: 0.5pt)
  v(-0.3em)
}

// write-slot: underline box for player to write in
#let write-slot(width: 100%) = {
  box(
    width: width,
    height: 1.4em,
    stroke: (bottom: 0.75pt),
  )[]
}

// id-box: a bordered box containing an ID number
#let id-box(content) = {
  box(
    stroke: 0.75pt,
    inset: (x: 5pt, y: 3pt),
    radius: 2pt,
  )[
    #text(font: mono-font, size: 10pt, weight: "bold")[#content]
  ]
}

// separator: decorative separator between ledger entries
#let separator() = {
  v(0.5em)
  align(center)[
    #text(size: 8pt, fill: luma(150))[— ✦ —]
  ]
  v(0.5em)
}
