// room-sheet.typ — Per-room page
#import "style.typ": sheet-title, section-title, write-slot, id-box, strike-text, title-font

#let room-sheet(room, is-start: false, blind: false) = {
  let hide-name = blind and not is-start
  let hide-objects = blind

  // Title
  if hide-name {
    // Blind non-start: small label with heavy rule as write line
    block(
      width: 100%,
      below: 0.15em,
    )[
      #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM NAME]
    ]
    line(length: 100%, stroke: 1.5pt)
  } else {
    let title = upper(room.name)
    if is-start {
      block(width: 100%, below: 0.15em)[
        #grid(
          columns: (auto, 1fr, auto),
          align(left + bottom)[
            #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[START ROOM]
          ],
          align(center + bottom)[
            #text(font: title-font, size: 20pt, weight: "black", tracking: 0.1em)[#title]
          ],
          align(right + bottom)[
            #hide[#text(font: "Liberation Sans", size: 9pt)[START ROOM]]
          ],
        )
      ]
      line(length: 100%, stroke: 1.5pt)
    } else {
      sheet-title(title)
    }
  }

  // Room ID
  block(width: 100%, below: 1em)[
    #align(center)[
      #box(baseline: -35%)[#text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM ID]]
      #h(0.5em)
      #id-box(str(room.id), crossable: true) #id-box(hide[000])
    ]
  ]

  // Description
  v(1em)
  section-title("Description")
  v(0.3em)
  block(below: 1.5em)[
    #if is-start and room.description != "" {
      box(width: 100%, height: 1.2em, stroke: (bottom: 0.5pt + luma(200)))[
        #text(size: 11pt)[#eval(room.description, mode: "markup")]
      ]
      write-slot(uppercase: false)
    } else {
      write-slot(uppercase: false)
      write-slot(uppercase: false)
    }
  ]

  // Actions and objects
  let prefix = if "entry_prefix" in room { room.entry_prefix } else { "A" }
  let room-actions = if "actions" in room { room.actions } else { () }
  let obj-count = room.objects.len()
  let act-count = room-actions.len()

  // Actions section (direct ledger references) — before objects
  // In blind mode, actions are merged into the blank slot pool below.
  if room-actions.len() > 0 and not blind {
    v(1em)
    section-title("Actions")
    v(0.3em)

    for act in room-actions {
      block(
        width: 100%,
        below: 0.4em,
      )[
        #grid(
          columns: (1fr, auto),
          gutter: 0.5em,
          align(left + horizon)[
            #strike-text(text(font: "Liberation Sans", size: 10pt)[#act.name.replace("_", " ")])
          ],
          align(right + horizon)[
            #text(font: "Liberation Sans", size: 10pt, weight: "bold")[#prefix\-#str(act.entry)]
          ],
        )
      ]
      line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
    }
  }

  // Objects section
  let total-slots = if blind { obj-count + act-count + room.discovery_slots } else { obj-count }

  if blind {
    // Blind mode: all slots are blank write-ins (actions + objects + discoveries merged)
    if is-start and total-slots > 0 {
      v(1em)
      section-title("Objects in this Room")
      v(0.3em)
      // Start room: show names, blank ID slots (actions first, then objects)
      for act in room-actions {
        block(
          width: 100%,
          below: 0.4em,
        )[
          #grid(
            columns: (1fr, auto),
            gutter: 0.5em,
            align(left + horizon)[
              #strike-text(text(font: "Liberation Sans", size: 10pt)[#act.name.replace("_", " ")])
            ],
            align(right + horizon)[#id-box(hide[000])],
          )
        ]
        line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
      }
      for obj in room.objects {
        block(
          width: 100%,
          below: 0.4em,
        )[
          #grid(
            columns: (1fr, auto),
            gutter: 0.5em,
            align(left + horizon)[
              #strike-text(text(font: "Liberation Sans", size: 10pt)[#obj.name.replace("_", " ")])
            ],
            align(right + horizon)[#id-box(hide[000])],
          )
        ]
        line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
      }
    } else if total-slots > 0 {
      v(1em)
      section-title("Objects in this Room")
      v(0.3em)
      // Non-start: all blank
      for _ in range(total-slots) {
        block(
          width: 100%,
          below: 0.8em,
        )[
          #grid(
            columns: (1fr, auto),
            gutter: 0.5em,
            align(left + bottom)[#write-slot()],
            align(right + horizon)[#id-box(hide[000])],
          )
        ]
      }
    }
  } else if obj-count > 0 {
    v(1em)
    section-title("Objects in this Room")
    v(0.3em)
    // Normal mode: show names and IDs, with empty box for state changes
    for obj in room.objects {
      block(
        width: 100%,
        below: 0.4em,
      )[
        #grid(
          columns: (1fr, auto, auto),
          gutter: 0.5em,
          align(left + horizon)[
            #strike-text(text(font: "Liberation Sans", size: 10pt)[#obj.name.replace("_", " ")])
          ],
          align(right + horizon)[
            #id-box(str(obj.id), crossable: true)
          ],
          align(right + horizon)[#id-box(hide[000])],
        )
      ]
      line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
    }
  }

  // Discovery slots (non-blind, or blind start room)
  if (not blind or is-start) and room.discovery_slots > 0 {
    v(1em)
    section-title("Discoveries")
    text(size: 9pt, style: "italic")[If objects are discovered in this room, record them here.]
    v(0.4em)

    for _ in range(room.discovery_slots) {
      block(
        width: 100%,
        below: 0.8em,
      )[
        #grid(
          columns: (1fr, auto),
          gutter: 0.5em,
          align(left + bottom)[#write-slot()],
          align(right + horizon)[#id-box(hide[000])],
        )
      ]
    }
  }

}
