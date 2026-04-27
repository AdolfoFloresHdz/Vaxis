"""
vaxis_pagos.py — Módulo de detección y parseo de comprobantes de pago
VAXIS — Variable Autonomous eXecution Integration System
"""
import re
import json
import os


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
def analizar_comprobante(texto):
    """
    Recibe el texto ya extraido por vaxis-lectura y devuelve los datos del comprobante.
    """
    if not texto or not texto.strip():
        return {"estado": "error", "mensaje": "No se pudo leer la imagen"}

    alumnos = cargar_alumnos()

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

