// main.typ — Entry point: reads JSON and assembles all pages
#import "style.typ": page-paper, page-margin, body-font
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet
#import "ledger.typ": story-ledger

// Read JSON data from --input data=<path>
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

// Game title from metadata (falls back to "ADDVENTURE")
#let game-title = upper(data.metadata.at("title", default: "Addventure"))

// Page and text defaults
#set page(
  paper: page-paper,
  margin: page-margin,
  footer: context {
    let author = data.metadata.at("author", default: none)
    let parts = (game-title,)
    if author != none { parts.push(author) }
    align(center)[
      #text(size: 7pt, fill: luma(150))[
        #parts.join(" — ") #h(1fr) Page #counter(page).display()
      ]
    ]
  },
)
#set text(font: body-font, size: 10pt, lang: "en")
#set par(leading: 0.65em)

// Verb sheet
#verb-sheet(data, game-title)

// Room sheets — one per room
#for room in data.rooms {
  pagebreak()
  room-sheet(room)
}

// Inventory & Potentials
#pagebreak()
#inventory-sheet(data, game-title)

// Story Ledger
#pagebreak()
#story-ledger(data, game-title)
