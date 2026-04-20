from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
import importlib
import time
import os

# ─────────────────────────────────────────────
#  CONFIGURACIÓN DE BRAVE
# ─────────────────────────────────────────────
options = Options()
options.binary_location = r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe"
options.add_argument(f"--user-data-dir={os.path.join(os.path.dirname(os.path.abspath(__file__)), 'brave-session')}")

service = Service(ChromeDriverManager().install())
driver = webdriver.Chrome(service=service, options=options)
driver.get("https://web.whatsapp.com/")

print("🚀 VAXIS ha despegado en Brave.")
print("Escanea el QR y cuando veas tus chats, presiona ENTER aquí...")
input()
print("¡Perfecto! Ahora VAXIS está activo. (Presiona Ctrl+C para apagarlo)")

# ─────────────────────────────────────────────
#  HOT RELOAD: cargamos el cerebro
# ─────────────────────────────────────────────
import vaxis_brain

BRAIN_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "vaxis_brain.py")
last_mtime = os.path.getmtime(BRAIN_FILE)

# Estado persistente (sobrevive los reloads)
ya_respondidos = set()

# ─────────────────────────────────────────────
#  BUCLE DE PATRULLA CON HOT RELOAD
# ─────────────────────────────────────────────
print("🤖 VAXIS en modo patrulla... esperando mensajes.")
print("💡 Edita vaxis_brain.py y guarda — los cambios se aplican solos.\n")
time.sleep(3)

while True:
    try:
        # ¿Cambió el archivo del cerebro?
        current_mtime = os.path.getmtime(BRAIN_FILE)
        if current_mtime != last_mtime:
            print("🔄 ¡Recargando cerebro de VAXIS...!")
            importlib.reload(vaxis_brain)
            last_mtime = current_mtime
            print("✅ Cerebro recargado. Nuevas palabras clave y respuestas activas.\n")

        # Ejecutar la lógica del cerebro
        vaxis_brain.revisar_chats(driver, ya_respondidos)

    except Exception as e:
        print(f"⚠️  Error en ciclo: {e}")

    time.sleep(3)