#!/usr/bin/env python3
"""
Script para convertir cocoCapi.png a .ico con margen seguro.
"""

import os
from pathlib import Path

from PIL import Image, ImageOps

PADDING_RATIO = 0.78  # porcentaje del lienzo ocupado por el grafico
BASE_ICON_SIZE = 512  # resolucion base para preservar nitidez
OUTPUT_SIZES = [256, 128, 96, 64, 48, 32, 24, 16]


def convert_png_to_ico() -> bool:
    """Convertir cocoCapi.png a .ico en varios tamaños con padding."""

    png_path = Path("cocoCapi.png")
    if not png_path.exists():
        print(f"Error: No se encontro {png_path}")
        return False

    try:
        source = Image.open(png_path).convert("RGBA")
        max_render = Image.new("RGBA", (BASE_ICON_SIZE, BASE_ICON_SIZE), (0, 0, 0, 0))

        target_box = int(BASE_ICON_SIZE * PADDING_RATIO)
        fitted = ImageOps.contain(source, (target_box, target_box), Image.Resampling.LANCZOS)
        offset = (
            (BASE_ICON_SIZE - fitted.width) // 2,
            (BASE_ICON_SIZE - fitted.height) // 2,
        )
        max_render.paste(fitted, offset, fitted)

        ico_path = Path("cocoCapi.ico")
        max_render.save(
            ico_path,
            format="ICO",
            sizes=[(size, size) for size in OUTPUT_SIZES],
        )

        print(f"Icono creado exitosamente: {ico_path}")
        print(f"Tamanos incluidos: {OUTPUT_SIZES}")
        return True

    except Exception as exc:
        print(f"Error al convertir imagen: {exc}")
        return False


def main() -> bool:
    """Funcion principal."""
    print("CapiAgentes - Creador de Icono")
    print("=" * 35)

    success = convert_png_to_ico()

    if success:
        print()
        print("Icono listo para usar en PyInstaller")
        print("Archivo: cocoCapi.ico")
    else:
        print()
        print("Error al crear el icono")

    return success


if __name__ == "__main__":
    main()
