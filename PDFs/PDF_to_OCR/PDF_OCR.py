"""OCR utility for producing searchable PDF files.

This script applies Tesseract OCR to PDF files, turning image-based PDFs into
searchable documents. By default, the script behaves exactly like the original
version: it processes all PDFs placed alongside the script/executable and
stores the OCR'd versions inside an ``ocr`` sub-folder.

The upgrade introduces a command line interface that lets you control where the
input files live, where the results are written, and how Tesseract should run.

Python dependencies (install via ``pip``):
    • pdf2image
    • pytesseract
    • PyPDF2

System dependencies:
    • Poppler (used by pdf2image): https://github.com/oschwartz10612/poppler-windows/releases/
    • Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
"""

from __future__ import annotations

import argparse
import io
import sys
from dataclasses import dataclass
from typing import List, Optional, Sequence

from pathlib import Path

from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfMerger


@dataclass
class OCRConfig:
    """Configuration parameters shared across the OCR workflow."""

    output_dir: Path
    dpi: int = 300
    language: Optional[str] = None
    overwrite: bool = False
    skip_existing: bool = False
    dry_run: bool = False
    poppler_path: Optional[str] = None

    def resolve_output_path(self, source: Path) -> Optional[Path]:
        """Resolve the destination PDF path according to overwrite/skip flags."""

        base_path = self.output_dir / f"{source.stem}_ocr.pdf"

        if self.overwrite:
            return base_path

        if self.skip_existing and base_path.exists():
            return None

        return get_available_filename(base_path)


def get_available_filename(base_path: Path) -> Path:
    """Generate a unique file path by appending ``(1)``, ``(2)``, etc."""

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


def ocr_pdf(input_pdf: Path, config: OCRConfig) -> None:
    """Convert a scanned/image-based PDF into a searchable PDF using OCR."""

    destination = config.resolve_output_path(input_pdf)
    if destination is None:
        print(f"⏭  Skipping (already exists): {input_pdf.name}")
        return

    print(f"Processing OCR for: {input_pdf.name}")
    if config.dry_run:
        print("  • Dry run enabled, no OCR performed.\n")
        return

    try:
        # 1. Render PDF pages as images
        pages = convert_from_path(
            str(input_pdf),
            dpi=config.dpi,
            poppler_path=config.poppler_path,
        )

        # 2. Create a merger to assemble OCR'd pages
        merger = PdfMerger()

        for page_num, pil_img in enumerate(pages, start=1):
            kwargs = {"extension": "pdf"}
            if config.language:
                kwargs["lang"] = config.language

            pdf_bytes = pytesseract.image_to_pdf_or_hocr(pil_img, **kwargs)
            merger.append(io.BytesIO(pdf_bytes))
            print(f"  • OCR on page {page_num}/{len(pages)}")

        # Ensure output directory exists
        destination.parent.mkdir(parents=True, exist_ok=True)

        # 3. Write merged PDF to disk
        with open(destination, "wb") as f_out:
            merger.write(f_out)
        merger.close()

        print(f"✔ OCR complete: {destination.name}\n")
    except Exception as exc:  # noqa: BLE001 - show readable error in console
        print(f"✖ Failed OCR on {input_pdf.name}: {exc}\n")


def parse_arguments(argv: Optional[Sequence[str]] = None) -> argparse.Namespace:
    """Build the command line interface and parse arguments."""

    parser = argparse.ArgumentParser(
        description=(
            "Apply Tesseract OCR to PDF files. Without arguments the script scans "
            "for PDFs in its own directory, mirroring the legacy behaviour."
        )
    )

    parser.add_argument(
        "pdfs",
        nargs="*",
        type=Path,
        help="Explicit PDF files to process. Overrides automatic discovery if provided.",
    )
    parser.add_argument(
        "-i",
        "--input-dir",
        type=Path,
        help="Directory to search for PDF files (defaults to the script/executable directory).",
    )
    parser.add_argument(
        "-o",
        "--output-dir",
        type=Path,
        help="Directory to write OCR results (defaults to <input-dir>/ocr).",
    )
    parser.add_argument(
        "-r",
        "--recursive",
        action="store_true",
        help="Search for PDFs recursively inside the input directory.",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=300,
        help="Rasterisation resolution passed to pdf2image (default: 300).",
    )
    parser.add_argument(
        "--lang",
        dest="language",
        help="Tesseract language codes (e.g. 'eng+spa').",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing *_ocr.pdf files instead of creating numbered copies.",
    )
    parser.add_argument(
        "--skip-existing",
        action="store_true",
        help="Skip PDFs whose *_ocr.pdf output already exists in the destination folder.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List the work that would be carried out without doing any OCR.",
    )
    parser.add_argument(
        "--tesseract-cmd",
        help="Custom path to the tesseract executable (useful on Windows).",
    )
    parser.add_argument(
        "--poppler-path",
        help="Path to the Poppler binaries for pdf2image (if not on PATH).",
    )

    args = parser.parse_args(argv)

    if args.overwrite and args.skip_existing:
        parser.error("--overwrite and --skip-existing are mutually exclusive")

    return args


def discover_pdfs(
    explicit_pdfs: Sequence[Path], input_dir: Path, recursive: bool = False
) -> List[Path]:
    """Return an ordered list of PDF files to process."""

    if explicit_pdfs:
        selected: List[Path] = []
        for pdf in explicit_pdfs:
            candidate = pdf.expanduser()
            if not candidate.is_absolute():
                candidate = (Path.cwd() / candidate).resolve()
            else:
                candidate = candidate.resolve()

            if not candidate.exists():
                print(f"⚠  File not found, skipping: {pdf}")
                continue
            if candidate.suffix.lower() != ".pdf":
                print(f"⚠  Not a PDF file, skipping: {candidate}")
                continue
            selected.append(candidate)

        return selected

    pattern = "**/*.pdf" if recursive else "*.pdf"
    return sorted(path for path in input_dir.glob(pattern) if path.is_file())


def prepare_environment(args: argparse.Namespace) -> None:
    """Apply runtime configuration that depends on CLI arguments."""

    if args.tesseract_cmd:
        pytesseract.pytesseract.tesseract_cmd = args.tesseract_cmd


def main(argv: Optional[Sequence[str]] = None) -> int:
    args = parse_arguments(argv)

    # Determine default base directory (script/executable directory)
    if getattr(sys, "frozen", False):
        default_dir = Path(sys.executable).parent
    else:
        default_dir = Path(__file__).parent

    input_dir = args.input_dir or default_dir
    if not input_dir.exists() or not input_dir.is_dir():
        print(f"✖ Input directory not found: {input_dir}")
        return 1

    output_dir = args.output_dir or (input_dir / "ocr")

    prepare_environment(args)

    config = OCRConfig(
        output_dir=output_dir,
        dpi=args.dpi,
        language=args.language,
        overwrite=args.overwrite,
        skip_existing=args.skip_existing,
        dry_run=args.dry_run,
        poppler_path=args.poppler_path,
    )

    pdf_files = discover_pdfs(args.pdfs, input_dir, recursive=args.recursive)
    if not pdf_files:
        print("⚠ No PDF files found to OCR.")
        return 0

    if config.dry_run:
        print("Dry run – the following PDFs would be processed:")
        for pdf in pdf_files:
            destination = config.resolve_output_path(pdf)
            status = "(skip)" if destination is None else f"→ {destination}"
            print(f"  - {pdf} {status}")
        return 0

    for pdf_file in pdf_files:
        ocr_pdf(pdf_file, config)

    return 0


if __name__ == "__main__":  # pragma: no cover - direct execution entry point
    sys.exit(main())
