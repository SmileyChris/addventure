// main.typ — Entry point: reads JSON and assembles all pages
#import "style.typ": page-paper, page-margin, body-font
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet
#import "ledger.typ": story-ledger

// Read JSON data from --input data=<path>
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

// Page and text defaults
#set page(
  paper: page-paper,
  margin: page-margin,
)
#set text(font: body-font, size: 10pt, lang: "en")
#set par(leading: 0.65em)

// Verb sheet
#verb-sheet(data)

// Room sheets — one per room
#for room in data.rooms {
  pagebreak()
  room-sheet(room)
}

// Inventory & Potentials
#pagebreak()
#inventory-sheet(data)

// Story Ledger
#pagebreak()
#story-ledger(data)
