// main-combined.typ — Multi-chapter entry point
// Layout: Cover, Shared Actions & Inventory, then per chapter:
//         Title page, Rooms, Ledger, Fragments
#import "style.typ": page-paper as default-paper, page-margin, body-font, title-font
#import "cover.typ": cover-page
#import "section-title-page.typ": title-page
#import "section-actions.typ": actions-inventory
#import "room-sheet.typ": room-sheet
#import "ledger.typ": story-ledger
#import "sealed-ledger.typ": sealed-ledger

// Read JSON data
#let data-path = sys.inputs.at("data")
#let data = json(data-path)

#let game-title = upper(data.at("game_title", default: "Addventure"))
#let blind = data.at("blind", default: false)

#let page-paper = sys.inputs.at("paper", default: default-paper)
#let logo-path = "addventure.jpg"
#let section-label = state("section-label", "")
#let footer-title = state("footer-title", game-title)

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
      text(font: title-font, size: 7pt, weight: "bold", fill: luma(150))[#footer-title.get()]
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
#let cover-logo = sys.inputs.at("cover", default: none)
#if cover-logo != none {
  let has-cues = data.chapters.any(ch => ch.at("cue_slots", default: 0) > 0)
  cover-page(game-title, cover-logo, has-cues: has-cues)
  pagebreak()
}

// 1. Shared Actions & Inventory
#section-label.update("Actions & Inventory")
#actions-inventory(data)

// 2. Per-chapter sections
#for chapter in data.chapters {
  let ch-title = upper(chapter.metadata.at("title", default: "Chapter"))
  let parent = chapter.metadata.at("parent_title", default: none)
  let display-title = if parent != none { upper(parent) + " — " + ch-title } else { ch-title }
  let start-room = chapter.at("start_room", default: none)

  // Title page (intro, signal checks, cues, potentials)
  pagebreak()
  footer-title.update(display-title)
  section-label.update(display-title)
  title-page(chapter, display-title)

  // Rooms
  if start-room != none {
    for room in chapter.rooms {
      if room.name == start-room {
        pagebreak()
        if blind { section-label.update("Room " + str(room.id)) }
        else { section-label.update("Room: " + room.name) }
        room-sheet(room, is-start: true, blind: blind)
      }
    }
  }
  for room in chapter.rooms {
    if room.name != start-room {
      pagebreak()
      if blind { section-label.update("Room " + str(room.id)) }
      else { section-label.update("Room: " + room.name) }
      room-sheet(room, is-start: false, blind: blind)
    }
  }

  // Ledger
  pagebreak()
  section-label.update("Ledger")
  story-ledger(chapter, display-title)

  // Fragments
  if not chapter.at("jigsaw", default: false) and chapter.at("sealed_texts", default: ()).len() > 0 {
    pagebreak(weak: true)
    section-label.update("Fragments")
    sealed-ledger(chapter)
  }
}
