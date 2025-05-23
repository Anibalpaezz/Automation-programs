"""
This script merges all PDF files in the current directory into a single PDF,
allowing you to choose the merge order: Alphabetical, by modification date, or manually.
The merged file is saved in a subfolder named 'merged'.
"""

import sys
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


def choose_order(pdf_files: list[Path]) -> list[Path]:
    """
    Prompts the user to choose how to order the PDF files before merging.
    Returns a reordered list.
    """
    print("Found the following PDF files:\n")
    for idx, pdf in enumerate(pdf_files, start=1):
        print(f"  {idx}) {pdf.name}")
    print("\nChoose order:")
    print("  A) Alphabetical")
    print("  D) By modification date (oldest first)")
    print("  M) Manual")

    while True:
        choice = input("Enter A, D, or M: ").strip().upper()
        if choice == "A":
            return sorted(pdf_files, key=lambda p: p.name.lower())
        if choice == "D":
            return sorted(pdf_files, key=lambda p: p.stat().st_mtime)
        if choice == "M":
            print("\nEnter the sequence of numbers separated by commas (e.g., 3,1,2):")
            order_input = input("> ").strip()
            try:
                indices = [int(x) for x in order_input.split(",")]
                if set(indices) != set(range(1, len(pdf_files) + 1)):
                    raise ValueError
                return [pdf_files[i - 1] for i in indices]
            except Exception:
                print("Invalid sequence. Please include each number exactly once.")
        else:
            print("Invalid choice. Please enter A, D, or M.")


def merge_pdfs(pdf_list: list[Path], output_dir: Path) -> None:
    """
    Merges all PDFs in pdf_list and saves the result to output_dir.
    """
    if not pdf_list:
        print("⚠ No PDF files to merge.")
        return

    merger = PdfMerger()
    print("\nMerging in this order:")
    for pdf in pdf_list:
        print(f"  • {pdf.name}")
        merger.append(str(pdf))  # type: ignore[attr-defined]

    output_file = get_available_filename(output_dir / "merged.pdf")
    merger.write(str(output_file))  # type: ignore[attr-defined]
    merger.close()
    print(f"\n✔ Merged PDF saved as: {output_file.name}")


def main():
    # Determine folder of script or executable
    if getattr(sys, "frozen", False):
        folder_path = Path(sys.executable).parent
    else:
        folder_path = Path(__file__).parent

    # Find all PDF files
    pdf_files = [p for p in folder_path.glob("*.pdf") if p.is_file()]
    if not pdf_files:
        print("⚠ No PDF files found to merge.")
        return

    # Ask user for ordering
    ordered_pdfs = choose_order(pdf_files)

    # Prepare output folder
    output_folder = folder_path / "merged"
    output_folder.mkdir(exist_ok=True)

    # Merge
    merge_pdfs(ordered_pdfs, output_folder)


if __name__ == "__main__":
    main()
