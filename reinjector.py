import os
import json
import csv
import re
from collections import defaultdict
# Cargar la configuración necesaria desde el archivo config.py
from config import (
    DATA_DIR, INPUT_CSV, REINJECT_NOTETAG_REGEXES, NOTETAG_REGEXES,
    EVENT_CODE_HANDLERS
)

def set_value_by_path(data, path, value):
    keys = re.split(r'[:\[\]]+', path)
    keys = [k for k in keys if k]
    current_element = data
    for i, key in enumerate(keys[:-1]):
        if key.isdigit():
            current_element = current_element[int(key)]
        else:
            current_element = current_element[key]
    final_key = keys[-1]
    if final_key.isdigit():
        current_element[int(final_key)] = value
    else:
        current_element[final_key] = value

def get_value_by_path(data, path):
    keys = re.split(r'[:\[\]]+', path)
    keys = [k for k in keys if k]
    current_element = data
    for key in keys:
        if key.isdigit():
            current_element = current_element[int(key)]
        else:
            current_element = current_element[key]
    return current_element

def main():
    if not os.path.exists(INPUT_CSV):
        print(f"Error: El archivo de traducciones '{INPUT_CSV}' no fue encontrado.")
        return

    translations_by_file = defaultdict(list)
    try:
        with open(INPUT_CSV, 'r', encoding='utf-8') as csvfile:
            reader = csv.DictReader(csvfile)
            for row in reader:
                if 'id' in row and 'text' in row and row['id'] and row['text'] is not None:
                    translations_by_file[row['id'].split(':')[0]].append(row)
    except Exception as e:
        print(f"Error leyendo el archivo CSV: {e}")
        return

    print("Iniciando reinyección de textos...")

    for filename, rows in translations_by_file.items():
        filepath = os.path.join(DATA_DIR, filename)
        if not os.path.exists(filepath):
            print(f"  Advertencia: No se encontró el archivo de datos {filepath}, saltando...")
            continue

        print(f"Procesando: {filename}...")
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                data = json.load(f)

            # Separar traducciones en 4 categorías: línea única, multilínea, notetags y scripts
            grouped_multiline = defaultdict(dict)
            single_line = []
            notetags = []
            scripts = []

            # Expresión regular para detectar IDs de script
            script_id_regex = re.compile(r'(.+?):pattern(\d+)_match(\d+)(?:_(\d+))?$')

            for row in rows:
                full_path = row['id'].split(':', 1)[1]

                # 1. Intentar clasificar como script
                match_script = script_id_regex.match(full_path)
                if match_script:
                    base_path, pattern_i, match_j, line_k = match_script.groups()
                    scripts.append({
                        'path': base_path,
                        'pattern_index': int(pattern_i),
                        'match_index': int(match_j),
                        'text': row['text'],
                        'id': row['id']
                    })
                    continue

                # 2. Intentar clasificar como notetag
                match_notetag = re.match(r'(.+):(\w+)$', full_path)
                if match_notetag:
                    path, tag_name = match_notetag.groups()
                    if tag_name in NOTETAG_REGEXES:
                        notetags.append({'path': path, 'tag': tag_name, 'text': row['text']})
                        continue

                # 3. Intentar clasificar como multilínea
                match_multiline = re.match(r'(.+)_(\d+)$', full_path)
                if match_multiline:
                    base_path, index = match_multiline.groups()
                    grouped_multiline[base_path][int(index)] = row['text']
                else:
                    # 4. Si no, es una línea única
                    single_line.append({'path': full_path, 'text': row['text']})

            # --- INYECCIÓN POR CATEGORÍAS ---

            # 1. Inyectar textos de una sola línea
            for t in single_line:
                set_value_by_path(data, t['path'], t['text'])

            # 2. Inyectar textos multilínea reconstruidos
            for base_path, parts in grouped_multiline.items():
                final_text = "\n".join(parts[k] for k in sorted(parts.keys()))
                set_value_by_path(data, base_path, final_text)

            # 3. Inyectar textos de notetags con regex
            for tag_info in notetags:
                path = tag_info['path']
                tag_name = tag_info['tag']
                regex = REINJECT_NOTETAG_REGEXES[tag_name]
                original_string = get_value_by_path(data, path)
                new_string = regex.sub(r'\g<1>' + tag_info['text'] + r'\g<3>', original_string)
                set_value_by_path(data, path, new_string)

            # 4. Inyectar textos de scripts con regex
            for script_info in scripts:
                # Obtener el comando de evento original para obtener el código
                event_path = script_info['path'].rsplit(':', 1)[0]
                event_command = get_value_by_path(data, event_path)
                code = event_command.get('code')

                if code in EVENT_CODE_HANDLERS and EVENT_CODE_HANDLERS[code]['type'] == 'script':
                    handler = EVENT_CODE_HANDLERS[code]
                    param_index = handler['param_index']
                    pattern = handler['patterns'][script_info['pattern_index']]

                    # Usamos una función para reemplazar solo la n-ésima coincidencia
                    match_count = 0
                    target_match = script_info['match_index']

                    def repl(matchobj):
                        nonlocal match_count
                        if match_count == target_match:
                            match_count += 1
                            # Reconstruir el string con el texto traducido
                            return matchobj.group(0).replace(matchobj.group(1), script_info['text'])
                        else:
                            match_count += 1
                            return matchobj.group(0)

                    original_script = event_command['parameters'][param_index]
                    new_script = pattern.sub(repl, original_script)
                    event_command['parameters'][param_index] = new_script
                else:
                    print(f"  Advertencia: No se encontró un manejador de script para el ID: {script_info['id']}")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"  Error inesperado procesando {filename}: {e}")

    print("\nReinyección completada.")

if __name__ == '__main__':
    main()
