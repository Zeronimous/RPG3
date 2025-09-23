import re

# ==============================================================================
# CONFIGURACIÓN PRINCIPAL PARA EL USUARIO
# ==============================================================================

# --- Lista de Códigos de Evento a Extraer ---
# Añade o elimina códigos de evento de esta lista para controlar qué textos se
# extraen. El script buscará en la "base de datos" de abajo cómo manejar cada
# uno de estos códigos.
EXTRACTABLE_EVENT_CODES = [
    # --- MENSAJES ---
    101,  # Nombre del hablante en "Mostrar Texto"
    102,  # Textos de las opciones en "Mostrar Opciones"
    401,  # Cuerpo del mensaje en "Mostrar Texto"
    405,  # Texto completo en "Mostrar Texto Desplazable"
    108,  # Comentarios (a menudo usados para notas o texto a traducir)

    # --- ACTORES ---
    320,  # Cambiar Nombre de Actor
    324,  # Cambiar Apodo de Actor
    325,  # Cambiar Perfil de Actor

    # --- SCRIPTS (CASO AVANZADO) ---
    355,  # Comando "Script" (extrae texto de dentro de cadenas de JS)
    655,  # Comando "Script" (continuación)
]


# ==============================================================================
# BASE DE DATOS DE MANEJADORES DE CÓDIGOS DE EVENTO
# (Normalmente no necesitas modificar esto, a menos que encuentres un nuevo
# código de evento o un patrón de script no soportado)
# ==============================================================================

EVENT_CODE_HANDLERS = {
    # --- MENSAJES ---
    101: {
        "description": "Nombre del Hablante (Show Text)",
        "type": "simple",
        "param_index": 4
    },
    102: {
        "description": "Opciones (Show Choices)",
        "type": "array",
        "param_index": 0
    },
    401: {
        "description": "Cuerpo del Mensaje (Show Text)",
        "type": "simple",
        "param_index": 0
    },
    405: {
        "description": "Texto Desplazable (Show Scrolling Text)",
        "type": "simple",
        "param_index": 0
    },
    108: {
        "description": "Comentario (Comment)",
        "type": "simple",
        "param_index": 0
    },

    # --- ACTORES ---
    320: {
        "description": "Cambiar Nombre de Actor (Change Actor Name)",
        "type": "simple",
        "param_index": 1
    },
    324: {
        "description": "Cambiar Apodo de Actor (Change Actor Nickname)",
        "type": "simple",
        "param_index": 1
    },
    325: {
        "description": "Cambiar Perfil de Actor (Change Actor Profile)",
        "type": "simple",
        "param_index": 1
    },

    # --- SCRIPTS (CASO AVANZADO) ---
    355: {
        "description": "Comando de Script",
        "type": "script",
        "param_index": 0,
        "prefix_processing": True,  # Aplicar lógica de prefijo a este comando
        # Patrón para capturar el contenido completo del string
        # Grupo 1: $gameVariables.setValue(X,
        # Grupo 2: "String completo con comillas"
        # Grupo 3: );
        "pattern": re.compile(r'(\$gameVariables\.setValue\(\d+,\s*)(".*?")(\);?)')
    },
    655: {
        "description": "Comando de Script (Continuación)",
        "type": "script",
        "param_index": 0,
        "prefix_processing": False, # No aplicar lógica de prefijo a las continuaciones
        # Patrón simple para capturar un string entre comillas
        "pattern": re.compile(r'(")(.*?)(")')
    },
}


# ==============================================================================
# OTRAS CONFIGURACIONES
# ==============================================================================

# --- Rutas de Archivos y Directorios ---
DATA_DIR = 'data/'
OUTPUT_CSV = 'traducciones.csv'
INPUT_CSV = 'traducciones.csv'

# --- Exclusiones de Archivos ---
EXCLUDED_FILES = {'Animations.json', 'MapInfos.json', 'Tilesets.json'}

# --- Claves de Diccionario a Procesar o Ignorar (Fuera de los eventos) ---
FILENAME_KEYS = {'battleback1Name', 'battleback2Name', 'parallaxName', 'characterName', 'faceName'}
AUDIO_PARENT_KEYS = {'bgm', 'bgs', 'me', 'se'}
SAFE_TEXT_KEYS = {'name', 'description', 'displayName', 'profile', 'message1', 'message2', 'message3', 'message4'}

# --- Expresiones Regulares para 'notetags' ---
# Para extraer texto de campos 'note'
NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'<breakMsg:(.*?)>', re.IGNORECASE)
}

# --- Expresiones Regulares para la Reinyección de 'notetags' ---
REINJECT_NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'(<breakMsg:)(.*?)(>)', re.IGNORECASE)
}
