import os
import re
from flask import Flask, request, jsonify
from werkzeug.utils import safe_join

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

@app.route('/search', methods=['GET'])
def search_files():
    """
    Searches files in a specified directory and returns files whose content matches the given regex.
    """
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # 1. Validate and resolve the search directory
    # Use safe_join to prevent directory traversal attacks (e.g., directory=../../etc)
    try:
        # If directory_param is empty, it defaults to FILES_ROOT
        search_path = safe_join(FILES_ROOT, directory_param)
        
        # Ensure the resolved path is actually within the FILES_ROOT
        if search_path is None or not search_path.startswith(FILES_ROOT):
            return jsonify({"error": "Invalid directory path provided."}), 400
        
        if not os.path.exists(search_path) or not os.path.isdir(search_path):
            return jsonify({"error": "Specified directory does not exist or is not a directory."}), 400
    except Exception as e:
        return jsonify({"error": f"Directory access error: {str(e)}"}), 400

    # 2. Compile the regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regular expression: {str(e)}"}), 400

    matching_files = []

    try:
        # 3. Traverse files
        if recursive_param:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the search_path as per OpenAPI spec
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only list files in the immediate directory
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        return jsonify({"error": f"Internal server error during search: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """
    Helper to read file content and check for regex match.
    Handles potential encoding issues by ignoring errors.
    """
    try:
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # We read the file content. For very large files, 
            # reading line by line is safer to avoid MemoryError.
            for line in f:
                if pattern.search(line):
                    return True
    except Exception:
        # If a file cannot be read (permissions, etc.), we skip it
        return False
    return False

if __name__ == '__main__':
    # Ensure the files root directory exists so the app doesn't crash on start
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)