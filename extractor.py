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

def yield_text(base_id, text, prefix="", is_simple_key=False):
    """
    Ayudante para generar texto. Normaliza saltos de línea, filtra líneas
    no deseadas y, si el texto es multilínea, lo divide y añade sufijos al ID.
    También propaga el prefijo si existe y divide el ID para textos simples.
    """
    if not text:
        return

    final_id = base_id
    final_prefix = prefix

    # Para textos simples (no de scripts), dividimos el ID en ruta (id) y clave (prefix)
    if is_simple_key and not prefix and ':' in base_id:
        try:
            path_part, key_part = base_id.rsplit(':', 1)
            if '[' not in key_part:
                final_id = path_part
                final_prefix = key_part
        except ValueError:
            pass

    normalized_text = text.replace('\\n', '\n')
    if '\n' in normalized_text:
        lines = normalized_text.split('\n')
        for i, line in enumerate(lines):
            if not is_skippable(line):
                # El prefijo (la clave) solo se asocia con la primera línea
                current_prefix = final_prefix if i == 0 else ""
                # Para multilínea, el ID debe ser consistente y completo
                yield {'id': f"{base_id}_{i+1}", 'prefix': current_prefix, 'text': line}
    else:
        if not is_skippable(normalized_text):
            yield {'id': final_id, 'prefix': final_prefix, 'text': normalized_text}

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

            if handler_type == "simple":
                if len(data['parameters']) > param_index:
                    text = data['parameters'][param_index]
                    yield from yield_text(f"{filename}:{path}:parameters[{param_index}]", text, is_simple_key=True)

            elif handler_type == "array":
                if len(data['parameters']) > param_index:
                    choices = data['parameters'][param_index]
                    if isinstance(choices, list):
                        for i, choice in enumerate(choices):
                            yield from yield_text(f"{filename}:{path}:parameters[{param_index}][{i}]", choice, is_simple_key=True)

            elif handler_type == "script":
                if len(data['parameters']) > param_index:
                    script_text = data['parameters'][param_index]
                    pattern = handler.get("pattern")
                    if pattern:
                        for match_num, match in enumerate(pattern.finditer(script_text)):
                            if len(match.groups()) < 2:
                                continue

                            full_string_literal = match.group(2)
                            inner_text = full_string_literal[1:-1]

                            prefix_to_yield = ""
                            text_to_yield = inner_text

                            if handler.get("prefix_processing"):
                                try:
                                    potential_prefix, potential_text = inner_text.split('.', 1)
                                    if ' ' not in potential_prefix.strip() and not potential_text.startswith(' '):
                                        prefix_to_yield = potential_prefix + '.'
                                        text_to_yield = potential_text
                                except ValueError:
                                    pass

                            special_id = f"{filename}:{path}:parameters[{param_index}]:match{match_num}"
                            yield from yield_text(special_id, text_to_yield, prefix=prefix_to_yield)
        return

    # Rama 2: Manejar todos los demás objetos
    for key, value in data.items():
        if key in FILENAME_KEYS: continue
        if key == 'name' and path.split(':')[-1] in AUDIO_PARENT_KEYS: continue

        is_map_event = 'pages' in data and 'name' in data and filename.startswith('Map')
        is_common_event = 'list' in data and 'name' in data and filename == 'CommonEvents.json'
        if (is_map_event or is_common_event) and key == 'name': continue

        new_path = f"{path}:{key}" if path else key

        if key == 'note' and isinstance(value, str):
            for tag_name, regex in NOTETAG_REGEXES.items():
                for match in regex.finditer(value):
                    if match and match.group(1):
                        special_id = f"{filename}:{new_path}:{tag_name}"
                        yield from yield_text(special_id, match.group(1), is_simple_key=True)
            yield from find_translatable_text(value, new_path, filename)

        elif key in SAFE_TEXT_KEYS and value:
            yield from yield_text(f"{filename}:{new_path}", value, is_simple_key=True)
        else:
            yield from find_translatable_text(value, new_path, filename)

def extract_text_from_system(data, path, filename):
    type_arrays = ['armorTypes', 'elements', 'equipTypes', 'skillTypes', 'weaponTypes']
    for array_name in type_arrays:
        if array_name in data and isinstance(data[array_name], list):
            for i, text in enumerate(data[array_name]):
                if i == 0 and not text: continue
                if text:
                    yield from yield_text(f"{filename}:{array_name}[{i}]", text, is_simple_key=True)

    if 'terms' in data:
        terms = data['terms']
        for category in ['basic', 'commands', 'params']:
            if category in terms:
                for i, text in enumerate(terms[category]):
                    if text:
                        yield from yield_text(f"{filename}:terms:{category}[{i}]", text, is_simple_key=True)
        if 'messages' in terms:
            for key, text in terms['messages'].items():
                if text:
                    yield from yield_text(f"{filename}:terms:messages:{key}", text, is_simple_key=True)

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
                if not data: continue

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
        print(f"Escribiendo {len(all_texts)} líneas en {OUTPUT_CSV}...")
        with open(OUTPUT_CSV, 'w', encoding='utf-8-sig') as f:
            # Escribir la cabecera con tabuladores
            f.write("id\tprefix\ttext\n")
            # Escribir cada fila
            for row in all_texts:
                id_val = str(row.get('id', ''))
                prefix_val = str(row.get('prefix', ''))
                # Reemplazar tabuladores en el texto para no corromper el formato
                text_val = str(row.get('text', '')).replace('\n', '\\n').replace('\t', ' ')

                # Escribir la línea, sin comillas y separada por tabuladores
                f.write(f"{id_val}\t{prefix_val}\t{text_val}\n")

        print(f"\nExtracción completada. Se encontraron {len(all_texts)} líneas de texto.")
        print(f"Archivo de salida: {OUTPUT_CSV}")
    except IOError:
        print(f"Error: No se pudo escribir en el archivo {OUTPUT_CSV}.")

if __name__ == '__main__':
    main()