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
                if 'id' in row and 'text' in row and row['id']:
                    # Asegurarse de que el prefijo sea una cadena, incluso si está ausente en el CSV
                    row['prefix'] = row.get('prefix', '')
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

            # Clasificar todas las traducciones
            grouped_multiline = defaultdict(lambda: {'lines': {}})
            single_line = []
            notetags = []
            scripts = []

            script_id_regex = re.compile(r'.*:parameters\[\d+\]:match\d+')

            for row in rows:
                full_path = row['id'].split(':', 1)[1]

                if script_id_regex.match(row['id']):
                    scripts.append(row)
                    continue

                match_notetag = re.match(r'(.+):(\w+)$', full_path)
                if match_notetag:
                    notetags.append(row)
                    continue

                match_multiline = re.match(r'(.+)_(\d+)$', full_path)
                if match_multiline:
                    base_path, index = match_multiline.groups()
                    grouped_multiline[base_path]['lines'][int(index)] = row['text']
                    if int(index) == 1:
                         grouped_multiline[base_path]['prefix'] = row['prefix']
                else:
                    single_line.append(row)

            # 1. Inyectar textos de una sola línea (NO scripts)
            for t in single_line:
                set_value_by_path(data, t['id'].split(':', 1)[1], t['text'])

            # 2. Inyectar textos multilínea
            for base_path, parts in grouped_multiline.items():
                prefix = parts.get('prefix', '')
                full_text = "\n".join(parts['lines'][k] for k in sorted(parts['lines'].keys()))
                final_text = prefix + full_text
                set_value_by_path(data, base_path, final_text)

            # 3. Inyectar notetags
            for t in notetags:
                path, tag_name = t['id'].split(':', 1)[1].rsplit(':', 1)
                regex = REINJECT_NOTETAG_REGEXES[tag_name]
                original_string = get_value_by_path(data, path)
                new_string = regex.sub(r'\g<1>' + t['text'] + r'\g<3>', original_string)
                set_value_by_path(data, path, new_string)

            # 4. Inyectar scripts
            for s_info in scripts:
                try:
                    event_path = s_info['id'].split(':')[1].rsplit(':', 1)[0]
                    event_command = get_value_by_path(data, event_path)
                    code = event_command.get('code')

                    if code in EVENT_CODE_HANDLERS and EVENT_CODE_HANDLERS[code]['type'] == 'script':
                        handler = EVENT_CODE_HANDLERS[code]
                        param_index = handler['param_index']
                        pattern = handler['pattern']

                        # Reconstruir el texto interno con el prefijo
                        new_inner_text = s_info['prefix'] + s_info['text']
                        # Escapar para que sea un literal JSON seguro y añadir comillas
                        new_string_literal = json.dumps(new_inner_text)

                        original_script = event_command['parameters'][param_index]
                        # Reemplazar solo la parte del string (grupo 2 del patrón en config.py)
                        new_script = pattern.sub(r'\g<1>' + new_string_literal + r'\g<3>', original_script, 1)
                        event_command['parameters'][param_index] = new_script
                except Exception as e:
                    print(f"  Error inyectando script para ID {s_info.get('id', 'N/A')}: {e}")

            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"  Error inesperado procesando {filename}: {e}")

    print("\nReinyección completada.")

if __name__ == '__main__':
    main()
