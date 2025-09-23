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
        "extraction_rules": [
            # Regla 1: Intentar encontrar un prefijo válido primero.
            # Prefijo = una palabra (\S+) seguida de un punto (\.)
            # Texto = empieza inmediatamente después, sin espacios (\S.*?)
            {
                "rule_type": "prefix_split",
                "pattern": re.compile(r'(\$gameVariables\.setValue\(\d+,\s*")(\S+\.)(\S.*?)("\);?)'),
                "text_group": 3,
                "reinject_template": r"\g<1>\g<2>{text}\g<4>"
            },
            {
                "rule_type": "prefix_split",
                "pattern": re.compile(r"(\$gameVariables\.setValue\(\d+,\s*')(\S+\.)(\S.*?)('\);?)"),
                "text_group": 3,
                "reinject_template": r"\g<1>\g<2>{text}\g<4>"
            },
            # Regla 2: Si no hay prefijo, extraer el string completo.
            {
                "rule_type": "full_string",
                "pattern": re.compile(r'(\$gameVariables\.setValue\(\d+,\s*")(.*?)("\);?)'),
                "text_group": 2,
                "reinject_template": r"\g<1>{text}\g<3>"
            },
            {
                "rule_type": "full_string",
                "pattern": re.compile(r"(\$gameVariables\.setValue\(\d+,\s*')(.*?)('\);?)"),
                "text_group": 2,
                "reinject_template": r"\g<1>{text}\g<3>"
            }
        ]
    },
    655: {
        "description": "Comando de Script (Continuación)",
        "type": "script",
        "param_index": 0,
        "extraction_rules": [
            # Para las líneas de continuación, asumimos que no hay prefijos complejos.
            {
                "rule_type": "full_string",
                "pattern": re.compile(r'(")(.*?)(")', re.DOTALL),
                "text_group": 2,
                "reinject_template": r"\g<1>{text}\g<3>"
            },
            {
                "rule_type": "full_string",
                "pattern": re.compile(r"(')(.*?)(')", re.DOTALL),
                "text_group": 2,
                "reinject_template": r"\g<1>{text}\g<3>"
            }
        ]
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
