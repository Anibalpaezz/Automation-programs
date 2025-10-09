"""
Este script aplica OCR a todos los PDF del directorio actual y crea PDFs buscables.
Requisitos Python:
    - pdf2image     : pip install pdf2image
    - pytesseract   : pip install pytesseract
    - PyPDF2        : pip install PyPDF2
    - tqdm          : pip install tqdm

Dependencias del sistema:
    • Poppler (para pdf2image): https://github.com/oschwartz10612/poppler-windows/releases/
    • Tesseract OCR: https://github.com/UB-Mannheim/tesseract/wiki
"""

import sys
import io
from pdf2image import convert_from_path, pdfinfo_from_path
import gc
from pathlib import Path
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


def ocr_pdf(
    input_pdf: Path, output_dir: Path, dpi: int = 200, tesseract_timeout: int = 120
) -> None:
    """
    OCR página a página (streaming) con control de timeout y menor uso de RAM.
    """
    print(f"\nProcesando OCR: {input_pdf.name}")
    try:
        # 0) Validaciones rápidas
        if input_pdf.stat().st_size == 0:
            print("✖ PDF vacio. Se omite.")
            return

        # 1) Contar páginas sin renderizarlas
        info = pdfinfo_from_path(str(input_pdf))
        total_pages = int(info.get("Pages", 0))
        if total_pages == 0:
            print("No se pudieron detectar paginas.")
            return

        merger = PdfMerger()

        # 2) Progreso
        if _HAS_TQDM:
            iterator = tqdm(
                range(1, total_pages + 1), desc="Paginas", unit="pag", leave=False
            )
        else:
            iterator = range(1, total_pages + 1)

        last_msg_len = 0
        for page_num in iterator:
            # Renderizar SOLO esta página
            pil_list = convert_from_path(
                str(input_pdf), dpi=dpi, first_page=page_num, last_page=page_num
            )
            if not pil_list:
                print(f"No se pudo renderizar la pagina {page_num}.")
                continue

            pil_img = pil_list[0]

            # 3) OCR con timeout y configuración básica
            #   - psm 3: layout automático; probar 6 si es texto en bloques
            #   - oem 1: LSTM only (suele ser fiable)
            config = "--oem 1 --psm 3"
            try:
                pdf_bytes = pytesseract.image_to_pdf_or_hocr(
                    pil_img,
                    extension="pdf",
                    lang="spa",  # o elimine si hay mezcla de idiomas
                    config=config,
                    timeout=tesseract_timeout,
                )
            except pytesseract.TesseractError as te:
                print(f"✖ Tesseract error en pag {page_num}: {te}")
                pil_img.close()
                continue
            except RuntimeError as rt:
                print(
                    f"✖ Timeout de Tesseract en pag {page_num} (> {tesseract_timeout}s)."
                )
                pil_img.close()
                continue

            merger.append(io.BytesIO(pdf_bytes))

            # Limpiar memoria de la imagen
            pil_img.close()
            del pil_img, pil_list
            gc.collect()

            if not _HAS_TQDM:
                percent = int(page_num * 100 / total_pages)
                msg = f"  • OCR página {page_num}/{total_pages} ({percent}%)"
                pad = " " * max(0, last_msg_len - len(msg))
                _print_inline(msg + pad)
                last_msg_len = len(msg)

        if not _HAS_TQDM:
            sys.stdout.write("\n")

        # 4) Salida
        out_name = input_pdf.stem + "_ocr.pdf"
        out_path = get_available_filename(output_dir / out_name)
        with open(out_path, "wb") as f_out:
            merger.write(f_out)
        merger.close()
        print(f"OCR completado: {out_path.name}")

    except Exception as e:
        print(f"Error de OCR en {input_pdf.name}: {e}")


def main():
    # Carpeta donde vive el script o el exe empacado
    if getattr(sys, 'frozen', False):
        folder_path = Path(sys.executable).parent
    else:
        folder_path = Path(__file__).parent

    # Buscar PDFs en la carpeta
    pdf_files = [f for f in folder_path.glob("*.pdf") if f.is_file()]
    if not pdf_files:
        print("No se encontraron archivos PDF para OCR.")
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
