# 🤖 VAXIS — Variable Autonomous eXecution Integration System

Automatización de respuestas en WhatsApp Web usando Python y Selenium.  
Diseñado para responder mensajes automáticamente y registrar comprobantes de pago de forma inteligente.

---

## ¿Qué hace?

- Detecta mensajes no leídos en WhatsApp Web
- Responde automáticamente según la palabra clave detectada (cada palabra tiene su propia respuesta)
- Si no hay coincidencia con ninguna palabra clave → silencio total, no manda nada
- Recarga la lógica de respuestas en caliente (hot reload) sin reiniciar
- **Detecta imágenes y PDFs de comprobantes de pago** y extrae automáticamente:
  - Nombre del titular / alias del alumno
  - Fecha del pago
  - Monto
  - Últimos dígitos de la tarjeta
- Registra los pagos validados en Google Sheets automáticamente
- Si el comprobante no es legible con suficiente confianza → marca como "pendiente de revisión" en lugar de registrar datos incorrectos

---

## Arquitectura

```
solucion-de-problemas/
├── vaxis.py              # Lanzador principal — NO se edita
├── vaxis_brain.py        # Lógica de respuestas — editable en caliente
├── vaxis_pagos.py        # OCR + parseo de comprobantes de pago
├── vaxis_sheets.py       # Conexión y escritura en Google Sheets
├── alumnos.json          # Lista de alumnos registrados
└── credenciales.json     # Credenciales de Google Cloud (no incluido en el repo)
```

**Separación de responsabilidades:**
- `vaxis.py` controla el ciclo de vida del bot y el hot reload
- `vaxis_brain.py` contiene la lógica de detección y respuesta por palabras clave
- `vaxis_pagos.py` maneja la detección de imágenes/PDFs y el OCR
- `vaxis_sheets.py` registra los pagos validados en Google Sheets

---

## Flujo de comprobantes de pago

```
Llega imagen/PDF
      │
      ▼
Google Cloud Vision OCR
      │
      ├── Alta confianza ──► Extrae datos ──► Registra en Google Sheets ✅
      │
      └── Baja confianza ──► Marca como "Pendiente de revisión" en Sheet ⚠️
```

El registro en Google Sheets queda así:

| Alumno | Fecha | Monto | Últimos dígitos | Semana | Estado |
|--------|-------|-------|-----------------|--------|--------|
| Adolfo Flores | 20/04/26 | $100 | 1234 | Semana 16 | ✅ Validado |
| María López | 20/04/26 | $100 | 5678 | Semana 16 | ⚠️ Revisar |

---

## Palabras clave y respuestas

Cada palabra clave tiene su propia respuesta configurada en `vaxis_brain.py`:

```python
RESPUESTAS = {
    "hola":       "Hola! Ahorita estoy ocupado, en un rato te contesto 🙌",
    "urgente":    "Vi tu mensaje, parece urgente. Dame unos minutos y te llamo. ⚡",
    "gracias":    "Con gusto! 😊",
    # ... más palabras clave
}
```

Si el mensaje no contiene ninguna palabra clave → no se manda ninguna respuesta.

---

## Conceptos técnicos aplicados

| Concepto | Implementación |
|---|---|
| **Automatización de navegador** | Selenium WebDriver con Brave/Chrome |
| **Hot reload** | `importlib.reload()` detecta cambios en `vaxis_brain.py` en tiempo real |
| **JavaScript injection** | `execute_script()` para manipular el DOM de WhatsApp directamente |
| **Espera explícita** | `WebDriverWait` en lugar de `time.sleep()` fijo |
| **Manejo de excepciones** | `StaleElementReferenceException` para elementos que cambian dinámicamente |
| **OCR inteligente** | Google Cloud Vision API para leer comprobantes de pago |
| **Registro automático** | Google Sheets API (gspread) para llevar el control de pagos |
| **Separación de responsabilidades** | Lanzador independiente de la lógica de negocio |

---

## Stack tecnológico

- Python 3.12+
- Selenium 4.x
- WebDriver Manager
- Brave Browser / Chrome
- Google Cloud Vision API
- Google Sheets API (gspread)

---

## Instalación

```bash
pip install selenium webdriver-manager gspread google-cloud-vision
```

Además necesitas:
1. Una cuenta de Google Cloud con Vision API y Sheets API habilitadas
2. Descargar tus credenciales como `credenciales.json` y colocarlas en la raíz del proyecto

> ⚠️ **Nunca subas `credenciales.json` a GitHub.** Está incluido en `.gitignore`.

---

## Uso

1. Configura las palabras clave y respuestas en `vaxis_brain.py`
2. Agrega tus alumnos en `alumnos.json`
3. Ejecuta el lanzador:

```bash
python vaxis.py
```

4. Escanea el QR de WhatsApp Web y presiona Enter
5. VAXIS queda en modo patrulla. Puedes editar `vaxis_brain.py` y los cambios se aplican solos

---

## Autor

**Adolfo Flores Hernández** — Backend Developer  
[linkedin.com/in/adolfo-flores-hdz](https://linkedin.com/in/adolfo-flores-hdz)
