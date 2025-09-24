import re

# ==============================================================================
# CONFIGURACIÓN PRINCIPAL PARA EL USUARIO
# ==============================================================================

# --- Lista de Códigos de Evento a Extraer ---
EXTRACTABLE_EVENT_CODES = [
    101, 102, 401, 405, 108, 320, 324, 325, 355, 655,
]

# ==============================================================================
# BASE DE DATOS DE MANEJADORES DE CÓDIGOS DE EVENTO
# ==============================================================================

EVENT_CODE_HANDLERS = {
    # --- MENSAJES ---
    101: {"description": "Nombre del Hablante (Show Text)", "type": "simple", "param_index": 4},
    102: {"description": "Opciones (Show Choices)", "type": "array", "param_index": 0},
    401: {"description": "Cuerpo del Mensaje (Show Text)", "type": "simple", "param_index": 0},
    405: {"description": "Texto Desplazable (Show Scrolling Text)", "type": "simple", "param_index": 0},
    108: {"description": "Comentario (Comment)", "type": "simple", "param_index": 0},

    # --- ACTORES ---
    320: {"description": "Cambiar Nombre de Actor", "type": "simple", "param_index": 1},
    324: {"description": "Cambiar Apodo de Actor", "type": "simple", "param_index": 1},
    325: {"description": "Cambiar Perfil de Actor", "type": "simple", "param_index": 1},

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
        "prefix_processing": True,  # Habilitamos la misma lógica que el código 355
        # Se usa el mismo patrón que el código 355
        "pattern": re.compile(r'(\$gameVariables\.setValue\(\d+,\s*)(".*?")(\);?)')
    },
}

# ==============================================================================
# OTRAS CONFIGURACIONES
# ==============================================================================

DATA_DIR = 'data/'
OUTPUT_CSV = 'traducciones.csv'
INPUT_CSV = 'traducciones.csv'
EXCLUDED_FILES = {'Animations.json', 'MapInfos.json', 'Tilesets.json'}
FILENAME_KEYS = {'battleback1Name', 'battleback2Name', 'parallaxName', 'characterName', 'faceName'}
AUDIO_PARENT_KEYS = {'bgm', 'bgs', 'me', 'se'}
SAFE_TEXT_KEYS = {'name', 'description', 'displayName', 'profile', 'message1', 'message2', 'message3', 'message4'}

NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'<breakMsg:(.*?)>', re.IGNORECASE)
}

REINJECT_NOTETAG_REGEXES = {
    'breakMsg': re.compile(r'(<breakMsg:)(.*?)(>)', re.IGNORECASE)
}
