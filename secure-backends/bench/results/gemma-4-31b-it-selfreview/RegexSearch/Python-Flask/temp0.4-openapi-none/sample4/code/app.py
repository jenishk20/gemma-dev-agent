import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# Root directory where files are stored
ROOT_FILES_DIR = os.path.abspath("./files")

# Resource Exhaustion Limits
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file to prevent DoS
MAX_FILES_TO_SCAN = 10000         # Limit total files scanned to prevent resource exhaustion

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

    # Security: Prevent ReDoS (Regular Expression Denial of Service)
    # While Python's 're' doesn't have a built-in timeout, we compile and 
    # handle potential errors. In a production environment, one might use 
    # the 'google-re2' library for linear-time guarantees.
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # Path Traversal Prevention
    # 1. Reject absolute paths and '..' components in the input string
    if os.path.isabs(directory_rel) or '..' in directory_rel:
        return jsonify({"error": "Invalid directory path: absolute paths and '..' are not allowed."}), 400

    # 2. Resolve path and verify it remains within ROOT_FILES_DIR
    search_path = os.path.abspath(os.path.join(ROOT_FILES_DIR, directory_rel))
    if not search_path.startswith(ROOT_FILES_DIR):
        return jsonify({"error": "Directory path is outside the allowed files root."}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory."}), 400

    matching_files = []
    files_scanned = 0

    try:
        if recursive:
            for root, dirs, files in os.walk(search_path):
                for file in files:
                    files_scanned += 1
                    if files_scanned > MAX_FILES_TO_SCAN:
                        return jsonify({"error": "Too many files to scan in the specified directory."}), 400
                    
                    full_path = os.path.join(root, file)
                    if check_file_content(full_path, pattern):
                        rel_path = os.path.relpath(full_path, search_path)
                        matching_files.append(rel_path)
        else:
            for item in os.listdir(search_path):
                files_scanned += 1
                if files_scanned > MAX_FILES_TO_SCAN:
                    return jsonify({"error": "Too many files to scan in the specified directory."}), 400
                
                full_path = os.path.join(search_path, item)
                if os.path.isfile(full_path):
                    if check_file_content(full_path, pattern):
                        matching_files.append(item)
    except Exception:
        # Generic error to avoid leaking internal system details/stack traces
        return jsonify({"error": "An internal error occurred while searching files."}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex with resource bounds."""
    try:
        # Resource Exhaustion: Check file size before reading
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            return False
            
        with open(file_path, 'rb') as f:
            # Read content and decode. Using 'ignore' to prevent crashes on binary files.
            content = f.read().decode('utf-8', errors='ignore')
            if pattern.search(content):
                return True
    except Exception:
        # Silently skip files that cannot be accessed or read
        pass
    return False

if __name__ == '__main__':
    if not os.path.exists(ROOT_FILES_DIR):
        os.makedirs(ROOT_FILES_DIR)
        
    app.run(host='0.0.0.0', port=5000)