"""
Este script aplica OCR a todos los PDF del directorio actual y crea PDFs buscables.
Requisitos Python:
    - pdf2image     : pip install pdf2image
    - pytesseract   : pip install pytesseract
    - PyPDF2        : pip install PyPDF2
Opcional (para barra de progreso bonita):
    - tqdm          : pip install tqdm

Dependencias del sistema:
    • Poppler (para pdf2image): https://github.com/oschwartz10612/poppler-windows/releases/
    • Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
"""

import sys
import io
import time
from pathlib import Path
from pdf2image import convert_from_path
import pytesseract
from PyPDF2 import PdfMerger

# ===== progreso opcional con tqdm =====
try:
    from tqdm.auto import tqdm
    _HAS_TQDM = True
except Exception:
    _HAS_TQDM = False


def get_available_filename(base_path: Path) -> Path:
    """
    Genera un nombre de archivo único añadiendo (1), (2), etc. si ya existe.
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


def _print_inline(msg: str) -> None:
    """
    Imprime en la misma línea (fallback sin tqdm).
    """
    sys.stdout.write("\r" + msg)
    sys.stdout.flush()


def ocr_pdf(input_pdf: Path, output_dir: Path, dpi: int = 300) -> None:
    """
    Convierte un PDF escaneado o de imágenes en un PDF con texto buscable mediante OCR.
    Muestra barra de progreso por página.
    """
    print(f"\nProcesando OCR: {input_pdf.name}")
    try:
        # 1) Renderizar páginas a imágenes
        pages = convert_from_path(str(input_pdf), dpi=dpi)
        total_pages = len(pages)

        # 2) Preparar merger para ensamblar las páginas OCR
        merger = PdfMerger()

        # 3) Progreso por páginas
        if _HAS_TQDM:
            iterator = tqdm(
                enumerate(pages, start=1),
                total=total_pages,
                desc="Páginas",
                unit="pág",
                leave=False
            )
        else:
            iterator = enumerate(pages, start=1)

        last_msg_len = 0
        for page_num, pil_img in iterator:
            # OCR de la página -> bytes PDF de esa página
            pdf_bytes = pytesseract.image_to_pdf_or_hocr(pil_img, extension='pdf')
            merger.append(io.BytesIO(pdf_bytes))

            if _HAS_TQDM:
                # tqdm ya gestiona el avance; opcionalmente podemos set_postfix
                pass
            else:
                # Fallback sin dependencias: porcentaje y páginas
                percent = int(page_num * 100 / total_pages)
                msg = f"  • OCR página {page_num}/{total_pages} ({percent}%)"
                # Limpiar restos si el mensaje nuevo es más corto
                pad = " " * max(0, last_msg_len - len(msg))
                _print_inline(msg + pad)
                last_msg_len = len(msg)

        # Si no hay tqdm, salto de línea para no pisar siguiente print
        if not _HAS_TQDM:
            sys.stdout.write("\n")

        # 4) Nombre de salida
        out_name = input_pdf.stem + "_ocr.pdf"
        out_path = get_available_filename(output_dir / out_name)

        # 5) Escribir PDF final
        with open(out_path, "wb") as f_out:
            merger.write(f_out)
        merger.close()

        print(f"✔ OCR completado: {out_path.name}")
    except Exception as e:
        print(f"✖ Error de OCR en {input_pdf.name}: {e}")


def main():
    # Carpeta donde vive el script o el exe empacado
    if getattr(sys, 'frozen', False):
        folder_path = Path(sys.executable).parent
    else:
        folder_path = Path(__file__).parent

    # Buscar PDFs en la carpeta
    pdf_files = [f for f in folder_path.glob("*.pdf") if f.is_file()]
    if not pdf_files:
        print("⚠ No se encontraron archivos PDF para OCR.")
        return

    # Directorio de salida
    output_folder = folder_path / "ocr"
    output_folder.mkdir(exist_ok=True)

    # Barra de progreso global sobre archivos (si hay tqdm)
    if _HAS_TQDM:
        files_iter = tqdm(pdf_files, desc="Archivos PDF", unit="archivo")
    else:
        files_iter = pdf_files

    for idx, pdf_file in enumerate(files_iter, start=1):
        if not _HAS_TQDM:
            print(f"\n[{idx}/{len(pdf_files)}] {pdf_file.name}")
        ocr_pdf(pdf_file, output_folder)


if __name__ == "__main__":
    main()
