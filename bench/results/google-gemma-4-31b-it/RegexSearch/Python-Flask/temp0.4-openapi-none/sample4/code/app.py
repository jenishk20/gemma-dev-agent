import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# Root directory where files are stored
ROOT_FILES_DIR = os.path.abspath("./files")

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_rel = request.args.get('directory', '')
    recursive_str = request.args.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    # Validation: regex is required
    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # Resolve search directory and ensure it's within ROOT_FILES_DIR (Security check)
    search_path = os.path.abspath(os.path.join(ROOT_FILES_DIR, directory_rel))
    if not search_path.startswith(ROOT_FILES_DIR):
        return jsonify({"error": "Directory path is outside the allowed files root."}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory."}), 400

    matching_files = []

    try:
        if recursive:
            # Walk through all subdirectories
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the requested directory
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Only search the immediate directory
            for item in os.listdir(search_path):
                full_path = os.path.join(search_path, item)
                if os.path.isfile(full_path):
                    if check_file_content(full_path, pattern):
                        matching_files.append(item)
    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex."""
    try:
        # We open in binary mode and decode to handle potential encoding issues 
        # while searching for text patterns.
        with open(file_path, 'rb') as f:
            content = f.read().decode('utf-8', errors='ignore')
            if pattern.search(content):
                return True
    except Exception:
        # If a file cannot be read, we skip it
        pass
    return False

if __name__ == '__main__':
    # Ensure the root files directory exists for the app to function
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)
        
    app.run(host='0.0.0.0', port=5000)