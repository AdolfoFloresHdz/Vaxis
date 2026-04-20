from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
import time

# ─────────────────────────────────────────────
#  CONFIGURACIÓN — Cambia esto cuando quieras
#
#  Formato: "palabra_clave": "respuesta"
#  Si el mensaje contiene la palabra clave → manda esa respuesta
#  Si no coincide nada → silencio total (no se manda nada)
# ─────────────────────────────────────────────
RESPUESTAS = {
    "hola":       "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "hey":        "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "buenas":     "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "qué onda":   "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "we":         "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "estás":      "Aquí ando pero ahorita no puedo hablar, luego te marco! 📲",
    "estas":      "Aquí ando pero ahorita no puedo hablar, luego te marco! 📲",
    "andas":      "Aquí ando pero ahorita no puedo hablar, luego te marco! 📲",
    "urgente":    "Vi tu mensaje, parece urgente. Dame unos minutos y te llamo. ⚡",
    "emergencia": "Vi tu mensaje, parece urgente. Dame unos minutos y te llamo. ⚡",
    "importante": "Vi tu mensaje, parece urgente. Dame unos minutos y te llamo. ⚡",
    "cuándo":     "Hoy mismo te respondo, ahorita estoy en algo. 🕐",
    "cuando":     "Hoy mismo te respondo, ahorita estoy en algo. 🕐",
    "gracias":    "Con gusto! 😊",
    "ok":         "Ok! Luego hablamos. 👍",
    "sale":       "Sale! Luego hablamos. 👍",
}


# ─────────────────────────────────────────────
#  FUNCIONES DE DETECCIÓN
# ─────────────────────────────────────────────
def obtener_nombre_chat(driver):
    """Nombre del chat abierto."""
    try:
        encabezado = driver.find_element(
            By.XPATH, '//header//span[@dir="auto" and @title]'
        )
        return encabezado.get_attribute("title").strip()
    except Exception:
        return None


def obtener_ultimo_mensaje(driver):
    """Texto del último mensaje recibido."""
    selectores = [
        '//div[contains(@class,"message-in")]//span[contains(@class,"selectable-text")]',
        '//div[contains(@class,"message-in")]//span[@dir="ltr"]',
        '//div[@data-id]//span[contains(@class,"selectable-text")]',
    ]
    for sel in selectores:
        try:
            mensajes = driver.find_elements(By.XPATH, sel)
            if mensajes:
                texto = mensajes[-1].text.strip()
                if texto:
                    return texto
        except Exception:
            pass
    return None


def enviar_respuesta(driver, texto):
    """Escribe y envía un mensaje."""
    selectores_input = [
        '//div[@contenteditable="true"][@data-tab="10"]',
        '//div[@contenteditable="true"][@role="textbox"]',
        '//div[@contenteditable="true"][@title="Escribe un mensaje aquí"]',
        '//footer//div[@contenteditable="true"]',
        '//div[@data-testid="conversation-compose-box-input"]',
    ]
    for sel in selectores_input:
        try:
            input_box = WebDriverWait(driver, 4).until(
                EC.element_to_be_clickable((By.XPATH, sel))
            )
            input_box.click()
            time.sleep(0.3)
            input_box.send_keys(texto)
            time.sleep(0.3)
            input_box.send_keys(Keys.ENTER)
            return True
        except Exception:
            pass
    print("⚠️  No encontré el cuadro de texto.")
    return False


# ─────────────────────────────────────────────
#  ENFOQUE CON JAVASCRIPT (más confiable)
#  WhatsApp usa React y los elementos cambian
#  mucho, JavaScript dentro de la página es
#  más estable que XPath desde afuera.
# ─────────────────────────────────────────────

JS_FIND_UNREAD = """
// Buscar todos los spans que contengan un número (1, 2, 3...)
// y que sean verdes / badges de no leído
var badges = document.querySelectorAll('span[aria-label*="leído"], span[aria-label*="unread"], span[data-testid="icon-unread-count"]');

// Si no encontramos con aria-label, buscar spans con número puro dentro del sidebar
if (badges.length === 0) {
    var allSpans = document.querySelectorAll('span');
    var numericBadges = [];
    for (var i = 0; i < allSpans.length; i++) {
        var s = allSpans[i];
        var txt = s.textContent.trim();
        // Es un número pequeño (1-99) y es un badge (elemento pequeño)
        if (/^[0-9]{1,2}$/.test(txt) && s.offsetWidth < 40 && s.offsetWidth > 0) {
            // Verificar que esté en el panel lateral (no en un chat abierto)
            var rect = s.getBoundingClientRect();
            if (rect.left < 500) {  // Panel lateral está a la izquierda
                numericBadges.push(s);
            }
        }
    }
    badges = numericBadges;
}

// Para cada badge, subir hasta el contenedor clickeable del chat
var results = [];
for (var i = 0; i < badges.length; i++) {
    var el = badges[i];
    var parent = el;
    // Subir hasta encontrar algo clickeable
    while (parent && parent !== document.body) {
        if (parent.getAttribute('role') === 'listitem' || 
            parent.getAttribute('role') === 'row' ||
            parent.getAttribute('role') === 'option' ||
            (parent.getAttribute('tabindex') && parent.classList.length > 0 && parent.getBoundingClientRect().height > 50)) {
            break;
        }
        parent = parent.parentElement;
    }
    if (parent && parent !== document.body) {
        results.push(parent);
    }
}
return results;
"""

JS_FIND_UNREAD_SIMPLE = """
// Enfoque súper simple: buscar el div que contenga el aria-label del chat
// con "no leído" o "unread" en su texto
var chatList = document.querySelectorAll('[role="listitem"], [role="row"], [role="option"]');
var unread = [];
for (var i = 0; i < chatList.length; i++) {
    var el = chatList[i];
    var html = el.innerHTML;
    // Si contiene un badge de no leído
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
_debug_printed = False  # Solo imprimir debug una vez

def revisar_chats(driver, ya_respondidos):
    """Busca chats no leídos usando JavaScript para máxima compatibilidad."""
    global _debug_printed

    # MÉTODO 1: JavaScript avanzado
    try:
        chats_no_leidos = driver.execute_script(JS_FIND_UNREAD)
        if chats_no_leidos:
            if not _debug_printed:
                print(f"🎯 JS encontró {len(chats_no_leidos)} chat(s) sin leer.")
            procesar_chats(driver, chats_no_leidos, ya_respondidos)
            return
    except Exception as e:
        if not _debug_printed:
            print(f"⚠️  JS_FIND_UNREAD falló: {e}")

    # MÉTODO 2: JavaScript simple
    try:
        chats_no_leidos = driver.execute_script(JS_FIND_UNREAD_SIMPLE)
        if chats_no_leidos:
            if not _debug_printed:
                print(f"🎯 JS simple encontró {len(chats_no_leidos)} chat(s) sin leer.")
            procesar_chats(driver, chats_no_leidos, ya_respondidos)
            return
    except Exception as e:
        if not _debug_printed:
            print(f"⚠️  JS_FIND_UNREAD_SIMPLE falló: {e}")

    # MÉTODO 3: XPath directo (fallback)
    selectores = [
        '//div[@role="listitem"]',
        '//div[@role="row"]',
        '//div[@role="option"]',
    ]
    for sel in selectores:
        try:
            items = driver.find_elements(By.XPATH, sel)
            if items:
                if not _debug_printed:
                    print(f"📋 XPath '{sel}' encontró {len(items)} items en la lista.")
                # Filtrar los que tienen no leído
                no_leidos = []
                for item in items:
                    try:
                        badges = item.find_elements(By.XPATH, './/span[contains(@aria-label,"leído") or contains(@aria-label,"unread") or @data-testid="icon-unread-count"]')
                        if badges:
                            no_leidos.append(item)
                    except StaleElementReferenceException:
                        continue
                if no_leidos:
                    if not _debug_printed:
                        print(f"🎯 Filtrados: {len(no_leidos)} con mensajes sin leer.")
                    procesar_chats(driver, no_leidos, ya_respondidos)
                    return
        except Exception:
            pass

    # Si llegamos aquí, nada funcionó — imprimir diagnóstico UNA VEZ
    if not _debug_printed:
        _debug_printed = True
        print("\n" + "="*50)
        print("🔍 DIAGNÓSTICO: no encontré chats sin leer")
        print("="*50)
        # Ver qué roles hay
        try:
            roles_js = driver.execute_script("""
                var roles = {};
                var all = document.querySelectorAll('[role]');
                for (var i = 0; i < all.length; i++) {
                    var r = all[i].getAttribute('role');
                    roles[r] = (roles[r] || 0) + 1;
                }
                return roles;
            """)
            print(f"📋 Roles encontrados en la página: {roles_js}")
        except Exception:
            pass

        # Ver si hay aria-labels con "leído"
        try:
            leido_count = driver.execute_script("""
                return document.querySelectorAll('[aria-label*="leído"], [aria-label*="unread"]').length;
            """)
            print(f"🏷️  Elementos con aria-label 'leído/unread': {leido_count}")
        except Exception:
            pass

        # Ver HTML del panel lateral (primeros 2000 chars)
        try:
            sidebar_html = driver.execute_script("""
                var pane = document.querySelector('#pane-side') || document.querySelector('[data-testid="chat-list"]');
                if (pane) return pane.innerHTML.substring(0, 2000);
                return 'No encontré #pane-side ni chat-list';
            """)
            print(f"\n📄 HTML del panel lateral (muestra):\n{sidebar_html[:800]}")
        except Exception:
            pass

        print("="*50 + "\n")


def procesar_chats(driver, chats, ya_respondidos):
    """Procesa una lista de elementos de chat no leídos."""
    global _debug_printed
    _debug_printed = False  # Reset para futuras detecciones

    for chat_el in chats:
        try:
            chat_el.click()
            time.sleep(1.5)

            nombre = obtener_nombre_chat(driver) or "chat_desconocido"
            texto  = obtener_ultimo_mensaje(driver)

            if not texto:
                print(f"⚠️  [{nombre}] Entré al chat pero no pude leer el mensaje.")
                continue

            clave = (nombre, texto)
            if clave in ya_respondidos:
                continue

            print(f"📥 [{nombre}] dice: \"{texto}\"")

            texto_lower = texto.lower()
            respuesta = None
            for palabra, resp in RESPUESTAS.items():
                if palabra in texto_lower:
                    respuesta = resp
                    break

            if respuesta:
                ok = enviar_respuesta(driver, respuesta)
                if ok:
                    ya_respondidos.add(clave)
                    print(f"📤 VAXIS respondió a [{nombre}] ✅")
                else:
                    print(f"❌ No pude responder a [{nombre}]")
            else:
                ya_respondidos.add(clave)
                print(f"🤫 [{nombre}] Sin coincidencia, silencio total.")

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
