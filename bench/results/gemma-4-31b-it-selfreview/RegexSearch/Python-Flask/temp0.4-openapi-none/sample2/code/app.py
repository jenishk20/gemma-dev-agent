import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.abspath(os.path.join(os.getcwd(), 'files'))

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

    # 1. Regex Denial of Service (ReDoS) Mitigation
    # While Python's 're' doesn't have a built-in timeout, we can limit the length 
    # of the regex pattern to prevent extremely complex patterns from being compiled.
    if len(regex_pattern) > 1000:
        return jsonify({"error": "Regex pattern is too long."}), 400

    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # 2. Path Traversal Mitigation
    # Reject absolute paths and '..' to prevent escaping the root directory
    if os.path.isabs(directory_rel) or '..' in directory_rel:
        return jsonify({"error": "Invalid directory path provided."}), 400

    # Construct the absolute path and verify it is contained within FILES_ROOT
    target_dir = os.path.abspath(os.path.join(FILES_ROOT, directory_rel))
    
    if not target_dir.startswith(FILES_ROOT):
        return jsonify({"error": "Directory is outside the allowed files root."}), 400

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({"error": "The specified directory does not exist or is not a directory."}), 400

    matching_files = []

    try:
        if recursive:
            # Walk through the directory tree
            for root, dirs, files in os.walk(target_dir):
                # Resource Exhaustion: Limit depth or number of files if necessary.
                # For this implementation, we iterate through files.
                for file in files:
                    file_path = os.path.join(root, file)
                    if check_file_content(file_path, pattern):
                        rel_path = os.path.relpath(file_path, target_dir)
                        matching_files.append(rel_path)
        else:
            # Only list files in the immediate directory
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isfile(item_path):
                    if check_file_content(item_path, pattern):
                        matching_files.append(item)

    except Exception:
        # Error handling: Return generic 500 without leaking internal details
        return jsonify({"error": "An internal server error occurred during file search."}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex."""
    try:
        # Resource Exhaustion: Limit the amount of data read from a single file
        # to prevent memory exhaustion from extremely large files.
        MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit
        
        if os.path.getsize(file_path) > MAX_FILE_SIZE:
            # If file is too large, we read it in chunks or skip it.
            # To maintain regex functionality (which often requires the whole string),
            # we read up to the limit.
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read(MAX_FILE_SIZE)
                return bool(pattern.search(content))
        else:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                return bool(pattern.search(content))
    except Exception:
        # If file cannot be read (permissions, etc), we skip it
        return False

if __name__ == '__main__':
    # Ensure the files root exists
    if not os.path.exists(FILES_ROOT):
        try:
            os.makedirs(FILES_ROOT)
        except Exception:
            pass
        
    app.run(host='0.0.0.0', port=5000)