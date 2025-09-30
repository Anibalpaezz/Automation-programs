"""
This script applies OCR to all PDF files in the current directory, producing searchable PDF outputs.
Requires:
    - pdf2image     : pip install pdf2image
    - pytesseract   : pip install pytesseract
    - PyPDF2        : pip install PyPDF2
Also install system dependencies:
    • Poppler (for pdf2image): https://github.com/oschwartz10612/poppler-windows/releases/
    • Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
"""

import sys
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfMerger
import io


def get_available_filename(base_path: Path) -> Path:
    """
    Generates a unique file path by appending (1), (2), etc. if the file already exists.
    """
    if not base_path.exists():
        return base_path

    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1

    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def ocr_pdf(input_pdf: Path, output_dir: Path, dpi: int = 300) -> None:
    """
    Converts a scanned/image-based PDF into a searchable PDF using OCR.
    Each page is rasterized, OCR'd, and then combined into one PDF.
    """
    print(f"Processing OCR for: {input_pdf.name}")
    try:
        # 1. Render PDF pages as images
        pages = convert_from_path(str(input_pdf), dpi=dpi)

        # 2. Create a merger to assemble OCR'd pages
        merger = PdfMerger()

        for page_num, pil_img in enumerate(pages, start=1):
            # 3. Perform OCR and get PDF bytes for that page
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(pil_img, extension='pdf')
            merger.append(io.BytesIO(pdf_bytes))
            print(f"  • OCR on page {page_num}/{len(pages)}")

        # 4. Determine output file path
        out_name = input_pdf.stem + "_ocr.pdf"
        out_path = get_available_filename(output_dir / out_name)

        # 5. Write merged PDF to disk
        with open(out_path, "wb") as f_out:
            merger.write(f_out)
        merger.close()

        print(f"✔ OCR complete: {out_path.name}\n")
    except Exception as e:
        print(f"✖ Failed OCR on {input_pdf.name}: {e}\n")


def main():
    # Determine folder where script or exe lives
    if getattr(sys, 'frozen', False):
        folder_path = Path(sys.executable).parent
    else:
        folder_path = Path(__file__).parent

    # Find all PDFs in folder
    pdf_files = [f for f in folder_path.glob("*.pdf") if f.is_file()]
    if not pdf_files:
        print("⚠ No PDF files found to OCR.")
        return

    # Create output directory
    output_folder = folder_path / "ocr"
    output_folder.mkdir(exist_ok=True)

    # Process each PDF
    for pdf_file in pdf_files:
        ocr_pdf(pdf_file, output_folder)


if __name__ == "__main__":
    main()
