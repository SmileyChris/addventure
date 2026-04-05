// main.typ — Entry point: reads JSON and assembles all pages
#import "style.typ": page-paper as default-paper, page-margin, body-font, title-font
#import "cover.typ": cover-page
#import "verb-sheet.typ": verb-sheet
#import "room-sheet.typ": room-sheet
#import "inventory.typ": inventory-sheet
#import "ledger.typ": story-ledger
#import "sealed-ledger.typ": sealed-ledger
#import "sealed-jigsaw.typ": sealed-jigsaw

// Read JSON data from --input data=<path>
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

// Game title from metadata (falls back to "ADDVENTURE")
#let game-title = upper(data.metadata.at("title", default: "Addventure"))
#let start-room = data.at("start_room", default: none)
#let blind = data.at("blind", default: false)

// Paper size: CLI --paper overrides template default
#let page-paper = sys.inputs.at("paper", default: default-paper)

// Watermark logo
#let logo-path = "addventure.jpg"

// Section label state for footer
#let section-label = state("section-label", "")
// Counter for multi-page sections
#let section-page = counter("section-page")

// Page and text defaults
#set page(
  paper: page-paper,
  margin: page-margin,
  background: place(bottom + right, dx: -0.45in, dy: -0.50in,
    image(logo-path, width: 0.5in, height: 0.5in),
  ),
  footer: context {
    let label = section-label.get()
    if label != "" {
      let author = data.metadata.at("author", default: none)
      text(font: title-font, size: 7pt, weight: "bold", fill: luma(150))[#game-title]
      if author != none [
        #text(size: 7pt, fill: luma(150))[ — #author]
      ]
      h(1fr)
      text(font: title-font, size: 7pt, weight: "bold", fill: luma(150))[#label]
    }
  },
)
#set text(font: body-font, size: 10pt, lang: "en")
#set par(leading: 0.65em)

// 0. Optional cover page
#let cover-logo = sys.inputs.at("cover", default: none)
#if cover-logo != none {
  let has-cues = data.at("cue_slots", default: 0) > 0
  cover-page(game-title, cover-logo, has-cues: has-cues)
  pagebreak()
}

// 1. Verb sheet (with game description and start room instruction)
#section-label.update("Verbs")
#verb-sheet(data, game-title, start-room)

// 2. Start room (first, so the player sees it right after verbs)
#if start-room != none {
  for room in data.rooms {
    if room.name == start-room {
      pagebreak()
      if blind {
        section-label.update("Room " + str(room.id))
      } else {
        section-label.update("Room: " + room.name)
      }
      room-sheet(room, is-start: true, blind: blind)
    }
  }
}

// 3. Inventory & Potentials
#pagebreak()
#section-label.update("Inventory & Potentials")
#inventory-sheet(data, game-title)

// 4. Remaining rooms (skip start room, already printed)
#for room in data.rooms {
  if room.name != start-room {
    pagebreak()
    if blind {
      section-label.update("Room " + str(room.id))
    } else {
      section-label.update("Room: " + room.name)
    }
    room-sheet(room, is-start: false, blind: blind)
  }
}

// 5. Story Ledger (last — player references it during play)
#pagebreak()
#section-label.update("Ledger")
#story-ledger(data, game-title)

// 6. Sealed texts (extended ledger mode)
#if not data.at("jigsaw", default: false) and data.at("sealed_texts", default: ()).len() > 0 {
  pagebreak(weak: true)
  section-label.update("Sealed Texts")
  sealed-ledger(data)
}

// 7. Sealed texts (jigsaw mode)
#if data.at("jigsaw", default: false) and data.at("jigsaw_data", default: none) != none {
  pagebreak(weak: true)
  section-label.update("Cut Pages")
  sealed-jigsaw(data)
}
