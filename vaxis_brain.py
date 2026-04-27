from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import importlib.util
import base64
import os
import time
import vaxis_pagos

# Importar vaxis-lectura (guion en el nombre requiere importlib)
_spec = importlib.util.spec_from_file_location(
    "vaxis_lectura",
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaxis-lectura.py")
)
vaxis_lectura = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(vaxis_lectura)

# ─────────────────────────────────────────────
#  DOS LISTAS PARALELAS
#  ENTRADAS[i] → lista de palabras clave
#  RESPUESTAS[i] → texto que se manda si alguna coincide
#
#  Agrega un grupo nuevo: pon la lista en ENTRADAS
#  y la respuesta en RESPUESTAS en la misma posición.
# ─────────────────────────────────────────────

ENTRADAS = [
    # 0 — Saludos
    ["hola", "hey", "buenas", "qué onda", "que onda", "we", "epa", "ey"],
    # 1 — Preguntar si está disponible
    ["estás", "estas", "andas", "available", "disponible"],
    # 2 — Urgente
    ["urgente", "emergencia", "importante", "auxilio", "ayuda"],
    # 3 — Cuándo
    ["cuándo", "cuando", "a qué hora", "a que hora"],
    # 4 — Agradecimiento
    ["gracias", "thank", "grac"],
    # 5 — Confirmación corta
    ["ok", "sale", "okey", "listo", "va", "perfecto", "de acuerdo"],
    # 6 — Preguntar precio / cobro
    ["precio", "cuánto", "cuanto", "costo", "cobras", "tarifa", "cuesta"],
    # 7 — Agendar
    ["clase", "clases", "agendar", "reservar", "apartar", "inscribir"],
]

RESPUESTAS = [
    # 0 — Saludos
    "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    # 1 — Disponibilidad
    "Aquí ando pero ahorita no puedo hablar, luego te marco! 📲",
    # 2 — Urgente
    "Vi tu mensaje, parece urgente. Dame unos minutos y te llamo. ⚡",
    # 3 — Cuándo
    "Hoy mismo te respondo, ahorita estoy en algo. 🕐",
    # 4 — Gracias
    "Con gusto! 😊",
    # 5 — Confirmación
    "Sale! Luego hablamos. 👍",
    # 6 — Precio
    "Ahorita no puedo hablar, pero en cuanto pueda te mando los detalles de precios. 💪",
    # 7 — Clases
    "Me da gusto que te interese! En un momento te confirmo disponibilidad. 📅",
]

# Respuesta automática cuando llega un comprobante (imagen)
RESPUESTA_COMPROBANTE = "¡Gracias por tu comprobante! En un momento lo reviso. 🧾✅"

# Verificación en tiempo de carga
assert len(ENTRADAS) == len(RESPUESTAS), "¡ENTRADAS y RESPUESTAS deben tener el mismo número de elementos!"


# ─────────────────────────────────────────────
#  DESCARGAR IMAGEN DE WHATSAPP WEB
# ─────────────────────────────────────────────
JS_GET_IMAGE = """
var imgs = document.querySelectorAll('div.message-in img[src]');
var img = imgs[imgs.length - 1];
if (!img || !img.src) return null;
try {
    var c = document.createElement('canvas');
    c.width = img.naturalWidth || img.width || 300;
    c.height = img.naturalHeight || img.height || 300;
    c.getContext('2d').drawImage(img, 0, 0);
    return c.toDataURL('image/jpeg', 0.85);
} catch(e) { return null; }
"""

def obtener_imagen_bytes(driver):
    """Lee la imagen del chat de WhatsApp en memoria, sin guardar nada en disco."""
    try:
        data_url = driver.execute_script(JS_GET_IMAGE)
        if not data_url or not data_url.startswith("data:"):
            return None
        _, encoded = data_url.split(",", 1)
        return base64.b64decode(encoded)
    except Exception as e:
        print(f"⚠️  No pude leer imagen: {e}")
        return None

def es_comprobante(resultado):
    """Devuelve True si el OCR encontró datos relevantes de pago."""
    if not resultado or resultado.get("estado") == "error":
        return False
    return bool(resultado.get("monto") or resultado.get("fecha"))


# ─────────────────────────────────────────────
#  BUSCAR RESPUESTA
# ─────────────────────────────────────────────
def buscar_respuesta(texto):
    """Devuelve la respuesta si encuentra alguna palabra clave, o None."""
    texto_lower = texto.lower()
    for i, palabras in enumerate(ENTRADAS):
        if any(palabra in texto_lower for palabra in palabras):
            return RESPUESTAS[i]
    return None


# ─────────────────────────────────────────────
#  LEER NOMBRE DEL CHAT ABIERTO
# ─────────────────────────────────────────────
def obtener_nombre_chat(driver):
    try:
        encabezado = driver.find_element(
            By.XPATH, '//header//span[@dir="auto" and @title]'
        )
        return encabezado.get_attribute("title").strip()
    except Exception:
        return None


# ─────────────────────────────────────────────
#  LEER ÚLTIMO MENSAJE RECIBIDO (texto o caption de imagen)
# ─────────────────────────────────────────────
def obtener_ultimo_mensaje(driver):
    """
    Lee el ULTIMO mensaje entrante y detecta si tiene texto, imagen o ambos.
    Texto e imagen se evalúan dentro del mismo elemento para no mezclar mensajes.
    Devuelve (texto, tiene_imagen).
    """
    try:
        mensajes = driver.find_elements(
            By.XPATH, '//div[contains(@class,"message-in")]'
        )
        if not mensajes:
            return None, False

        ultimo = mensajes[-1]

        # ¿Tiene imagen dentro?
        tiene_imagen = False
        try:
            imgs = ultimo.find_elements(By.XPATH, './/img[@src]')
            tiene_imagen = len(imgs) > 0
        except Exception:
            pass

        # ¿Tiene texto dentro?
        texto = None
        for sel in [
            './/span[contains(@class,"selectable-text")]',
            './/span[@dir="ltr"]',
            './/span[@dir="auto"]',
        ]:
            try:
                spans = ultimo.find_elements(By.XPATH, sel)
                if spans:
                    t = spans[-1].text.strip()
                    if t:
                        texto = t
                        break
            except Exception:
                pass

        return texto, tiene_imagen

    except Exception:
        return None, False


# ─────────────────────────────────────────────
#  ENVIAR RESPUESTA (3 métodos en cascada)
# ─────────────────────────────────────────────
def enviar_respuesta(driver, texto):
    """Intenta enviar un mensaje por 3 métodos distintos."""

    # Método 1: Selenium directo con varios selectores
    selectores_input = [
        '//div[@contenteditable="true"][@data-tab="10"]',
        '//footer//div[@contenteditable="true"]',
        '//div[@contenteditable="true"][@role="textbox"]',
        '//div[@data-testid="conversation-compose-box-input"]',
        '//div[@contenteditable="true"][@title]',
    ]
    for sel in selectores_input:
        try:
            caja = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH, sel))
            )
            caja.click()
            time.sleep(0.4)
            caja.send_keys(texto)
            time.sleep(0.3)
            caja.send_keys(Keys.ENTER)
            time.sleep(0.5)
            return True
        except Exception:
            pass

    # Método 2: JavaScript para enfocar + ActionChains para escribir
    try:
        driver.execute_script("""
            var input = document.querySelector('[contenteditable="true"][data-tab="10"]')
                     || document.querySelector('footer [contenteditable="true"]')
                     || document.querySelector('[contenteditable="true"][role="textbox"]');
            if (input) { input.focus(); input.click(); }
        """)
        time.sleep(0.4)
        actions = ActionChains(driver)
        actions.send_keys(texto)
        actions.send_keys(Keys.ENTER)
        actions.perform()
        time.sleep(0.5)
        return True
    except Exception:
        pass

    # Método 3: Portapapeles (pyperclip)
    try:
        import pyperclip
        pyperclip.copy(texto)
        driver.execute_script("""
            var input = document.querySelector('[contenteditable="true"][data-tab="10"]')
                     || document.querySelector('footer [contenteditable="true"]');
            if (input) { input.focus(); }
        """)
        time.sleep(0.3)
        actions = ActionChains(driver)
        actions.key_down(Keys.CONTROL).send_keys("v").key_up(Keys.CONTROL)
        actions.perform()
        time.sleep(0.3)
        ActionChains(driver).send_keys(Keys.ENTER).perform()
        time.sleep(0.5)
        return True
    except Exception:
        pass

    print("⚠️  No pude enviar el mensaje (los 3 métodos fallaron).")
    return False


# ─────────────────────────────────────────────
#  JAVASCRIPT PARA DETECTAR CHATS NO LEÍDOS
# ─────────────────────────────────────────────
JS_FIND_UNREAD = """
var badges = document.querySelectorAll('span[aria-label*="leído"], span[aria-label*="unread"], span[data-testid="icon-unread-count"]');
if (badges.length === 0) {
    var allSpans = document.querySelectorAll('span');
    var numericBadges = [];
    for (var i = 0; i < allSpans.length; i++) {
        var s = allSpans[i];
        var txt = s.textContent.trim();
        if (/^[0-9]{1,2}$/.test(txt) && s.offsetWidth < 40 && s.offsetWidth > 0) {
            var rect = s.getBoundingClientRect();
            if (rect.left < 500) { numericBadges.push(s); }
        }
    }
    badges = numericBadges;
}
var results = [];
for (var i = 0; i < badges.length; i++) {
    var el = badges[i];
    var parent = el;
    while (parent && parent !== document.body) {
        if (parent.getAttribute('role') === 'listitem' ||
            parent.getAttribute('role') === 'row' ||
            parent.getAttribute('role') === 'option' ||
            (parent.getAttribute('tabindex') && parent.classList.length > 0 && parent.getBoundingClientRect().height > 50)) {
            break;
        }
        parent = parent.parentElement;
    }
    if (parent && parent !== document.body) { results.push(parent); }
}
return results;
"""

JS_FIND_UNREAD_SIMPLE = """
var chatList = document.querySelectorAll('[role="listitem"], [role="row"], [role="option"]');
var unread = [];
for (var i = 0; i < chatList.length; i++) {
    var el = chatList[i];
    var html = el.innerHTML;
    if (html.indexOf('leído') > -1 || html.indexOf('unread') > -1 ||
        html.indexOf('icon-unread-count') > -1) {
        unread.push(el);
    }
}
return unread;
"""


# ─────────────────────────────────────────────
#  FUNCIÓN PRINCIPAL — llamada cada ciclo
# ─────────────────────────────────────────────
_debug_printed = False

def revisar_chats(driver, ya_respondidos):
    global _debug_printed

    # Método 1: JS avanzado
    try:
        chats = driver.execute_script(JS_FIND_UNREAD)
        if chats:
            if not _debug_printed:
                print(f"🎯 JS encontró {len(chats)} chat(s) sin leer.")
            procesar_chats(driver, chats, ya_respondidos)
            return
    except Exception as e:
        if not _debug_printed:
            print(f"⚠️  JS_FIND_UNREAD falló: {e}")

    # Método 2: JS simple
    try:
        chats = driver.execute_script(JS_FIND_UNREAD_SIMPLE)
        if chats:
            if not _debug_printed:
                print(f"🎯 JS simple encontró {len(chats)} chat(s) sin leer.")
            procesar_chats(driver, chats, ya_respondidos)
            return
    except Exception as e:
        if not _debug_printed:
            print(f"⚠️  JS simple falló: {e}")

    # Método 3: XPath fallback
    for sel in ['//div[@role="listitem"]', '//div[@role="row"]', '//div[@role="option"]']:
        try:
            items = driver.find_elements(By.XPATH, sel)
            no_leidos = []
            for item in items:
                try:
                    badges = item.find_elements(
                        By.XPATH,
                        './/span[contains(@aria-label,"leído") or contains(@aria-label,"unread") or @data-testid="icon-unread-count"]'
                    )
                    if badges:
                        no_leidos.append(item)
                except StaleElementReferenceException:
                    continue
            if no_leidos:
                if not _debug_printed:
                    print(f"🎯 XPath encontró {len(no_leidos)} chat(s) sin leer.")
                procesar_chats(driver, no_leidos, ya_respondidos)
                return
        except Exception:
            pass

    if not _debug_printed:
        _debug_printed = True
        print("🔍 Sin chats no leídos detectados (esperando mensajes...)")


# ─────────────────────────────────────────────
#  PROCESAR LISTA DE CHATS NO LEÍDOS
# ─────────────────────────────────────────────
def procesar_chats(driver, chats, ya_respondidos):
    global _debug_printed
    _debug_printed = False

    for chat_el in chats:
        try:
            chat_el.click()
            time.sleep(2)  # Dar tiempo a que cargue el chat completo

            nombre = obtener_nombre_chat(driver) or "chat_desconocido"
            texto, tiene_imagen = obtener_ultimo_mensaje(driver)

            if not texto and not tiene_imagen:
                print(f"⚠️  [{nombre}] No pude leer el mensaje.")
                continue

            clave = (nombre, texto or "__imagen__")
            if clave in ya_respondidos:
                continue

            # Caso 1: solo texto
            if texto and not tiene_imagen:
                print(f"📥 [{nombre}] Mensaje: \"{texto}\"")
                respuesta = buscar_respuesta(texto)
                if respuesta:
                    ok = enviar_respuesta(driver, respuesta)
                    if ok:
                        ya_respondidos.add(clave)
                        print(f"📤 VAXIS respondió a [{nombre}]: \"{respuesta[:40]}...\" ✅")
                    else:
                        print(f"❌ No pude enviar respuesta a [{nombre}]")
                else:
                    ya_respondidos.add(clave)
                    print(f"🤫 [{nombre}] Sin coincidencia — silencio.")

            # Caso 2: texto + imagen (caption)
            elif texto and tiene_imagen:
                print(f"📥 [{nombre}] Imagen con caption: \"{texto}\"")
                respuesta = buscar_respuesta(texto)
                if respuesta:
                    ok = enviar_respuesta(driver, respuesta)
                    if ok:
                        print(f"📤 VAXIS respondió texto a [{nombre}]: \"{respuesta[:40]}...\" ✅")
                imagen_bytes = obtener_imagen_bytes(driver)
                texto_ocr = vaxis_lectura.leer_imagen(imagen_bytes)
                resultado = vaxis_pagos.analizar_comprobante(texto_ocr)
                print(f"🔍 [{nombre}] OCR: {resultado}")
                if es_comprobante(resultado):
                    time.sleep(0.5)
                    ok = enviar_respuesta(driver, RESPUESTA_COMPROBANTE)
                    if ok:
                        ya_respondidos.add(clave)
                        print(f"📤 [{nombre}] Comprobante aprobado ✅")
                else:
                    ya_respondidos.add(clave)
                    print(f"🖼️  [{nombre}] Imagen no es comprobante — silencio.")

            # Caso 3: solo imagen
            else:
                print(f"🖼️  [{nombre}] Solo imagen, sin texto.")
                imagen_bytes = obtener_imagen_bytes(driver)
                texto_ocr = vaxis_lectura.leer_imagen(imagen_bytes)
                resultado = vaxis_pagos.analizar_comprobante(texto_ocr)
                print(f"🔍 [{nombre}] OCR: {resultado}")
                if es_comprobante(resultado):
                    ok = enviar_respuesta(driver, RESPUESTA_COMPROBANTE)
                    if ok:
                        ya_respondidos.add(clave)
                        print(f"📤 [{nombre}] Comprobante aprobado ✅")
                else:
                    ya_respondidos.add(clave)
                    print(f"🖼️  [{nombre}] Imagen sin datos de pago — silencio.")

            time.sleep(0.5)
            try:
                driver.find_element(By.TAG_NAME, "body").send_keys(Keys.ESCAPE)
            except Exception:
                pass
            time.sleep(0.5)

        except StaleElementReferenceException:
            continue
        except Exception as e:
            print(f"⚠️  Error procesando chat: {e}")
            continue
