"""Post-process a Typst-generated PDF to convert form:// link annotations into fillable fields."""

from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DecodedStreamObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)


def _make_text_field(rect: list[float], name: str, font_size: int = 10, bold: bool = False, centered: bool = False, uppercase: bool = False) -> DictionaryObject:
    """Create a PDF text field widget annotation."""
    font_name = "/HeBo" if bold else "/Helv"
    field = DictionaryObject()
    field[NameObject("/Type")] = NameObject("/Annot")
    field[NameObject("/Subtype")] = NameObject("/Widget")
    field[NameObject("/FT")] = NameObject("/Tx")
    field[NameObject("/T")] = TextStringObject(name)
    field[NameObject("/Rect")] = ArrayObject([FloatObject(v) for v in rect])
    field[NameObject("/F")] = NumberObject(4)  # Print flag
    field[NameObject("/DA")] = TextStringObject(f"{font_name} {font_size} Tf 0 0 0 rg")
    field[NameObject("/Border")] = ArrayObject(
        [NumberObject(0), NumberObject(0), NumberObject(0)]
    )
    if centered:
        field[NameObject("/Q")] = NumberObject(1)  # 0=left, 1=center, 2=right
    if uppercase:
        # JavaScript keystroke action to force uppercase
        js_action = DictionaryObject()
        js_action[NameObject("/S")] = NameObject("/JavaScript")
        js_action[NameObject("/JS")] = TextStringObject("event.change = event.change.toUpperCase();")
        aa = DictionaryObject()
        aa[NameObject("/K")] = js_action  # Keystroke trigger
        field[NameObject("/AA")] = aa
    return field


def _make_cross_checkbox(rect: list[float], name: str) -> DictionaryObject:
    """Create a checkbox that draws an X across the box when checked."""
    x1, y1, x2, y2 = rect
    w = x2 - x1
    h = y2 - y1

    field = DictionaryObject()
    field[NameObject("/Type")] = NameObject("/Annot")
    field[NameObject("/Subtype")] = NameObject("/Widget")
    field[NameObject("/FT")] = NameObject("/Btn")
    field[NameObject("/T")] = TextStringObject(name)
    field[NameObject("/Rect")] = ArrayObject([FloatObject(v) for v in rect])
    field[NameObject("/F")] = NumberObject(4)  # Print flag
    field[NameObject("/V")] = NameObject("/Off")
    field[NameObject("/AS")] = NameObject("/Off")
    field[NameObject("/Border")] = ArrayObject(
        [NumberObject(0), NumberObject(0), NumberObject(0)]
    )

    # Custom appearance: diagonal X lines when checked, nothing when off
    on_stream = DecodedStreamObject()
    # Draw two diagonal lines across the box
    on_stream.set_data(
        f"q 1.5 w 0.4 0.4 0.4 RG "
        f"0 0 m {w:.1f} {h:.1f} l S "
        f"0 {h:.1f} m {w:.1f} 0 l S Q".encode()
    )
    on_stream[NameObject("/Type")] = NameObject("/XObject")
    on_stream[NameObject("/Subtype")] = NameObject("/Form")
    on_stream[NameObject("/BBox")] = ArrayObject([FloatObject(0), FloatObject(0), FloatObject(w), FloatObject(h)])

    off_stream = DecodedStreamObject()
    off_stream.set_data(b"")
    off_stream[NameObject("/Type")] = NameObject("/XObject")
    off_stream[NameObject("/Subtype")] = NameObject("/Form")
    off_stream[NameObject("/BBox")] = ArrayObject([FloatObject(0), FloatObject(0), FloatObject(w), FloatObject(h)])

    n_dict = DictionaryObject()
    n_dict[NameObject("/Yes")] = on_stream
    n_dict[NameObject("/Off")] = off_stream

    ap = DictionaryObject()
    ap[NameObject("/N")] = n_dict

    field[NameObject("/AP")] = ap
    field[NameObject("/MK")] = DictionaryObject()  # Empty appearance characteristics

    return field


def make_fillable(input_path: Path, output_path: Path | None = None) -> Path:
    """Convert form:// link annotations to fillable PDF form fields."""
    if output_path is None:
        output_path = input_path

    reader = PdfReader(str(input_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)

    all_fields = []

    for page_num in range(len(writer.pages)):
        page = writer.pages[page_num]
        if "/Annots" not in page:
            continue

        annots = list(page["/Annots"])
        new_annots = []

        for annot_ref in annots:
            annot = annot_ref.get_object()

            if (
                annot.get("/Subtype") == "/Link"
                and "/A" in annot
                and annot["/A"].get("/S") == "/URI"
            ):
                uri = annot["/A"].get("/URI", "")
                if uri.startswith("form://"):
                    rect = [float(v) for v in annot["/Rect"]]
                    parts = uri.replace("form://", "").split("/")
                    field_type = parts[0]
                    field_id = parts[1] if len(parts) > 1 else str(len(all_fields))

                    name = f"f_{page_num}_{field_id}"

                    if field_type == "cross":
                        field = _make_cross_checkbox(rect, name)
                    elif field_type == "id":
                        field = _make_text_field(rect, name, font_size=8, bold=True, centered=True, uppercase=True)
                    elif field_type == "desc":
                        field = _make_text_field(rect, name, font_size=10)
                    else:
                        field = _make_text_field(rect, name, font_size=10, uppercase=True)

                    ref = writer._add_object(field)
                    all_fields.append(ref)
                    new_annots.append(ref)
                    continue

            new_annots.append(annot_ref)

        page[NameObject("/Annots")] = ArrayObject(new_annots)

    if all_fields:
        # Font resources for form fields
        helv = DictionaryObject()
        helv[NameObject("/Type")] = NameObject("/Font")
        helv[NameObject("/Subtype")] = NameObject("/Type1")
        helv[NameObject("/BaseFont")] = NameObject("/Helvetica")

        helv_bold = DictionaryObject()
        helv_bold[NameObject("/Type")] = NameObject("/Font")
        helv_bold[NameObject("/Subtype")] = NameObject("/Type1")
        helv_bold[NameObject("/BaseFont")] = NameObject("/Helvetica-Bold")

        font_dict = DictionaryObject()
        font_dict[NameObject("/Helv")] = writer._add_object(helv)
        font_dict[NameObject("/HeBo")] = writer._add_object(helv_bold)

        dr = DictionaryObject()
        dr[NameObject("/Font")] = font_dict

        acroform = DictionaryObject()
        acroform[NameObject("/Fields")] = ArrayObject(all_fields)
        acroform[NameObject("/DR")] = dr
        acroform[NameObject("/DA")] = TextStringObject("/HeBo 10 Tf 0 0 0 rg")
        acroform[NameObject("/NeedAppearances")] = NameObject("/true")
        writer._root_object[NameObject("/AcroForm")] = acroform

    with open(output_path, "wb") as f:
        writer.write(f)

    return output_path
