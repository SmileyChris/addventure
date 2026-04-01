// main.typ — Entry point: reads JSON and assembles all pages
#import "style.typ": page-paper as default-paper, page-margin, body-font
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet
#import "ledger.typ": story-ledger

// Read JSON data from --input data=<path>
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

// Game title from metadata (falls back to "ADDVENTURE")
#let game-title = upper(data.metadata.at("title", default: "Addventure"))
#let start-room = data.at("start_room", default: none)

// Paper size: CLI --paper overrides template default
#let page-paper = sys.inputs.at("paper", default: default-paper)

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

// 1. Verb sheet (with game description and start room instruction)
#verb-sheet(data, game-title, start-room)

// 2. Start room (first, so the player sees it right after verbs)
#if start-room != none {
  for room in data.rooms {
    if room.name == start-room {
      pagebreak()
      room-sheet(room, is-start: true)
    }
  }
}

// 3. Inventory & Potentials
#pagebreak()
#inventory-sheet(data, game-title)

// 4. Remaining rooms (skip start room, already printed)
#for room in data.rooms {
  if room.name != start-room {
    pagebreak()
    room-sheet(room, is-start: false)
  }
}

// 5. Story Ledger (last — player references it during play)
#pagebreak()
#story-ledger(data, game-title)
