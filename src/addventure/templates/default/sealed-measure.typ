// Pass 1: Render sealed text content to measure its natural height.
// Page width = content width + 2*margin, height = auto.
#let raw-data = read(sys.inputs.data)
#let data = json(raw-data)

#let margin = 2mm
#set page(width: eval(data.content_w) + 2 * margin, height: auto, margin: margin)
#set text(size: 10pt)
#set par(justify: true)
#set align(left)

#eval(data.content, mode: "markup")
