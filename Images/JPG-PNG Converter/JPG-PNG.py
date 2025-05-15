"""
This script converts all JPG/JPEG or PNG images in the current directory to the opposite format.
- If only JPG/JPEG files are present, it converts all to PNG automatically.
- If only PNG files are present, it converts all to JPG automatically.
- If both types are present, it prompts the user to choose.
Converted files are saved in 'converted/png/' or 'converted/jpg/' respectively.
"""

import sys
from pathlib import Path
from PIL import Image


def get_available_filename(base_path: Path) -> Path:
    """
    Return a unique file path by appending (1), (2), etc. if base_path exists.
    """
    if not base_path.exists():
        return base_path
    stem, suffix, parent = base_path.stem, base_path.suffix, base_path.parent
    counter = 1
    while True:
        new_name = f"{stem} ({counter}){suffix}"
        new_path = parent / new_name
        if not new_path.exists():
            return new_path
        counter += 1


def ask_conversion_direction() -> str:
    """
    Ask the user which conversion to perform: jpg->png or png->jpg.
    """
    while True:
        choice = input("Convert images to (jpg) or (png)? ").strip().lower()
        if choice in ("jpg", "png"):
            return choice
        print("Invalid input. Please enter 'jpg' or 'png'.")


def convert_image(img_path: Path, output_format: str, output_dir: Path) -> None:
    """
    Convert a single image to the specified format and save it in output_dir.
    """
    out_suffix = f".{output_format}"
    out_file = output_dir / img_path.with_suffix(out_suffix).name
    out_file = get_available_filename(out_file)
    try:
        with Image.open(img_path) as img:
            if output_format == "jpg":
                # JPEG does not support alpha; provide white background if needed
                if img.mode in ("RGBA", "LA") or (
                    img.mode == "P" and "transparency" in img.info
                ):
                    img = img.convert("RGBA")
                    bg = Image.new("RGB", img.size, (255, 255, 255))
                    bg.paste(img, mask=img.split()[3])
                    img = bg
                else:
                    img = img.convert("RGB")
            save_format = "JPEG" if output_format == "jpg" else "PNG"
            img.save(out_file, format=save_format)
        print(f"✔ Converted: {img_path.name} → {out_file.name}")
    except Exception as e:
        print(f"✖ Failed to convert {img_path.name}: {e}")


def main():
    # Determine base folder
    if getattr(sys, "frozen", False):
        base_folder = Path(sys.executable).parent
    else:
        base_folder = Path(__file__).parent

    # Gather JPG/JPEG and PNG files
    jpg_files = [f for f in base_folder.glob("*.jpg")] + [
        f for f in base_folder.glob("*.jpeg")
    ]
    png_files = [f for f in base_folder.glob("*.png")]

    # Decide conversion direction
    if jpg_files and not png_files:
        target_format = "png"
        images = jpg_files
    elif png_files and not jpg_files:
        target_format = "jpg"
        images = png_files
    else:
        # Mixed or none
        if not jpg_files and not png_files:
            print("⚠ No JPG/JPEG or PNG files found to convert.")
            return
        target_format = ask_conversion_direction()
        if target_format == "png":
            images = jpg_files
        else:
            images = png_files

    # Prepare output directory
    output_dir = base_folder / "converted" / target_format
    output_dir.mkdir(parents=True, exist_ok=True)

    # Perform conversions
    for img in images:
        convert_image(img, target_format, output_dir)


if __name__ == "__main__":
    main()
