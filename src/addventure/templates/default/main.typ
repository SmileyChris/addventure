// main.typ — Single-chapter entry point
// Layout: Cover, Title page, Actions & Inventory, Rooms, Ledger, Fragments
#import "style.typ": page-paper as default-paper, page-margin, body-font, title-font
#import "cover.typ": cover-page
#import "section-title-page.typ": title-page
#import "section-actions.typ": actions-inventory
#import "room-sheet.typ": room-sheet
#import "ledger.typ": story-ledger
#import "sealed-ledger.typ": sealed-ledger
#import "sealed-jigsaw.typ": sealed-jigsaw

// Read JSON data
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

#let chapter-title = upper(data.metadata.at("title", default: "Addventure"))
#let parent-title = data.metadata.at("parent_title", default: none)
#let game-title = if parent-title != none { upper(parent-title) + " — " + chapter-title } else { chapter-title }
#let start-room = data.at("start_room", default: none)
#let blind = data.at("blind", default: false)

#let page-paper = sys.inputs.at("paper", default: default-paper)
#let logo-path = "addventure.jpg"
#let section-label = state("section-label", "")
#let sealed-only = sys.inputs.at("sealed_only", default: "0") == "1"

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

// 0. Cover
#if not sealed-only {
  let cover-logo = sys.inputs.at("cover", default: none)
  if cover-logo != none {
    let has-cues = data.at("cue_slots", default: 0) > 0
    cover-page(game-title, cover-logo, has-cues: has-cues)
    pagebreak()
  }
}

// 1. Title page (intro, signal checks, cues, potentials)
#if not sealed-only {
  section-label.update(game-title)
  title-page(data, game-title)
}

// 2. Actions & Inventory (verbs, inventory, signals)
#if not sealed-only {
  pagebreak()
  section-label.update("Actions & Inventory")
  actions-inventory(data)
}

// 3. Rooms
#if not sealed-only and start-room != none {
  for room in data.rooms {
    if room.name == start-room {
      pagebreak()
      if blind { section-label.update("Room " + str(room.id)) }
      else { section-label.update("Room: " + room.name) }
      room-sheet(room, is-start: true, blind: blind)
    }
  }
}
#if not sealed-only {
  for room in data.rooms {
    if room.name != start-room {
      pagebreak()
      if blind { section-label.update("Room " + str(room.id)) }
      else { section-label.update("Room: " + room.name) }
      room-sheet(room, is-start: false, blind: blind)
    }
  }
}

// 4. Ledger
#if not sealed-only {
  pagebreak()
  section-label.update("Ledger")
  story-ledger(data, game-title)
}

// 5. Fragments
#if not data.at("jigsaw", default: false) and data.at("sealed_texts", default: ()).len() > 0 {
  if not sealed-only { pagebreak(weak: true) }
  section-label.update("Fragments")
  sealed-ledger(data)
}
#if not sealed-only and data.at("jigsaw", default: false) and data.at("jigsaw_data", default: none) != none {
  pagebreak(weak: true)
  section-label.update("Cut Pages")
  sealed-jigsaw(data)
}
