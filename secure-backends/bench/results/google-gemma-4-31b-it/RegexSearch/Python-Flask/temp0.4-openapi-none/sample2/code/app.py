import os
import re
from flask import Flask, request, jsonify

app = Flask(__name__)

# The root directory where files are stored
FILES_ROOT = os.path.join(os.getcwd(), 'files')

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

    # Validate regex pattern
    try:
        pattern = re.compile(regex_pattern)
    except re.error as e:
        return jsonify({"error": f"Invalid regex pattern: {str(e)}"}), 400

    # Construct the absolute path to the search directory
    # We use os.path.normpath and check if it starts with FILES_ROOT to prevent directory traversal attacks
    target_dir = os.path.normpath(os.path.join(FILES_ROOT, directory_rel))
    
    if not target_dir.startswith(FILES_ROOT):
        return jsonify({"error": "Directory is outside the allowed files root."}), 400

    if not os.path.exists(target_dir) or not os.path.isdir(target_dir):
        return jsonify({"error": "The specified directory does not exist or is not a directory."}), 400

    matching_files = []

    try:
        if recursive:
            # Walk through the directory tree
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    file_path = os.path.join(root, file)
                    if check_file_content(file_path, pattern):
                        # Calculate path relative to the search directory as per OpenAPI spec
                        rel_path = os.path.relpath(file_path, target_dir)
                        matching_files.append(rel_path)
        else:
            # Only list files in the immediate directory
            for item in os.listdir(target_dir):
                item_path = os.path.join(target_dir, item)
                if os.path.isfile(item_path):
                    if check_file_content(item_path, pattern):
                        matching_files.append(item)

    except Exception as e:
        return jsonify({"error": f"Internal server error: {str(e)}"}), 500

    return jsonify({"files": matching_files}), 200

def check_file_content(file_path, pattern):
    """Helper to check if a file's content matches the regex."""
    try:
        # We open in binary mode and decode to handle potential encoding issues gracefully
        # or read as text. For a general search, we'll try reading as utf-8.
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
            if pattern.search(content):
                return True
    except Exception:
        # If file cannot be read, we skip it
        pass
    return False

if __name__ == '__main__':
    # Ensure the files root exists for the app to function
    if not os.path.exists(FILES_ROOT):
        os.makedirs(FILES_ROOT)
        
    app.run(host='0.0.0.0', port=5000)