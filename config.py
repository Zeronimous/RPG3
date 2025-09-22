import re

# ==============================================================================
# CONFIGURACIÓN
# Modifica estas variables para adaptar los scripts a tu juego.
# ==============================================================================

# --- Rutas de Archivos y Directorios ---
DATA_DIR = 'data/'
OUTPUT_CSV = 'traducciones.csv'
# El archivo CSV de entrada para el script de reinyección. Debe ser el mismo que OUTPUT_CSV.
INPUT_CSV = 'traducciones.csv'


# --- Exclusiones de Archivos ---
# Una lista de nombres de archivos JSON que se ignorarán durante la extracción.
EXCLUDED_FILES = {'Animations.json', 'MapInfos.json', 'Tilesets.json'}


# --- Claves de Diccionario a Procesar o Ignorar ---

# Claves que siempre contienen nombres de archivo y deben ser ignoradas.
FILENAME_KEYS = {'battleback1Name', 'battleback2Name', 'parallaxName', 'characterName', 'faceName'}

# Si una clave 'name' está dentro de un objeto cuya clave es una de estas, se ignorará.
# Útil para evitar traducir nombres de archivos de audio.
AUDIO_PARENT_KEYS = {'bgm', 'bgs', 'me', 'se'}

# Claves que generalmente contienen texto seguro para traducir.
SAFE_TEXT_KEYS = {'name', 'description', 'displayName', 'profile', 'message1', 'message2', 'message3', 'message4'}


# --- Códigos de Evento para Extracción de Texto ---

# Códigos de evento que contienen texto en su primer parámetro.
# Ejemplo: {'code': 401, 'parameters': ['Este es el texto a traducir']}
EVENT_TEXT_CODES = {
    401,  # Mostrar texto (línea principal)
    405,  # Mostrar texto (en ventana con scroll)
}

# Código de evento para "Mostrar Opciones" (Show Choices).
# El texto de las opciones se encuentra en una lista en el primer parámetro.
# Ejemplo: {'code': 102, 'parameters': [['Opción 1', 'Opción 2', ...]]}
EVENT_CHOICE_CODE = 102

# Código de evento que contiene el nombre del hablante (generalmente parte de "Mostrar Texto").
# Especifica el código de evento y el índice del parámetro que contiene el nombre.
# Ejemplo: {'code': 101, 'parameters': [..., ..., ..., ..., 'Nombre del Personaje']}
EVENT_SPEAKER_NAME_CONFIG = {
    'code': 101,
    'param_index': 4
}

# Código para "Control de Variables" cuando asigna un string a una variable.
# Esto a menudo tiene una "firma" de parámetros fijos antes del texto.
# Ejemplo: {'code': 122, 'parameters': [8, 8, 0, 4, '"Texto de la variable"']}
EVENT_CONTROL_VARIABLE_TEXT_CONFIG = {
    'code': 122,
    'param_signature': [8, 8, 0, 4],  # Parámetros fijos que preceden al texto.
    'param_index': 4                  # Índice del parámetro que contiene el texto.
}


# --- Expresiones Regulares para 'notetags' ---
# Para extraer texto de campos 'note' que usan un formato específico.
# La clave (ej. 'breakMsg') se usa en el ID para la reinyección, así que debe ser única.
# Esta configuración será usada tanto por el extractor como por el reinyector.
NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'<breakMsg:(.*?)>', re.IGNORECASE)
    # Ejemplo para otro notetag:
    # 'enemyName': re.compile(r'<Name:(.*?)>', re.IGNORECASE)
}

# --- Expresiones Regulares para la Reinyección ---
# Usado por el script de reinyección para encontrar y reemplazar el texto del notetag.
# Las claves deben coincidir con NOTETAG_REGEXES. El patrón debe tener 3 grupos:
# 1: El prefijo (<tag:), 2: El texto a reemplazar, 3: El sufijo (>).
REINJECT_NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'(<breakMsg:)(.*?)(>)', re.IGNORECASE)
    # Ejemplo:
    # 'enemyName': re.compile(r'(<Name:)(.*?)(>)', re.IGNORECASE)
}
