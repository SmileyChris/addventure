// cover.typ — Optional "How to Play" cover page
#import "style.typ": title-font, body-font

#let cover-page(game-title, logo-path, has-cues: false) = {
  // No header/footer on cover
  set page(footer: none, background: none)

  // Logo + title at top
  align(center)[
    #set par(spacing: 0pt, leading: 0pt)
    #image(logo-path, width: 40%)
    #text(font: title-font, size: 36pt, weight: "black", tracking: 0.1em)[ADDVENTURE]
  ]

  v(1fr)

  // How to play — centred vertically
  align(center)[
    #text(font: title-font, size: 14pt, weight: "bold", tracking: 0.08em)[HOW TO PLAY]
  ]
  v(0.15in)

  context {
  let small = page.height < 10in
  let body-size = if small { 8.5pt } else { 10pt }
  let body-leading = if small { 0.5em } else { 0.7em }
  let body-spacing = if small { 0.7em } else { 1em }
  align(center)[#block(width: 85%)[
    #set align(left)
    #set text(size: body-size)
    #set par(leading: body-leading, spacing: body-spacing)

    *The core mechanic* is addition. Pick a verb and add its number to an object's number. Look up the resulting sum in the Master Potentials List. If it's listed, read the matching Story Ledger entry aloud. If it's not listed, nothing happens --- try something else!

    *Your sheets:*
    - *Title Page* --- game intro and the Potentials List (the lookup table: find your sum here to know which Ledger entry to read)
    - *Actions & Inventory* --- your available verbs (each with a number), inventory tracking slots, and signal codes
    - *Room Sheets* --- one per location, listing the objects you can see and interact with
    - *Story Ledger* --- the narrative entries that drive the story forward, with instructions to follow

    *Discoveries:* Some actions reveal new objects in a room. When a Ledger entry tells you to add something to a room, write it in that room's Discoveries section.

    *Taking items:* When you pick something up, cross it off the room sheet and record it on your Inventory sheet. Use its inventory number for future actions.

    #if has-cues [
      *Cue Checks:* Some events set up triggers for later. When you receive a Cue, record its number on your Inventory sheet. Each time you enter a new room, add each Cue number to the Room ID and check the Potentials List.
    ]
  ]]
  }

  v(1fr)

  // Let's play at bottom
  align(center)[
    #text(font: title-font, size: 18pt, weight: "black", tracking: 0.05em)[
      Let's play...
      #text(size: 24pt)[#game-title!]
    ]
  ]
}
