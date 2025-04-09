import json

import os
import ast
import re

import dotenv

from app.utils import send_log_to_slack

dotenv.load_dotenv()

CODE_DIR = os.getenv("CODE_DIR")


def extract_from_section(source):
    models_info = {}
    all_functions = []
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        print(f"Cannot parse source: {e}")
        return models_info, all_functions

    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            for base in node.bases:
                if isinstance(base, ast.Name):
                    model_name = node.name
                    fields = []
                    methods = []

                    for sub_node in ast.iter_child_nodes(node):
                        if isinstance(sub_node, ast.Assign):
                            for target in sub_node.targets:
                                if isinstance(target, ast.Name):
                                    fields.append(target.id)
                        elif isinstance(sub_node, ast.FunctionDef):
                            methods.append(sub_node.name)

                    models_info[model_name] = {
                        'fields': fields,
                        'methods': methods
                    }
    return models_info


def extract_and_save_model_data():
    models_file_path = os.path.join(CODE_DIR, "models_data.json")
    others_file_path = os.path.join(CODE_DIR, "others_data.json")

    # Check if the model data files already exist
    if not os.path.exists(models_file_path) or not os.path.exists(others_file_path):
        # Extract model information
        send_log_to_slack(f"Building codebase data")
        classes = extract_models_and_functions_from_directory(file_name="models.py")
        model_names = create_names_from_classes(classes)

        other = extract_models_and_functions_from_directory(file_name=None, skip_files=["models.py"])
        other_names = create_names_from_classes(other)

        # Save data to json files
        with open(models_file_path, "w", encoding="utf-8") as f:
            json.dump(model_names, f)

        with open(others_file_path, "w", encoding="utf-8") as f:
            json.dump(other_names, f)

    # Load data from json files
    with open(models_file_path, "r", encoding="utf-8") as f:
        model_names = json.load(f)

    with open(others_file_path, "r", encoding="utf-8") as f:
        other_names = json.load(f)

    return model_names, other_names

def extract_models_and_functions_from_directory(file_name=None, skip_files=[], dir_path=CODE_DIR):
    models_info = {}
    all_functions = []

    section_header_regex = re.compile(r'#---\s*\n#(.+\.py)\s*\n#---')

    for root, _, files in os.walk(dir_path):
        for file in files:
            if not file.endswith('.txt'):
                continue

            full_path = os.path.join(root, file)
            print(f"Processing file: {full_path}")

            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                print(f"Cannot read {full_path}: {e}")
                continue

            # Find all sections
            matches = list(section_header_regex.finditer(content))
            for i, match in enumerate(matches):
                section_name = match.group(1)
                if file_name and file_name not in section_name:
                    continue
                elif file_name is None and section_name in skip_files:
                    continue

                # Determine section boundaries
                start_index = match.end()
                if i + 1 < len(matches):
                    end_index = matches[i + 1].start()
                else:
                    end_index = len(content)

                section_content = content[start_index:end_index]
                models = extract_from_section(section_content)

                for model, info in models.items():
                    if model not in models_info:
                        models_info[model] = info
                    else:
                        models_info[model]['fields'].extend(info['fields'])
                        models_info[model]['methods'].extend(info['methods'])

    return models_info

def create_names_from_classes(class_info:dict):
    names = []
    for class_name, class_entry in class_info.items():
        fields = class_entry['fields']
        methods = [method for method in class_entry['methods'] if "__" not in method]

        for field in fields+methods:
            names.append(f"{class_name}.{field}")

    return names

def search_functions_with_keywords(keywords, code_dir=CODE_DIR):
    matches = []

    for root, _, files in os.walk(code_dir):
        for file in files:

            full_path = os.path.join(root, file)
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    source = f.read()
            except Exception as e:
                print(f"Cannot read {full_path}: {e}")
                continue

            try:
                tree = ast.parse(source)
            except SyntaxError as e:
                print(f"Cannot parse {full_path}: {e}")
                continue

            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    func_start = node.lineno - 1
                    func_end = getattr(node, 'end_lineno', None)

                    if func_end is None:
                        # fallback if Python < 3.8 — use indentation trick
                        func_lines = source.splitlines()[func_start:]
                        for i, line in enumerate(func_lines[1:], 1):
                            if line.strip() and not line.startswith((" ", "\t")):
                                func_end = func_start + i
                                break
                        if func_end is None:
                            func_end = len(source.splitlines())

                    func_body = source.splitlines()[func_start:func_end]
                    func_code = "\n".join(func_body)
                    found_keywords = [kw for kw in keywords if kw.lower() in func_code.lower()]
                    if found_keywords:
                        matches.append({
                            "file": full_path,
                            "function_name": node.name,
                            "line_number": func_start + 1,
                            "snippet": func_code,
                            "found_keywords": found_keywords
                        })

    if len(matches) > 200:
        matches = [match for match in matches if len(match['found_keywords']) > 1]

    # If there are still more than 200 matches, prioritize those with multi-word keywords
    if len(matches) > 200:
        multi_word_matches = [
            match for match in matches
            if any('.' in kw or '_' in kw or ' ' in kw for kw in match['found_keywords'] or len(match['found_keywords']) > 1)
        ]

        # If reducing to multi-word matches leads to too few matches, fall back to all matches
        if len(multi_word_matches) > 0:
            matches = multi_word_matches
        else:
            raise Exception("No matches found")

    if len(matches) > 200:
        max_matches_to_return = 200
        matches = random.sample(matches, max_matches_to_return)

    return matches

