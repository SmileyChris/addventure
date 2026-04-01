// room-sheet.typ — Per-room page
#import "style.typ": sheet-title, section-title, write-slot, id-box

#let room-sheet(room) = {
  sheet-title("ROOM: " + upper(room.name))

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

  // Objects table
  if room.objects.len() > 0 {
    section-title("Objects in this Room")

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
