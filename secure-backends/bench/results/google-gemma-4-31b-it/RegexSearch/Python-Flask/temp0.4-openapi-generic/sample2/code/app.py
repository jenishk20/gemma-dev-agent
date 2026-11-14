import os
import re
from flask import Flask, request, jsonify
from werkzeug.utils import safe_join

app = Flask(__name__)

# Define the root directory for files
FILES_ROOT = os.path.abspath("./files")

def is_safe_path(base, path):
    """
    Ensures that the resolved path is within the base directory 
    to prevent directory traversal attacks.
    """
    # safe_join handles basic sanitization, but we double check with commonpath
    try:
        # Resolve absolute paths
        abs_base = os.path.abspath(base)
        # Join and resolve the requested path
        requested_path = os.path.abspath(os.path.join(abs_base, path))
        return os.path.commonpath([abs_base, requested_path]) == abs_base
    except Exception:
        return False

@app.route('/search', methods=['GET'])
def search_files():
    # 1. Extract and validate parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    if not regex_pattern:
        return jsonify({"error": "Missing required parameter: regex"}), 400

    # 2. Validate Regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # 3. Validate and resolve directory
    # We use safe_join to prevent directory traversal (e.g., ../../etc/passwd)
    target_dir = safe_join(FILES_ROOT, directory_param)
    
    if target_dir is None or not is_safe_path(FILES_ROOT, target_dir):
        return jsonify({"error": "Invalid or inaccessible directory path"}), 400

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({"error": "The specified directory does not exist"}), 400

    matching_files = []

    try:
        # 4. Search files
        if recursive_param:
            # Recursive search using os.walk
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        # Calculate path relative to the search directory as per schema
                        rel_path = os.path.relpath(full_path, target_dir)
                        matching_files.append(rel_path)
        else:
            # Non-recursive search
            for entry in os.scandir(target_dir):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception as e:
        return jsonify({"error": f"Internal server error during search: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """
    Helper to read file content and check for regex match.
    Handles potential decoding errors for binary files.
    """
    try:
        # We read in chunks or as text. For regex, we typically need text.
        # Using 'utf-8' with 'ignore' to handle files that might not be pure text.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read, we skip it
        pass
    return False

if __name__ == '__main__':
    # Ensure the root files directory exists so the app doesn't crash on startup
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)