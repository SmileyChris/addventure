import sys
from pathlib import Path

from pypdf import PdfReader, PdfWriter
from pypdf.generic import (
    ArrayObject,
    DictionaryObject,
    FloatObject,
    NameObject,
    NumberObject,
    TextStringObject,
)

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from addventure.fillable import make_fillable


def _write_link_fixture(path: Path) -> None:
    writer = PdfWriter()
    page = writer.add_blank_page(width=200, height=200)

    for annotation in [
        _link_annotation([10, 10, 40, 30], "form://cross/alpha"),
        _link_annotation([50, 10, 100, 30], "form://id/beta"),
        _link_annotation([110, 10, 170, 30], "https://example.com/plain-link"),
    ]:
        writer.add_annotation(page, annotation)

    with open(path, "wb") as handle:
        writer.write(handle)


def _link_annotation(rect: list[float], uri: str) -> DictionaryObject:
    action = DictionaryObject()
    action[NameObject("/S")] = NameObject("/URI")
    action[NameObject("/URI")] = TextStringObject(uri)

    annotation = DictionaryObject()
    annotation[NameObject("/Type")] = NameObject("/Annot")
    annotation[NameObject("/Subtype")] = NameObject("/Link")
    annotation[NameObject("/Rect")] = ArrayObject([FloatObject(value) for value in rect])
    annotation[NameObject("/Border")] = ArrayObject([NumberObject(0), NumberObject(0), NumberObject(0)])
    annotation[NameObject("/A")] = action
    return annotation


def test_make_fillable_converts_form_links_to_widgets(tmp_path):
    input_path = tmp_path / "links.pdf"
    output_path = tmp_path / "fillable.pdf"
    _write_link_fixture(input_path)

    make_fillable(input_path, output_path)

    reader = PdfReader(str(output_path))
    acroform = reader.trailer["/Root"]["/AcroForm"]
    fields = acroform["/Fields"]
    page_annots = reader.pages[0]["/Annots"]

    assert len(fields) == 2
    assert len(page_annots) == 3
    assert {field.get_object()["/FT"] for field in fields} == {"/Btn", "/Tx"}
    assert page_annots[2].get_object()["/Subtype"] == "/Link"
    assert acroform["/DA"] == "/HeBo 10 Tf 0 0 0 rg"


def test_make_fillable_survives_pdf_roundtrip(tmp_path):
    input_path = tmp_path / "links.pdf"
    output_path = tmp_path / "fillable.pdf"
    roundtrip_path = tmp_path / "fillable-roundtrip.pdf"
    _write_link_fixture(input_path)

    make_fillable(input_path, output_path)

    reader = PdfReader(str(output_path))
    writer = PdfWriter()
    writer.clone_document_from_reader(reader)
    with open(roundtrip_path, "wb") as handle:
        writer.write(handle)

    roundtrip_reader = PdfReader(str(roundtrip_path))
    acroform = roundtrip_reader.trailer["/Root"]["/AcroForm"]

    assert len(acroform["/Fields"]) == 2
    assert roundtrip_reader.pages[0]["/Annots"][0].get_object()["/Subtype"] == "/Widget"
