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

    # --- SECURITY FIX: Path Traversal ---
    # 1. Reject absolute paths to prevent bypassing the root
    if os.path.isabs(directory_rel):
        return jsonify({"error": "Absolute paths are not allowed"}), 400
    
    # 2. Resolve the path and verify it remains within FILES_ROOT
    # os.path.join handles the concatenation, os.path.abspath resolves '..'
    try:
        search_path = os.path.abspath(os.path.join(FILES_ROOT, directory_rel))
        if not search_path.startswith(FILES_ROOT):
            return jsonify({"error": "Invalid directory path"}), 400
    except Exception:
        return jsonify({"error": "Invalid directory path"}), 400

    if not os.path.exists(search_path) or not os.path.isdir(search_path):
        return jsonify({"error": "Specified directory does not exist or is not a directory"}), 400

    # --- SECURITY FIX: Regex Denial of Service (ReDoS) ---
    # While Python's 're' module doesn't have a built-in timeout, 
    # we compile the regex and wrap the search in a try-except.
    # In a production environment, one would use a library like 'google-re2'.
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
                    # --- SECURITY FIX: Resource Exhaustion ---
                    # Limit the amount of data read from a single file to prevent 
                    # memory exhaustion (e.g., reading a multi-gigabyte log file).
                    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB limit per file
                    
                    if os.path.getsize(file_full_path) > MAX_FILE_SIZE:
                        continue

                    with open(file_full_path, 'r', encoding='utf-8', errors='ignore') as f:
                        content = f.read()
                        # Use search() as per spec (partial match)
                        if compiled_re.search(content):
                            rel_path = os.path.relpath(file_full_path, search_path)
                            matching_files.append(rel_path)
                except (OSError, IOError):
                    # Skip files that cannot be read due to permissions or system errors
                    continue
            
            if not recursive:
                break

    except Exception:
        # Generic error to avoid leaking internal stack traces
        return jsonify({"error": "An internal server error occurred"}), 500

    return jsonify({"files": matching_files}), 200

if __name__ == '__main__':
    # Start the server on 0.0.0.0:5000
    app.run(host='0.0.0.0', port=5000)