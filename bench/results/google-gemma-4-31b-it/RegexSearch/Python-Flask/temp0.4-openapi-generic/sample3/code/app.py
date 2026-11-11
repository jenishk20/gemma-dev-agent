import os
import re
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

def safe_join(base, path):
    """
    Ensures that the joined path does not escape the base directory.
    """
    # Normalize path to remove '..' and resolve symlinks
    final_path = os.path.abspath(os.path.join(base, path))
    if not final_path.startswith(FILES_ROOT):
        raise PermissionError("Attempted to access directory outside of root.")
    return final_path

@app.route('/search', methods=['GET'])
def search_files():
    # 1. Extract and validate parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return jsonify({"error": "Missing required parameter: regex"}), 400

    # 2. Validate and resolve the search directory
    try:
        search_path = safe_join(FILES_ROOT, directory_param)
        if not os.path.isdir(search_path):
            return jsonify({"error": "Specified directory does not exist or is not a directory"}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid directory path: {str(e)}"}), 400

    # 3. Compile the regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    matching_files = []

    try:
        # 4. Walk through files
        if recursive_param:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the requested search directory
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only check files in the immediate directory
            try:
                for entry in os.scandir(search_path):
                    if entry.is_file():
                        if check_file_content(entry.path, pattern):
                            matching_files.append(entry.name)
            except OSError as e:
                return jsonify({"error": f"Could not read directory: {str(e)}"}), 400

    except Exception as e:
        return jsonify({"error": f"Internal server error during search: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """
    Reads file content and checks if the regex pattern matches.
    Handles potential encoding issues by reading as bytes or ignoring errors.
    """
    try:
        # We open in 'r' mode with errors='ignore' to handle binary files or 
        # mixed encodings without crashing the server.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If a file cannot be read, we simply skip it
        pass
    return False

if __name__ == '__main__':
    # Ensure the root directory exists so the app doesn't crash on startup
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    # Run the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)