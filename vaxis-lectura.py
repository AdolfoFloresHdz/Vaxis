# Modulo central de OCR — recibe bytes de imagen y devuelve texto

import io
import numpy as np
from PIL import Image

try:
    import easyocr
    _reader = None
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False
    print("easyocr no instalado. Corre: pip install easyocr")

def leer_imagen(imagen_bytes):
    """
    Recibe los bytes de una imagen y devuelve el texto extraido.
    No escribe ningun archivo en disco.
    """
    if not OCR_DISPONIBLE or not imagen_bytes:
        return None
    global _reader
    try:
        if _reader is None:
            print("Cargando modelo OCR (solo la primera vez)...")
            _reader = easyocr.Reader(["es", "en"], verbose=False)
        img = Image.open(io.BytesIO(imagen_bytes))
        img_array = np.array(img)
        resultados = _reader.readtext(img_array, detail=0)
        return "\n".join(resultados) if resultados else None
    except Exception as e:
        print(f"Error al leer imagen: {e}")
        return None
