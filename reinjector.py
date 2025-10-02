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
        with open(INPUT_CSV, 'r', encoding='utf-8-sig') as csvfile:
            # Leer el archivo usando tabuladores como delimitador
            reader = csv.DictReader(csvfile, delimiter='\t')
            for row in reader:
                if 'id' in row and 'text' in row and row['id']:
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

            # Agrupar textos multilínea
            grouped_multiline = defaultdict(lambda: {'lines': {}, 'prefix': ''})
            single_translations = []

            for row in rows:
                match_multiline = re.match(r'(.+)_(\d+)$', row['id'])
                if match_multiline:
                    base_id, index = match_multiline.groups()
                    grouped_multiline[base_id]['lines'][int(index)] = row['text']
                    if int(index) == 1 and row['prefix']:
                        grouped_multiline[base_id]['prefix'] = row['prefix']
                else:
                    single_translations.append(row)

            # Inyectar textos multilínea
            for base_id, parts in grouped_multiline.items():
                # Para textos simples, reconstruir la ruta completa
                if parts['prefix']:
                    # Si es un texto simple multilínea, el prefijo es la clave
                    if not parts['prefix'].endswith('.'):
                         final_path = f"{base_id}:{parts['prefix']}"
                         final_text = "\n".join(parts['lines'][k] for k in sorted(parts['lines'].keys()))
                         set_value_by_path(data, final_path, final_text)
                         continue

                # Para scripts y otros, el ID ya es la ruta completa
                full_text = "\n".join(parts['lines'][k] for k in sorted(parts['lines'].keys()))
                final_text = parts['prefix'] + full_text
                set_value_by_path(data, base_id, final_text)


            # Inyectar todos los demás textos
            for row in single_translations:
                full_id = row['id']
                prefix = row['prefix']
                text = row['text']
                final_text = prefix + text
                path_to_set = ""

                # Diferenciar entre un script y un texto simple
                is_script = ':match' in full_id
                is_notetag = not is_script and (':' in prefix) # Heurística para notetags

                if is_script:
                    event_path = full_id.split(':', 1)[1].rsplit(':', 1)[0]
                    event_command = get_value_by_path(data, event_path)
                    code = event_command.get('code')

                    if code in EVENT_CODE_HANDLERS and EVENT_CODE_HANDLERS[code]['type'] == 'script':
                        handler = EVENT_CODE_HANDLERS[code]
                        param_index = handler['param_index']
                        pattern = handler['pattern']

                        new_string_literal = json.dumps(final_text)
                        original_script = event_command['parameters'][param_index]
                        new_script = pattern.sub(r'\g<1>' + new_string_literal + r'\g<3>', original_script, 1)
                        event_command['parameters'][param_index] = new_script
                    continue

                elif is_notetag:
                    path, tag_name = prefix.rsplit(':', 1)
                    regex = REINJECT_NOTETAG_REGEXES[tag_name]
                    original_string = get_value_by_path(data, path)
                    new_string = regex.sub(r'\g<1>' + text + r'\g<3>', original_string)
                    set_value_by_path(data, path, new_string)
                    continue

                else:
                    # Es un texto simple, reconstruir la ruta
                    path_to_set = f"{full_id}:{prefix}" if prefix else full_id
                    # Para textos simples, el prefijo no es parte del texto final
                    final_text = text

                set_value_by_path(data, path_to_set.split(':', 1)[1], final_text)


            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=4)

        except Exception as e:
            print(f"  Error inesperado procesando {filename}: {e}")

    print("\nReinyección completada.")

if __name__ == '__main__':
    main()