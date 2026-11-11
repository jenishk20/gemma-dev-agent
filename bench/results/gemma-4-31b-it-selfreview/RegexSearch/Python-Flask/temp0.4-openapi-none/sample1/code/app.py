import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath(os.path.join(os.getcwd(), 'files'))

# Resource exhaustion limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file to prevent memory exhaustion
MAX_READ_SIZE = 10 * 1024 * 1024   # Max bytes to read from a file

@app.route('/search', methods=['GET'])
def search_files():
    # Extract query parameters
    regex_pattern = request.args.get('regex')
    directory_rel = request.args.get('directory', '')
    recursive_str = request.args.get('recursive', 'false').lower()
    recursive = recursive_str == 'true'

    if not regex_pattern:
        return jsonify({"error": "Missing required parameter: regex"}), 400

    # Validate and compile regex
    # To prevent ReDoS (Regular Expression Denial of Service), we use a try-except.
    # Note: Python's 're' module doesn't have a built-in timeout. 
    # In a production environment, one might use 'google-re2' or a separate process.
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # Path Traversal Prevention:
    # 1. Reject absolute paths and '..' components explicitly to be strict.
    if os.path.isabs(directory_rel) or '..' in directory_rel.split(os.sep):
        return jsonify({"error": "Invalid directory path: absolute paths and '..' are not allowed"}), 400

    # 2. Resolve absolute path and verify it is within FILES_ROOT.
    search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_rel))
    if not search_path.startswith(FILES_ROOT):
        return jsonify({"error": "Directory path is outside the allowed root directory"}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory"}), 400

    matching_files = []

    try:
        if recursive:
            for root, dirs, files in os.walk(search_path):
                # Security: prevent walking into directories that might be symlinks to outside root
                # os.walk doesn't follow symlinks by default, but we ensure we stay in bounds.
                for file in files:
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            for entry in os.scandir(search_path):
                if entry.is_file():
                    if check_file_content(entry.path, pattern):
                        matching_files.append(entry.name)
    except Exception:
        # Generic catch to prevent leaking internal stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex with resource bounds."""
    try:
        # Resource Exhaustion: Check file size before reading
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return False
            
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            # Read only up to MAX_READ_SIZE to prevent memory exhaustion
            content = f.read(MAX_READ_SIZE)
            if pattern.search(content):
                return True
    except (OSError, IOError):
        # Handle inaccessible files (permissions, etc) without crashing
        return False
    except Exception:
        return False
    return False

if __name__ == '__main__':
    # Ensure the files root directory exists
    if not os.path.exists(FILES_ROOT):
        try:
            os.makedirs(FILES_ROOT)
        except Exception:
            pass
            
    app.run(host='0.0.0.0', port=5000)