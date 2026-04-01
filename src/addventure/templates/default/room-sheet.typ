// room-sheet.typ — Per-room page
#import "style.typ": sheet-title, section-title, write-slot, id-box, title-font

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
      #id-box(str(room.id)) #id-box(hide[000])
    ]
  ]

  // Description
  v(1em)
  section-title("Description")
  v(0.3em)
  block(below: 1.5em)[
    #if is-start and room.description != "" {
      text(size: 11pt)[#eval(room.description, mode: "markup")]
    } else {
      write-slot()
      write-slot()
    }
  ]

  // Objects section
  let obj-count = room.objects.len()
  let total-slots = if blind { obj-count + room.discovery_slots } else { obj-count }

  if total-slots > 0 {
    v(1em)
    section-title("Objects in this Room")
    v(0.3em)

    if blind {
      // Blind mode: all slots are blank write-ins (objects + discoveries merged)
      if is-start {
        // Start room: show names, blank ID slots
        for obj in room.objects {
          block(
            width: 100%,
            below: 0.4em,
          )[
            #grid(
              columns: (1fr, auto),
              gutter: 0.5em,
              align(left + horizon)[
                #text(font: "Liberation Sans", size: 10pt)[#obj.name.replace("_", " ")]
              ],
              align(right + horizon)[#id-box(hide[000])],
            )
          ]
          line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
        }
      } else {
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
    } else {
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
              #text(font: "Liberation Sans", size: 10pt)[#obj.name.replace("_", " ")]
            ],
            align(right + horizon)[
              #id-box(str(obj.id))
            ],
            align(right + horizon)[#id-box(hide[000])],
          )
        ]
        line(length: 100%, stroke: (paint: luma(220), thickness: 0.3pt))
      }
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
