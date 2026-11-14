import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath("./files")

# Ensure the files root exists for the app to function
if not os.path.exists(FILES_ROOT):
    os.makedirs(FILES_ROOT)

def is_safe_path(basedir, path):
    """
    Ensures that the resolved path is contained within the basedir.
    Prevents directory traversal attacks.
    """
    # Reject absolute paths to prevent bypassing the root
    if os.path.isabs(path):
        return False
    
    # Join and resolve to absolute path
    full_path = os.path.abspath(os.path.join(basedir, path))
    # Check if the resolved path starts with the basedir
    return full_path.startswith(basedir)

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_param = request.args.get('directory', '')
    recursive_param = request.args.get('recursive', 'false').lower() == 'true'

    # Validation: regex is required
    if not regex_pattern:
        return jsonify({"error": "The 'regex' query parameter is required."}), 400

    # Resource Exhaustion Protection: Limit regex length to prevent ReDoS (Regular Expression Denial of Service)
    if len(regex_pattern) > 1024:
        return jsonify({"error": "Regex pattern is too long."}), 400

    # Validate and compile regex
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regular expression: {str(e)}"}), 400

    # Path Traversal Protection
    if not is_safe_path(FILES_ROOT, directory_param):
        return jsonify({"error": "Invalid directory path provided."}), 400

    search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_param))

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "The specified directory does not exist or is not a directory."}), 400

    matching_files = []

    try:
        # Walk through files
        if recursive_param:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    full_path = os.path.join(root, file)
                    # Double check that the file being read is still within the root (protection against symlink attacks)
                    if not os.path.abspath(full_path).startswith(FILES_ROOT):
                        continue
                    if check_file_content(full_path, pattern):
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            for entry in os.scandir(search_path):
                if entry.is_file():
                    # Ensure the entry is not a symlink pointing outside the root
                    if entry.is_symlink():
                        real_path = os.path.realpath(entry.path)
                        if not real_path.startswith(FILES_ROOT):
                            continue
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)

    except Exception:
        # Generic error to avoid leaking internal stack traces
        return jsonify({"error": "An internal server error occurred while searching files."}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to read file content and check for regex match with resource limits."""
    try:
        # Resource Exhaustion Protection: Limit the amount of data read from a single file
        # to prevent memory exhaustion (OOM) when encountering huge files.
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit
        
        # Check file size before reading
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return False

        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read(MAX_FILE_SIZE)
            # ReDoS mitigation: regex.search can be slow. 
            # In a production environment, one would use a timeout or a different engine.
            if pattern.search(content):
                return True
    except Exception:
        # Silently skip files that cannot be accessed or read
        return False
    return False

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)