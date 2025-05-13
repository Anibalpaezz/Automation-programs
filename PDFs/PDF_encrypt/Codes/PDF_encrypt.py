"""
This script encrypts all PDF files in the current directory with a specified password.
Encrypted files are saved in a subfolder named 'encrypted'.
"""
import sys
from pathlib import Path
from PyPDF2 import PdfReader, PdfWriter


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


def encrypt_pdf(input_pdf: Path, output_dir: Path, password: str) -> None:
    """
    Encrypts a single PDF with the given password and saves it to the output directory.
    """
    output_path = output_dir / input_pdf.name
    output_path = get_available_filename(output_path)

    try:
        reader = PdfReader(input_pdf)
        writer = PdfWriter()

        for page in reader.pages:
            writer.add_page(page)

        writer.encrypt(password)
        with open(output_path, "wb") as f:
            writer.write(f)

        print(f"✔ Encrypted: {input_pdf.name} → {output_path.name}")
    except Exception as e:
        print(f"✖ Failed to encrypt {input_pdf.name}: {e}")


def main():
    # Detect whether we're running from .py or .exe
    if getattr(sys, 'frozen', False):
        folder_path = Path(sys.executable).parent
    else:
        folder_path = Path(__file__).parent

    # Define output folder and password
    output_folder = folder_path / "Encrypted"
    output_folder.mkdir(exist_ok=True)
    password = "1234"  # You can change this or make it user-configurable

    # Find all PDF files
    pdf_files = [f for f in folder_path.glob("*.pdf") if f.is_file()]

    if not pdf_files:
        print("⚠ No PDF files found to encrypt.")
        return

    # Encrypt each PDF
    for pdf_file in pdf_files:
        encrypt_pdf(pdf_file, output_folder, password)


if __name__ == "__main__":
    main()
