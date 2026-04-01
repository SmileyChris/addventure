// room-sheet.typ — Per-room page
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let room-sheet(room, is-start: false, blind: false) = {
  let hide-name = blind and not is-start
  let hide-objects = blind

  // Title
  if hide-name {
    // Blind non-start: small label with heavy rule as write line
    align(center)[
      #block(
        width: 100%,
        below: 0.15em,
      )[
        #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM TITLE]
      ]
      #line(length: 100%, stroke: 1.5pt)
    ]
  } else {
    let title = "ROOM: " + upper(room.name)
    if is-start { title = title + "  ★ START" }
    sheet-title(title)
  }

  // Room ID
  block(below: 1em)[
    #grid(
      columns: (auto, 1fr),
      gutter: 0.5em,
      align(left + horizon)[
        #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[ROOM ID]
      ],
      align(left + horizon)[
        #id-box(str(room.id)) #id-box(hide[000])
      ],
    )
  ]

  // Description
  block(below: 1.5em)[
    #text(font: "Liberation Sans", size: 9pt, fill: luma(80))[DESCRIPTION]
    #v(0.2em)
    #if is-start and room.description != "" {
      text(size: 11pt, style: "italic")[#room.description]
    } else {
      write-slot()
      v(0.3em)
      write-slot()
    }
  ]

  // Objects section
  let obj-count = room.objects.len()
  if obj-count > 0 {
    v(1em)
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
        // Non-start: blank name and ID slots
        for _ in range(obj-count) {
          block(
            width: 100%,
            below: 0.6em,
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

  // Discovery slots
  if room.discovery_slots > 0 {
    v(1em)
    section-title("Discoveries")
    text(size: 9pt, style: "italic")[If objects are discovered in this room, record them here.]
    v(0.4em)

    for _ in range(room.discovery_slots) {
      block(
        width: 100%,
        below: 0.6em,
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
