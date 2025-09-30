"""
This script compresses all PDF files in the current directory using Ghostscript.
Requires Ghostscript to be installed and added to the system PATH.

Compression levels:
    - /screen   (low quality, smallest size)
    - /ebook    (medium quality)
    - /printer  (high quality)
    - /prepress (very high quality)

Requires:
    - Python
    - Ghostscript (https://www.ghostscript.com/)
    - tqdm (optional, for progress bars)
"""

import subprocess
import sys
from pathlib import Path

# ===== progreso opcional con tqdm =====
try:
    from tqdm.auto import tqdm
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False


def get_available_filename(base_path: Path) -> Path:
    if not base_path.exists():
        return base_path
    stem = base_path.stem
    suffix = base_path.suffix
    parent = base_path.parent
    counter = 1
    while True:
        new_path = parent / f"{stem} ({counter}){suffix}"
        if not new_path.exists():
            return new_path
        counter += 1


def compress_pdf_with_ghostscript(input_pdf: Path, output_dir: Path, quality: str = "/ebook") -> None:
    output_pdf = get_available_filename(output_dir / input_pdf.name)

    # Detectar el nombre del ejecutable de Ghostscript según el sistema operativo
    gs_command = "gswin64c" if sys.platform.startswith("win") else "gs"

    try:
        # Mostrar info en consola
        print(f"  • Compressing: {input_pdf.name}")

        subprocess.run(
            [
                gs_command,
                "-sDEVICE=pdfwrite",
                "-dCompatibilityLevel=1.4",
                f"-dPDFSETTINGS={quality}",
                "-dNOPAUSE",
                "-dQUIET",
                "-dBATCH",
                f"-sOutputFile={str(output_pdf)}",
                str(input_pdf),
            ],
            check=True,
        )
        print(f"    ✔ Saved as: {output_pdf.name}")
    except subprocess.CalledProcessError:
        print(f"    ✖ Ghostscript error while compressing {input_pdf.name}")


def main():
    folder_path = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(__file__).parent
    pdf_files = [p for p in folder_path.glob("*.pdf") if p.is_file()]
    if not pdf_files:
        print("⚠ No PDF files found to compress.")
        return

    output_dir = folder_path / "compressed"
    output_dir.mkdir(exist_ok=True)

    print("Select compression quality:")
    print("  1) Low    (/screen)")
    print("  2) Medium (/ebook)")
    print("  3) High   (/printer)")
    print("  4) Best   (/prepress)")

    quality_map = {"1": "/screen", "2": "/ebook", "3": "/printer", "4": "/prepress"}
    choice = input("Enter choice (1-4): ").strip()
    quality = quality_map.get(choice, "/ebook")

    # Barra de progreso para todos los PDFs
    if _HAS_TQDM:
        iterator = tqdm(pdf_files, desc="Compressing PDFs", unit="file")
    else:
        iterator = pdf_files

    for idx, pdf in enumerate(iterator, start=1):
        if not _HAS_TQDM:
            percent = int(idx * 100 / len(pdf_files))
            print(f"[{idx}/{len(pdf_files)}] ({percent}%)")
        compress_pdf_with_ghostscript(pdf, output_dir, quality)


if __name__ == "__main__":
    main()
