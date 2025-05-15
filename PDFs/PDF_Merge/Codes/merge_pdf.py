"""
This script merges all PDF files in the current directory into a single PDF.
The merged file is saved in a subfolder named 'merged'.
"""

from pathlib import Path
from PyPDF2 import PdfMerger


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


def merge_pdfs(pdf_list: list[Path], output_dir: Path) -> None:
    """
    Merges all PDFs in pdf_list and saves the result to output_dir.
    """
    if not pdf_list:
        print("⚠ No PDF files found to merge.")
        return

    output_file = get_available_filename(output_dir / "merged.pdf")
    merger = PdfMerger()

    print("Merging the following files:")
    for pdf in pdf_list:
        print(f" • {pdf.name}")
        merger.append(str(pdf))  # type: ignore[attr-defined]

    merger.write(str(output_file))  # type: ignore[attr-defined]
    merger.close()
    print(f"\n✔ Merged PDF saved as: {output_file.name}")


def main():
    # Determine the folder where the script is located
    folder_path = Path(__file__).parent

    # Find all PDF files in the folder, sorted alphabetically
    pdf_files = sorted([f for f in folder_path.glob("*.pdf") if f.is_file()])

    # Create output directory
    output_folder = folder_path / "merged"
    output_folder.mkdir(exist_ok=True)

    # Merge and save
    merge_pdfs(pdf_files, output_folder)


if __name__ == "__main__":
    main()
