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
  v(0.3in)

  block(width: 85%, inset: (x: 7.5%))[
    #set text(size: 10pt)
    #set par(leading: 0.7em, spacing: 1em)

    *The core mechanic* is addition. Pick a verb and add its number to an object's number. Look up the resulting sum in the Master Potentials List. If it's listed, read the matching Story Ledger entry aloud. If it's not listed, nothing happens --- try something else!

    *Your sheets:*
    - *Verb Sheet* --- your available actions, each with a number
    - *Room Sheets* --- one per location, listing the objects you can see and interact with
    - *Inventory* --- tracks items you're carrying and their numbers
    - *Master Potentials List* --- the lookup table: find your sum here to know which Ledger entry to read
    - *Story Ledger* --- the narrative entries that drive the story forward, with instructions to follow

    *Discoveries:* Some actions reveal new objects in a room. When a Ledger entry tells you to add something to a room, write it in that room's Discoveries section.

    *Taking items:* When you pick something up, cross it off the room sheet and record it on your Inventory sheet. Use its inventory number for future actions.

    #if has-cues [
      *Cue Checks:* Some events set up triggers for later. When you receive a Cue, record its number on your Inventory sheet. Each time you enter a new room, add each Cue number to the Room ID and check the Potentials List.
    ]
  ]

  v(1fr)

  // Let's play at bottom
  align(center)[
    #text(font: title-font, size: 18pt, weight: "black", tracking: 0.05em)[
      Let's play...
      #text(size: 24pt)[#game-title!]
    ]
  ]
}
