"""
This script upsamples all JPG, JPEG, PNG or WEBP images in the current directory
by a user-specified factor (e.g. 2×, 4×) using Lanczos resampling, then applies
an Unsharp Mask to enhance sharpness. Output images go into 'converted/upscaled/'.
"""

import sys
from pathlib import Path
from PIL import Image, ImageFilter
from PIL.Image import Resampling

RESAMPLE_LANCZOS = Resampling.LANCZOS



def get_available_filename(base_path: Path) -> Path:
    """
    Return a unique file path by appending (1), (2), etc., if base_path exists.
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


def ask_scale_factor() -> float:
    """
    Ask the user for an upscaling factor (e.g. 2 for 2×, 3 for 3×).
    """
    while True:
        val = input("Enter upscale factor (e.g. 2 for 2×, 4 for 4×): ").strip()
        try:
            f = float(val)
            if f > 1:
                return f
        except ValueError:
            pass
        print("Invalid factor. Please enter a number greater than 1.")


def upscale_and_sharpen(img_path: Path, factor: float, output_dir: Path) -> None:
    """
    Upscales the image by the given factor using Lanczos, then applies UnsharpMask.
    """
    out_file = output_dir / img_path.with_suffix(img_path.suffix).name
    out_file = get_available_filename(out_file)
    try:
        with Image.open(img_path) as img:
            # 1) Convert to RGBA para procesar cualquier modo
            working = img.convert("RGBA")

            # 2) Upscale con Lanczos
            new_size = (int(working.width * factor), int(working.height * factor))
            up = working.resize(new_size, resample=RESAMPLE_LANCZOS)

            # 3) Aplicar filtro de nitidez
            enhanced = up.filter(ImageFilter.UnsharpMask(radius=2, percent=150, threshold=3))

            # 4) Si es JPEG, eliminar alfa
            if img.format and img.format.upper() == "JPEG":
                final = enhanced.convert("RGB")
            else:
                final = enhanced

            # 5) Guardar en mismo formato
            final.save(out_file, format=img.format)
        print(f"✔ Upscaled: {img_path.name} → {out_file.name} ({factor}×)")
    except Exception as e:
        print(f"✖ Failed on {img_path.name}: {e}")



def main():
    # Determine working folder
    if getattr(sys, "frozen", False):
        base_folder = Path(sys.executable).parent
    else:
        base_folder = Path(__file__).parent

    # Gather all supported image files
    patterns = ["*.jpg", "*.jpeg", "*.png", "*.webp"]
    img_files: list[Path] = []
    for pat in patterns:
        img_files += [f for f in base_folder.glob(pat) if f.is_file()]

    if not img_files:
        print("⚠ No JPG, JPEG, PNG or WEBP files found.")
        return

    # Ask for scale factor
    factor = ask_scale_factor()

    # Prepare output folder
    output_dir = base_folder / "upscaled"
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process each image
    for img in img_files:
        upscale_and_sharpen(img, factor, output_dir)


if __name__ == "__main__":
    main()
