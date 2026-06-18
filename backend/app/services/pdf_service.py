from io import BytesIO

from pypdf import PdfReader


def extract_text_from_pdf(file_bytes: bytes) -> str:
    """Extract all text from a PDF given its raw bytes.

    Returns the combined text of every page, stripped of leading/trailing
    whitespace.  Raises ValueError if no text could be extracted (e.g. a
    purely image-based / scanned PDF).
    """
    reader = PdfReader(BytesIO(file_bytes))
    pages: list[str] = []
    for page in reader.pages:
        text = page.extract_text()
        if text:
            pages.append(text)

    combined = "\n".join(pages).strip()
    if not combined:
        raise ValueError(
            "No extractable text found in the PDF. "
            "The file may be a scanned image — please upload a text-based PDF."
        )
    return combined
