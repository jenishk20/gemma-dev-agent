import os
import re
from flask import Flask, request, jsonify
from werkzeug.exceptions import BadRequest

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

def safe_join(root, path):
    """
    Ensures that the resulting path is within the root directory 
    to prevent Directory Traversal attacks.
    """
    # Resolve absolute paths
    final_path = os.path.abspath(os.path.join(root, path))
    if not final_path.startswith(FILES_ROOT):
        raise PermissionError("Access denied: Path is outside the allowed root directory.")
    return final_path

@app.route('/search', methods=['GET'])
def search_files():
    # 1. Extract and validate parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # 2. Validate and resolve the search directory
    try:
        search_path = safe_join(FILES_ROOT, directory_param)
        if not os.path.exists(search_path):
            return jsonify({"error": "The specified directory does not exist."}), 400
        if not os.path.isdir(search_path):
            return jsonify({"error": "The specified path is not a directory."}), 400
    except PermissionError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": f"Directory error: {str(e)}"}), 400

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
                        # Calculate path relative to the search directory
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            # Non-recursive: only look at files directly in search_path
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        return jsonify({"error": f"Internal server error during search: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """
    Reads file content and checks if the regex pattern matches.
    Uses a try-except block to handle binary files or encoding issues.
    """
    try:
        # We open in 'r' mode with errors='ignore' to handle potential binary files 
        # without crashing the server, treating them as text.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read for any reason, we skip it
        pass
    return False

if __name__ == '__main__':
    # Ensure the files root exists for the app to function
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    # Run on 0.0.0.0:5000 as requested
    app.run(host='0.0.0.0', port=5000)