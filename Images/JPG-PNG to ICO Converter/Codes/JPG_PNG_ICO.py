"""
This script converts all JPG, JPEG, or PNG images in the current directory into ICO format.
Converted icons are saved in 'converted/ico/'.
"""

import sys
from pathlib import Path
from typing import List
from PIL import Image


def get_available_filename(base_path: Path) -> Path:
    """
    Return a unique file path by appending (1), (2), etc., if base_path exists.
    """
    if not base_path.exists():
        return base_path

    stem: str = base_path.stem
    suffix: str = base_path.suffix
    parent: Path = base_path.parent
    counter: int = 1

    while True:
        new_name: str = f"{stem} ({counter}){suffix}"
        new_path: Path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def convert_to_ico(img_path: Path, output_dir: Path) -> None:
    """
    Convert a single image to ICO format and save it in output_dir.
    """
    out_file: Path = output_dir / img_path.with_suffix(".ico").name
    out_file = get_available_filename(out_file)
    try:
        with Image.open(img_path) as img:
            if img.mode not in ("RGB", "RGBA"):
                img = img.convert("RGBA")
            # Optionally specify sizes: sizes=[(64,64), (128,128)]
            img.save(out_file, format="ICO")
        print(f"✔ Converted: {img_path.name} → {out_file.name}")
    except Exception as e:
        print(f"✖ Failed to convert {img_path.name}: {e}")


def main() -> None:
    # Determine base folder
    if getattr(sys, "frozen", False):
        base_folder: Path = Path(sys.executable).parent
    else:
        base_folder: Path = Path(__file__).parent

    # Collect image files with explicit types
    jpg_files: List[Path] = list(base_folder.glob("*.jpg"))
    jpeg_files: List[Path] = list(base_folder.glob("*.jpeg"))
    png_files: List[Path] = list(base_folder.glob("*.png"))

    img_files: List[Path] = jpg_files + jpeg_files + png_files

    if not img_files:
        print("⚠ No JPG, JPEG, or PNG files found to convert.")
        return

    # Prepare output directory
    output_dir: Path = base_folder / "converted" / "ico"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Convert each image
    for img in img_files:
        convert_to_ico(img, output_dir)


if __name__ == "__main__":
    main()
