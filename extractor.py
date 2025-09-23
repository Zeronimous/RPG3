import os
import json
import csv
import re
# Cargar la configuración desde el archivo config.py
from config import (
    DATA_DIR, OUTPUT_CSV, EXCLUDED_FILES, FILENAME_KEYS, AUDIO_PARENT_KEYS,
    SAFE_TEXT_KEYS, NOTETAG_REGEXES, EXTRACTABLE_EVENT_CODES, EVENT_CODE_HANDLERS
)

def is_skippable(value):
    if not value or not isinstance(value, str):
        return True

    stripped_value = value.strip()
    # Consideramos "saltable" si está vacío, es un marcador de RPG Maker, o es solo una comilla.
    return (not stripped_value or
            stripped_value.startswith('◆') or
            stripped_value.startswith('--') or
            stripped_value in ['"', "'"])

def yield_text(base_id, text, prefix=""):
    """
    Ayudante para generar texto. Normaliza los saltos de línea, filtra líneas
    no deseadas y, si el texto es multilínea, lo divide y añade sufijos al ID.
    También propaga el prefijo si existe.
    """
    if not text:
        return

    normalized_text = text.replace('\\n', '\n')
    if '\n' in normalized_text:
        lines = normalized_text.split('\n')
        for i, line in enumerate(lines):
            if not is_skippable(line):
                yield {'id': f"{base_id}_{i+1}", 'prefix': prefix, 'text': line}
    else:
        if not is_skippable(normalized_text):
            yield {'id': base_id, 'prefix': prefix, 'text': normalized_text}

def find_translatable_text(data, path, filename):
    # --- PROCESAMIENTO DE LISTAS (DE EVENTOS O DE OTROS ELEMENTOS) ---
    if isinstance(data, list):
        for i, item in enumerate(data):
            if item is None:
                continue
            new_path = f"{path}[{i}]"
            yield from find_translatable_text(item, new_path, filename)
        return

    # --- PROCESAMIENTO DE DICCIONARIOS (OBJETOS JSON) ---
    if not isinstance(data, dict):
        return

    # Rama 1: Manejar comandos de evento de forma dinámica
    if 'code' in data and 'parameters' in data:
        code = data.get('code', 0)
        if code in EXTRACTABLE_EVENT_CODES and code in EVENT_CODE_HANDLERS:
            handler = EVENT_CODE_HANDLERS[code]
            handler_type = handler.get("type")
            param_index = handler.get("param_index")

            # --- Lógica de extracción basada en el tipo de manejador ---
            if handler_type == "simple":
                if len(data['parameters']) > param_index:
                    text = data['parameters'][param_index]
                    yield from yield_text(f"{filename}:{path}:parameters[{param_index}]", text)

            elif handler_type == "array":
                if len(data['parameters']) > param_index:
                    choices = data['parameters'][param_index]
                    if isinstance(choices, list):
                        for i, choice in enumerate(choices):
                            yield from yield_text(f"{filename}:{path}:parameters[{param_index}][{i}]", choice)

            elif handler_type == "script":
                if len(data['parameters']) > param_index:
                    script_text = data['parameters'][param_index]
                    pattern = handler.get("pattern")
                    if pattern:
                        for match_num, match in enumerate(pattern.finditer(script_text)):
                            # El grupo 2 contiene el string completo (ej. '"Prefijo.Texto"')
                            if len(match.groups()) < 2: continue
                        full_string_literal = match.group(2)

                        # Quitar las comillas de los extremos para analizar el contenido
                        inner_text = full_string_literal[1:-1]

                        prefix = ""
                        text_to_translate = inner_text

                        # Aplicar la lógica de prefijos si está activada en la config
                        if handler.get("prefix_processing"):
                            try:
                                # Intentar dividir por el primer punto
                                potential_prefix, potential_text = inner_text.split('.', 1)
                                # Validar las condiciones del prefijo
                                is_single_word = ' ' not in potential_prefix.strip()
                                no_space_after = not potential_text.startswith(' ')

                                if is_single_word and no_space_after:
                                    prefix = potential_prefix + '.'
                                    text_to_translate = potential_text
                            except ValueError:
                                # split() falló, significa que no hay punto, así que no hay prefijo.
                                # Se usará el texto completo.
                                pass

                        special_id = f"{filename}:{path}:parameters[{param_index}]:match{match_num}"
                        yield from yield_text(special_id, text_to_translate, prefix)
        # No continuamos buscando en los parámetros de un comando de evento
        return

    # Rama 2: Manejar todos los demás objetos (no son comandos de evento)
    parent_key = path.split(':')[-1] if path else ''
    for key, value in data.items():
        # Regla 1: Ignorar claves que son nombres de archivo
        if key in FILENAME_KEYS:
            continue
        # Regla 2: Ignorar 'name' si el padre es un objeto de audio
        if key == 'name' and parent_key in AUDIO_PARENT_KEYS:
            continue
        # Regla 3: Ignorar 'name' de un objeto de evento
        is_map_event = 'pages' in data and 'name' in data and filename.startswith('Map')
        is_common_event = 'list' in data and 'name' in data and filename == 'CommonEvents.json'
        if (is_map_event or is_common_event) and key == 'name':
            continue

        new_path = f"{path}:{key}" if path else key

        # Manejo especial para el campo 'note' con regex
        if key == 'note' and isinstance(value, str):
            for tag_name, regex in NOTETAG_REGEXES.items():
                for match in regex.finditer(value):
                    if match.group(1):
                        special_id = f"{filename}:{new_path}:{tag_name}"
                        yield from yield_text(special_id, match.group(1))
            # Continuar la búsqueda recursiva por si el valor es un objeto complejo
            yield from find_translatable_text(value, new_path, filename)

        elif key in SAFE_TEXT_KEYS and value:
            yield from yield_text(f"{filename}:{new_path}", value)
        else:
            yield from find_translatable_text(value, new_path, filename)

def extract_text_from_system(data, path, filename):
    # Procesar los arrays de "tipos"
    type_arrays = ['armorTypes', 'elements', 'equipTypes', 'skillTypes', 'weaponTypes']
    for array_name in type_arrays:
        if array_name in data and isinstance(data[array_name], list):
            for i, text in enumerate(data[array_name]):
                # El primer elemento a menudo es nulo o vacío
                if i == 0 and not text:
                    continue
                if text:
                    yield from yield_text(f"{filename}:{array_name}[{i}]", text)

    # Procesar el objeto "terms"
    if 'terms' in data:
        terms = data['terms']
        for category in ['basic', 'commands', 'params']:
            if category in terms:
                for i, text in enumerate(terms[category]):
                    if text: # Añadida comprobación para evitar valores nulos
                        yield from yield_text(f"{filename}:terms:{category}[{i}]", text)
        if 'messages' in terms:
            for key, text in terms['messages'].items():
                if text: # Añadida comprobación para evitar valores nulos
                    yield from yield_text(f"{filename}:terms:messages:{key}", text)

def main():
    all_texts = []
    processed_ids = set()

    if not os.path.exists(DATA_DIR):
        print(f"Error: El directorio '{DATA_DIR}' no fue encontrado.")
        return

    print("Iniciando extracción de texto...")

    for filename in sorted(os.listdir(DATA_DIR)):
        if not filename.endswith('.json') or filename in EXCLUDED_FILES:
            continue

        filepath = os.path.join(DATA_DIR, filename)
        print(f"Procesando: {filename}")
        with open(filepath, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
                if not data:
                    continue

                results = []
                if filename == 'System.json':
                    results = list(extract_text_from_system(data, '', filename))
                else:
                    results = list(find_translatable_text(data, '', filename))

                for item in results:
                    if item['id'] not in processed_ids:
                        all_texts.append(item)
                        processed_ids.add(item['id'])

            except json.JSONDecodeError:
                print(f"  Advertencia: No se pudo decodificar JSON en {filename}.")
            except Exception as e:
                print(f"  Error inesperado procesando {filename}: {e}")

    all_texts.sort(key=lambda x: x['id'])

    try:
        with open(OUTPUT_CSV, 'w', newline='', encoding='utf-8') as csvfile:
            # Añadimos la nueva columna 'prefix' al CSV
            writer = csv.DictWriter(csvfile, fieldnames=['id', 'prefix', 'text'])
            writer.writeheader()
            writer.writerows(all_texts)
        print(f"\nExtracción completada. Se encontraron {len(all_texts)} líneas de texto.")
        print(f"Archivo de salida: {OUTPUT_CSV}")
    except IOError:
        print(f"Error: No se pudo escribir en el archivo {OUTPUT_CSV}.")

if __name__ == '__main__':
    main()
