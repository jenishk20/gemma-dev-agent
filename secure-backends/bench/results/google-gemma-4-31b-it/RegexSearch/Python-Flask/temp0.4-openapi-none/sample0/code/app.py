import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

# Ensure the files root exists for the app to be runnable
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT)

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_rel = request.args.get('directory', '')
    recursive = request.args.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return jsonify({"error": "Missing required parameter: regex"}), 400

    # Security check: Prevent directory traversal by ensuring the path is within FILES_ROOT
    try:
        search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_rel))
        if not search_path.startswith(FILES_ROOT):
            return jsonify({"error": "Directory path is outside the allowed root directory"}), 400
    except Exception as e:
        return jsonify({"error": f"Invalid directory path: {str(e)}"}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory"}), 400

    # Compile the regex pattern
    try:
        compiled_re = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    matching_files = []

    try:
        # Walk through the directory
        for root, dirs, files in os.walk(search_path):
            # If recursive is False, don't go into subdirectories
            if not recursive and root != search_path:
                continue
            
            for file in files:
                file_full_path = os.path.join(root, file)
                try:
                    # Read file content. Using 'utf-8' and ignoring errors for binary/non-utf8 files
                    with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        if compiled_re.search(content):
                            # Calculate path relative to the search directory as per OpenAPI spec
                            rel_path = os.path.relpath(file_full_path, search_path)
                            matching_files.append(rel_path)
                except Exception:
                    # Skip files that cannot be read
                    continue
            
            if not recursive:
                break

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)