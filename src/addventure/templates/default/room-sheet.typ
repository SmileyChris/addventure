// room-sheet.typ — Per-room page
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let room-sheet(room, is-start: false, blind: false) = {
  let hide-name = blind and not is-start
  let hide-objects = blind

  // Title: blank write-in for blind non-start, normal otherwise
  if hide-name {
    // Show only the room ID with a blank title slot
    block(below: 0.2em)[
      #align(center)[
        #block(width: 100%, below: 0.15em)[
          #grid(
            columns: (1fr, auto, 1fr),
            gutter: 0.5em,
            [],
            align(center + horizon)[
              #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM] #h(0.5em) #id-box(str(room.id))
            ],
            [],
          )
        ]
        #line(length: 100%, stroke: 1.5pt)
      ]
    ]
    // Blank line for room name
    v(0.3em)
    text(size: 9pt, style: "italic")[Room name:]
    h(0.5em)
    write-slot(width: 60%)
    v(0.8em)
  } else {
    let title = "ROOM: " + upper(room.name)
    if is-start { title = title + "  ★ START" }
    sheet-title(title)

    // Room ID
    block(below: 1em)[
      #grid(
        columns: (auto, 1fr),
        gutter: 0.5em,
        align(left + horizon)[
          #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM ID]
        ],
        align(left + horizon)[
          #id-box(str(room.id))
        ],
      )
    ]
  }

  // Objects section
  let obj-count = room.objects.len()
  if obj-count > 0 {
    section-title("Objects in this Room")

    if hide-objects {
      // Blind mode: all object slots are blank write-ins
      if is-start {
        // Start room: show names, blank ID slots
        for obj in room.objects {
          block(
            width: 100%,
            below: 0.4em,
          )[
            #grid(
              columns: (1fr, 4em),
              gutter: 0.5em,
              align(left + horizon)[
                #text(font: "Liberation Sans", size: 10pt)[#obj.name]
              ],
              align(right + bottom)[#write-slot(width: 100%)],
            )
          ]
          line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
        }
      } else {
        // Non-start: blank name and ID slots
        for _ in range(obj-count) {
          block(
            width: 100%,
            below: 0.6em,
          )[
            #grid(
              columns: (1fr, 4em),
              gutter: 0.5em,
              align(left + bottom)[#write-slot()],
              align(right + bottom)[#write-slot(width: 100%)],
            )
          ]
        }
      }
    } else {
      // Normal mode: show names and IDs
      for obj in room.objects {
        block(
          width: 100%,
          below: 0.4em,
        )[
          #grid(
            columns: (1fr, auto),
            gutter: 0.5em,
            align(left + horizon)[
              #text(font: "Liberation Sans", size: 10pt)[#obj.name]
            ],
            align(right + horizon)[
              #id-box(str(obj.id))
            ],
          )
        ]
        line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
      }
    }
  }

  // Discovery slots
  if room.discovery_slots > 0 {
    v(1em)
    section-title("Discoveries")
    text(size: 9pt, style: "italic")[Objects may be discovered in this room. Record them here when found.]
    v(0.4em)

    for _ in range(room.discovery_slots) {
      block(
        width: 100%,
        below: 0.6em,
      )[
        #grid(
          columns: (1fr, 4em),
          gutter: 0.5em,
          align(left + bottom)[#write-slot()],
          align(right + bottom)[#write-slot(width: 100%)],
        )
      ]
    }
  }

  // Room alerts section
  v(1em)
  section-title("Room Alerts")
  block(
    width: 100%,
    stroke: (left: 2pt + luma(180)),
    inset: (left: 8pt, y: 6pt),
  )[
    #text(size: 9pt, style: "italic")[
      Some actions in other rooms may affect what you find here. If instructed to update this room's state, record it below.
    ]
  ]
  v(0.5em)
  write-slot()
  v(0.4em)
  write-slot()
}
