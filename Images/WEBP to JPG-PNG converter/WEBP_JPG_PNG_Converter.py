"""
This script converts all WEBP images in the current directory to either JPG or PNG format.
The user is prompted to choose the desired output format.
Converted files are saved in 'converted/jpg/' or 'converted/png/'.
"""

import sys
from pathlib import Path
from PIL import Image


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


def convert_webp(image_path: Path, output_format: str, output_dir: Path) -> None:
    """
    Converts a WEBP image to the specified format and saves it in the output directory.
    """
    output_file = output_dir / image_path.with_suffix(f".{output_format.lower()}").name
    output_file = get_available_filename(output_file)

    try:
        with Image.open(image_path) as img:
            if output_format.lower() == "jpg":
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    img = img.convert("RGBA")
                    background = Image.new(
                        "RGB", img.size, (255, 255, 255)
                    )  # white background
                    background.paste(
                        img, mask=img.split()[3]
                    )  # use alpha channel as mask
                    img = background
                else:
                    img = img.convert("RGB")
            img.save(output_file, "JPEG" if output_format.lower() == "jpg" else "PNG")
        print(f"✔ Converted: {image_path.name} → {output_file.name}")
    except Exception as e:
        print(f"✖ Failed to convert {image_path.name}: {e}")


def ask_format() -> str:
    """
    Asks the user whether to convert to JPG or PNG. Loops until valid input.
    """
    while True:
        choice = input("Convert WEBP images to JPG or PNG? ").strip().lower()
        if choice in ("jpg", "png"):
            return choice
        print("Invalid input. Please type 'jpg' or 'png'.")


def main():
    # Get the current directory where the script is located
    if getattr(sys, "frozen", False):
        folder_path = Path(sys.executable).parent  # When compiled to .exe
    else:
        folder_path = Path(__file__).parent  # When running as .py

    # Ask for desired output format
    output_format = ask_format()

    # Find .webp files
    webp_files = [f for f in folder_path.glob("*.webp") if f.is_file()]

    if not webp_files:
        print("⚠ No WEBP files found in the current directory.")
        return

    # Create output folder
    output_folder = folder_path / "converted" / output_format.lower()
    output_folder.mkdir(parents=True, exist_ok=True)

    # Convert all webp files
    for img in webp_files:
        convert_webp(img, output_format, output_folder)


if __name__ == "__main__":
    main()
