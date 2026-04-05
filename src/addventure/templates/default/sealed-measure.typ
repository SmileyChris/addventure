// Pass 1: Render sealed text content to measure its natural height.
// Page width = content width + 2*margin, height = auto.
#let data = json(sys.inputs.data)

#let margin = 2mm
#set page(width: eval(data.content_w) + 2 * margin, height: auto, margin: margin)
#set text(size: 10pt)
#set par(justify: true)
#set align(left)

#eval(data.content, mode: "markup")
