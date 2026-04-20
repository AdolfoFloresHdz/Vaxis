"""
vaxis_pagos.py — Módulo de detección y parseo de comprobantes de pago
VAXIS — Variable Autonomous eXecution Integration System
"""
import re
import json
import os

try:
    import easyocr
    _reader = None  # Se inicializa la primera vez que se usa
    OCR_DISPONIBLE = True
except ImportError:
    OCR_DISPONIBLE = False
    print("⚠️  easyocr no instalado. Corre: pip install -r requirements.txt")

# ─────────────────────────────────────────────
#  SEMANAS SEGÚN MONTO
# ─────────────────────────────────────────────
SEMANAS_POR_MONTO = {
    100: 1,
    200: 2,
    300: 3,
}

# ─────────────────────────────────────────────
#  CARGAR ALUMNOS
# ─────────────────────────────────────────────
ALUMNOS_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "alumnos.json")

def cargar_alumnos():
    with open(ALUMNOS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)["alumnos"]

# ─────────────────────────────────────────────
#  EXTRAER TEXTO DE IMAGEN (OCR)
# ─────────────────────────────────────────────
def extraer_texto(ruta_imagen):
    """Extrae texto de una imagen usando EasyOCR."""
    if not OCR_DISPONIBLE:
        return None
    try:
        global _reader
        if _reader is None:
            print("🧠 Cargando modelo OCR (solo la primera vez)...")
            _reader = easyocr.Reader(["es", "en"], verbose=False)
        resultados = _reader.readtext(ruta_imagen, detail=0)
        return "\n".join(resultados)
    except Exception as e:
        print(f"⚠️  Error al leer imagen: {e}")
        return None

# ─────────────────────────────────────────────
#  PARSEAR INFORMACIÓN DEL COMPROBANTE
# ─────────────────────────────────────────────
def parsear_monto(texto):
    """Busca el monto transferido en el texto."""
    patrones = [
        r"\$\s?(\d{1,6})(?:[,\.](\d{2}))?",           # $200.00 o $200
        r"(\d{1,6}(?:[,\.]\d{2,3})*)\s?(?:MXN|pesos)", # 200 MXN
        r"Total[:\s]+\$?\s?(\d{1,6}(?:[,\.]\d{2,3})*)",
        r"Importe[:\s]+\$?\s?(\d{1,6}(?:[,\.]\d{2,3})*)",
        r"Cantidad\s+Total[:\s]+\$?\s?(\d{1,6}(?:[,\.]\d{2,3})*)",
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            valor = match.group(1).replace(",", "")
            try:
                return int(float(valor))
            except Exception:
                pass
    return None

def parsear_fecha(texto):
    """Busca una fecha válida en el texto."""
    meses = {
        "enero": "01", "febrero": "02", "marzo": "03",
        "abril": "04", "mayo": "05", "junio": "06",
        "julio": "07", "agosto": "08", "septiembre": "09",
        "octubre": "10", "noviembre": "11", "diciembre": "12"
    }
    # "02 de febrero 2026" o "2 de febrero de 2026"
    match = re.search(
        r"(\d{1,2})\s+de\s+(\w+)\s+(?:de\s+)?(\d{4})",
        texto, re.IGNORECASE
    )
    if match:
        dia, mes_texto, anio = match.groups()
        mes = meses.get(mes_texto.lower())
        if mes:
            return f"{dia.zfill(2)}/{mes}/{anio}"

    # "09/01/2026" o "09-01-2026"
    match = re.search(r"\b(\d{2})[/-](\d{2})[/-](\d{4})\b", texto)
    if match:
        return f"{match.group(1)}/{match.group(2)}/{match.group(3)}"

    # "20/04/26"
    match = re.search(r"\b(\d{2})[/-](\d{2})[/-](\d{2})\b", texto)
    if match:
        return f"{match.group(1)}/{match.group(2)}/20{match.group(3)}"

    return None

def parsear_ultimos_digitos(texto):
    """Busca los últimos 4 dígitos de una tarjeta (opcional)."""
    patrones = [
        r"\*{2,4}\s?(\d{4})",           # **1234 o ****1234
        r"[Xx]{2,4}\s?(\d{4})",          # XX1234 o XXXX1234
        r"terminaci[oó]n\s+(\d{4})",     # terminación 1234
        r"#\d*(\d{4})\b",               # #...1234
    ]
    for patron in patrones:
        match = re.search(patron, texto, re.IGNORECASE)
        if match:
            return match.group(1)
    return None

def parsear_destinatario(texto):
    """
    Detecta si el comprobante es un pago al titular (Adolfo).
    Busca el nombre del destinatario en comprobantes tipo 'Transferiste $X a NOMBRE'.
    """
    match = re.search(
        r"(?:Transferiste|enviaste|transferido\s+a)[^\n]*\n([A-ZÁÉÍÓÚÑ\s]+)",
        texto, re.IGNORECASE
    )
    if match:
        return match.group(1).strip()

    # También busca línea con "a NOMBRE" en mayúsculas después del monto
    match = re.search(r"a\s+([A-ZÁÉÍÓÚÑ]{3,}(?:\s+[A-ZÁÉÍÓÚÑ]{3,})+)", texto)
    if match:
        return match.group(1).strip()

    return None

def buscar_alumno_en_texto(texto, alumnos):
    """Busca si algún nombre/alias de alumno aparece en el texto."""
    texto_upper = texto.upper()
    for alumno in alumnos:
        if alumno["nombre"].upper() in texto_upper:
            return alumno
        if alumno["alias"].upper() in texto_upper:
            return alumno
    return None

# ─────────────────────────────────────────────
#  CALCULAR SEMANAS PAGADAS
# ─────────────────────────────────────────────
def calcular_semanas(monto):
    return SEMANAS_POR_MONTO.get(monto, None)

# ─────────────────────────────────────────────
#  CALCULAR CONFIANZA
# ─────────────────────────────────────────────
def calcular_confianza(fecha, monto, alumno, semanas):
    score = 0
    if fecha:   score += 35
    if monto:   score += 35
    if alumno:  score += 20
    if semanas: score += 10
    return score

# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL
# ─────────────────────────────────────────────
def analizar_comprobante(ruta_imagen):
    """
    Analiza una imagen de comprobante de pago.
    Devuelve un dict con los datos encontrados y el nivel de confianza.
    """
    alumnos = cargar_alumnos()
    texto = extraer_texto(ruta_imagen)

    if not texto:
        return {"estado": "error", "mensaje": "No se pudo leer la imagen"}

    print(f"\n📄 Texto extraído:\n{'-'*40}\n{texto.strip()}\n{'-'*40}")

    fecha   = parsear_fecha(texto)
    monto   = parsear_monto(texto)
    digitos = parsear_ultimos_digitos(texto)
    alumno  = buscar_alumno_en_texto(texto, alumnos)
    semanas = calcular_semanas(monto) if monto else None

    confianza = calcular_confianza(fecha, monto, alumno, semanas)

    resultado = {
        "alumno":    alumno["nombre"] if alumno else None,
        "fecha":     fecha,
        "monto":     monto,
        "semanas":   semanas,
        "digitos":   digitos,
        "confianza": confianza,
        "estado":    "validado" if confianza >= 60 else "pendiente",
    }

    return resultado

# ─────────────────────────────────────────────
#  PRUEBA RÁPIDA — python vaxis_pagos.py imagen.jpg
# ─────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Uso: python vaxis_pagos.py <ruta_imagen>")
        print("Ejemplo: python vaxis_pagos.py imagen1.jpeg")
        sys.exit(1)

    ruta = sys.argv[1]
    print(f"🔍 Analizando: {ruta}")
    resultado = analizar_comprobante(ruta)

    print(f"\n📊 RESULTADO:")
    print(f"   Alumno:    {resultado.get('alumno') or '❌ No encontrado'}")
    print(f"   Fecha:     {resultado.get('fecha')  or '❌ No encontrada'}")
    print(f"   Monto:     ${resultado.get('monto') or '❌ No encontrado'}")
    print(f"   Semanas:   {resultado.get('semanas') or '❌ No determinado'}")
    print(f"   Tarjeta:   {'****' + resultado['digitos'] if resultado.get('digitos') else 'No disponible'}")
    print(f"   Confianza: {resultado.get('confianza')}%")
    print(f"   Estado:    {'✅ Validado' if resultado.get('estado') == 'validado' else '⚠️  Pendiente de revisión'}")
