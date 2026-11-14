import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

# Ensure the files root exists for the app to function
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT)

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    # Validation: regex is required
    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regular expression: {str(e)}"}), 400

    # Resolve the search directory path and prevent directory traversal attacks
    # We join the root with the provided directory and check if it's still within the root
    search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_param))
    if not search_path.startswith(FILES_ROOT):
        return jsonify({"error": "Directory path is outside the allowed root directory."}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "The specified directory does not exist or is not a directory."}), 400

    matching_files = []

    try:
        # Walk through files
        if recursive_param:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the requested directory
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only list files in the immediate directory
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to read file content and check for regex match."""
    try:
        # We read in binary mode and decode to handle various encodings gracefully
        # or just read as text. Using 'utf-8' with 'ignore' to avoid crashing on binary files.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read, we skip it
        return False
    return False

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)