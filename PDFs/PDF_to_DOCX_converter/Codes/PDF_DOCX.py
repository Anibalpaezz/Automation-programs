"""
This script converts all PDF files in the current directory to DOCX format using the pdf2docx library.
The converted files are saved in a subfolder named 'Converted'.

Requirements:
    pip install pdf2docx tqdm
"""

import subprocess
import sys
from pathlib import Path
from pdf2docx import Converter

# ===== progreso opcional con tqdm =====
try:
    from tqdm.auto import tqdm

    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False


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


def convert_pdf_to_docx(pdf_path: Path, output_dir: Path) -> None:
    """
    Converts a single PDF file to DOCX format and saves it in the specified output directory.
    """
    output_path = output_dir / pdf_path.with_suffix(".docx").name
    docx_path = get_available_filename(output_path)

    try:
        print(f"  • Converting {pdf_path.name} → {docx_path.name}")
        cv = Converter(pdf_path)
        cv.convert(docx_path, start=0, end=None)
        cv.close()
        print(f"    ✔ Success: {docx_path.name}")
    except Exception as e:
        print(f"    ✖ Error converting {pdf_path.name}: {e}")


def main():
    # Get the current directory where the script is located
    if getattr(sys, "frozen", False):
        folder_path = Path(sys.executable).parent  # When compiled to .exe
    else:
        folder_path = Path(__file__).parent  # When running as .py

    # Find all PDF files in the current directory
    pdf_files = [f for f in folder_path.glob("*.pdf") if f.is_file()]

    if not pdf_files:
        print("⚠ No PDF files found to convert.")
        return

    # Create output folder if it doesn't exist
    output_folder = folder_path / "Converted"
    output_folder.mkdir(exist_ok=True)

    # Barra de progreso global
    if _HAS_TQDM:
        iterator = tqdm(pdf_files, desc="Converting PDFs", unit="file")
    else:
        iterator = pdf_files

    # Convert all found PDF files
    for idx, pdf_file in enumerate(iterator, start=1):
        if not _HAS_TQDM:
            percent = int(idx * 100 / len(pdf_files))
            print(f"[{idx}/{len(pdf_files)}] ({percent}%)")
        convert_pdf_to_docx(pdf_file, output_folder)

    # Open the output folder when done (only on Windows)
    try:
        if sys.platform.startswith("win"):
            subprocess.Popen(f'explorer "{output_folder}"')
    except Exception:
        pass


if __name__ == "__main__":
    main()
